// Copyright 2018 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package main

import (
	"fmt"
	"math/rand"
	"net"
	"sync"
	"time"
	//"runtime/debug"

	"monarch/pkg/cover"
	"monarch/pkg/host"
	"monarch/pkg/log"
	"monarch/pkg/mgrconfig"
	"monarch/pkg/rpctype"
	"monarch/pkg/signal"
	"monarch/prog"
)

type RPCServer struct {
	mgr                   RPCManagerView
	cfg                   *mgrconfig.Config
	modules               []host.KernelModule
	port                  int
	targetEnabledSyscalls map[*prog.Syscall]bool
	coverFilter           map[uint32]uint32
	stats                 *Stats
	batchSize             int

	mu              sync.Mutex
	fuzzers         map[string]*Fuzzer
	checkResult     *rpctype.CheckArgs
	maxSignal       signal.Signal
	corpusCliSignal signal.Signal
	corpusSrvSignal signal.Signal
	corpusFailSignal signal.Signal
	corpusCliCover  cover.Cover
	corpusSrvCover  cover.Cover
	rotator         *prog.Rotator
	rnd             *rand.Rand
	checkFailures   int

	startTime int64

	smashQueue  []*rpctype.NewInputArgs
	triageQueue []*rpctype.NewInputArgs
}

type Fuzzer struct {
	name          string
	rotated       bool
	inputs        []rpctype.RPCInput
	newMaxSignal  signal.Signal
	rotatedSignal signal.Signal
	machineInfo   []byte
}

type BugFrames struct {
	memoryLeaks []string
	dataRaces   []string
}

// RPCManagerView restricts interface between RPCServer and Manager.
type RPCManagerView interface {
	fuzzerConnect([]host.KernelModule) (
		[]rpctype.RPCInput, BugFrames, map[uint32]uint32, []byte, error)
	machineChecked(result *rpctype.CheckArgs, enabledSyscalls map[*prog.Syscall]bool)
	newInput(inp rpctype.RPCInput, cliSign signal.Signal, srvSign signal.Signal) bool
	candidateBatch(size int) []rpctype.RPCCandidate
	rotateCorpus() bool
}

func startRPCServer(mgr *Manager) (*RPCServer, error) {
	serv := &RPCServer{
		mgr:       mgr,
		cfg:       mgr.cfg,
		stats:     mgr.stats,
		fuzzers:   make(map[string]*Fuzzer),
		rnd:       rand.New(rand.NewSource(time.Now().UnixNano())),
		startTime: 0,
	}
	serv.batchSize = 5
	if serv.batchSize < mgr.cfg.Procs {
		serv.batchSize = mgr.cfg.Procs
	}
	s, err := rpctype.NewRPCServer(mgr.cfg.RPC, "Manager", serv)
	if err != nil {
		return nil, err
	}
	log.Logf(0, "serving rpc on tcp://%v", s.Addr())
	serv.port = s.Addr().(*net.TCPAddr).Port
	go s.Serve()
	return serv, nil
}

func (serv *RPCServer) Connect(a *rpctype.ConnectArgs, r *rpctype.ConnectRes) error {
	log.Logf(1, "fuzzer %v connected", a.Name)
	serv.stats.vmRestarts.inc()

	corpus, bugFrames, coverFilter, coverBitmap, err := serv.mgr.fuzzerConnect(a.Modules)
	if err != nil {
		return err
	}
	serv.coverFilter = coverFilter
	serv.modules = a.Modules

	serv.mu.Lock()
	defer serv.mu.Unlock()

	f := &Fuzzer{
		name:        a.Name,
		machineInfo: a.MachineInfo,
	}
	serv.fuzzers[a.Name] = f
	r.MemoryLeakFrames = bugFrames.memoryLeaks
	r.DataRaceFrames = bugFrames.dataRaces
	r.CoverFilterBitmap = coverBitmap
	r.EnabledCalls = serv.cfg.Syscalls
	r.GitRevision = prog.GitRevision
	r.TargetRevision = serv.cfg.Target.Revision
	if serv.mgr.rotateCorpus() && serv.rnd.Intn(5) == 0 {
		// We do rotation every other time because there are no objective
		// proofs regarding its efficiency either way.
		// Also, rotation gives significantly skewed syscall selection
		// (run prog.TestRotationCoverage), it may or may not be OK.
		r.CheckResult = serv.rotateCorpus(f, corpus)
	} else {
		r.CheckResult = serv.checkResult
		f.inputs = corpus
		f.newMaxSignal = serv.maxSignal.Copy()
	}
	return nil
}

func (serv *RPCServer) rotateCorpus(f *Fuzzer, corpus []rpctype.RPCInput) *rpctype.CheckArgs {
	// Fuzzing tends to stuck in some local optimum and then it fails to cover
	// other state space points since code coverage is only a very approximate
	// measure of logic coverage. To overcome this we introduce some variation
	// into the process which should cause steady corpus rotation over time
	// (the same coverage is achieved in different ways).
	//
	// First, we select a subset of all syscalls for each VM run (result.EnabledCalls).
	// This serves 2 goals: (1) target fuzzer at a particular area of state space,
	// (2) disable syscalls that cause frequent crashes at least in some runs
	// to allow it to do actual fuzzing.
	//
	// Then, we remove programs that contain disabled syscalls from corpus
	// that will be sent to the VM (f.inputs). We also remove 10% of remaining
	// programs at random to allow to rediscover different variations of these programs.
	//
	// Then, we drop signal provided by the removed programs and also 10%
	// of the remaining signal at random (f.newMaxSignal). This again allows
	// rediscovery of this signal by different programs.
	//
	// Finally, we adjust criteria for accepting new programs from this VM (f.rotatedSignal).
	// This allows to accept rediscovered varied programs even if they don't
	// increase overall coverage. As the result we have multiple programs
	// providing the same duplicate coverage, these are removed during periodic
	// corpus minimization process. The minimization process is specifically
	// non-deterministic to allow the corpus rotation.
	//
	// Note: at no point we drop anything globally and permanently.
	// Everything we remove during this process is temporal and specific to a single VM.
	calls := serv.rotator.Select()

	var callIDs []int
	callNames := make(map[string]bool)
	for call := range calls {
		callNames[call.Name] = true
		callIDs = append(callIDs, call.ID)
	}

	f.inputs, f.newMaxSignal = serv.selectInputs(callNames, corpus, serv.maxSignal)
	// Remove the corresponding signal from rotatedSignal which will
	// be used to accept new inputs from this manager.
	f.rotatedSignal = serv.corpusCliSignal.Intersection(f.newMaxSignal)
	f.rotatedSignal.Merge(serv.corpusSrvSignal.Intersection(f.newMaxSignal))
	f.rotated = true

	result := *serv.checkResult
	result.EnabledCalls = map[string][]int{serv.cfg.Sandbox: callIDs}
	return &result
}

func (serv *RPCServer) selectInputs(enabled map[string]bool, inputs0 []rpctype.RPCInput, signal0 signal.Signal) (
	inputs []rpctype.RPCInput, signal signal.Signal) {
	signal = signal0.Copy()
	for _, inp := range inputs0 {
		calls, _, err := prog.CallSet(inp.Prog...)
		if err != nil {
			panic(fmt.Sprintf("rotateInputs: CallSet failed: %v\n%s", err, inp.Prog))
		}
		for call := range calls {
			if !enabled[call] {
				goto drop
			}
		}
		if serv.rnd.Float64() > 0.9 {
			goto drop
		}
		inputs = append(inputs, inp)
		continue
	drop:
		for _, sig := range inp.CliSignal.Elems {
			delete(signal, sig)
		}
		for _, sig := range inp.SrvSignal.Elems {
			delete(signal, sig)
		}
	}
	signal.Split(len(signal) / 10)
	return inputs, signal
}

func (serv *RPCServer) Check(a *rpctype.CheckArgs, r *int) error {

	serv.mu.Lock()
	defer serv.mu.Unlock()

	if serv.checkResult != nil {
		return nil // another VM has already made the check
	}
	// Note: need to print disbled syscalls before failing due to an error.
	// This helps to debug "all system calls are disabled".
	if len(serv.cfg.EnabledSyscalls) != 0 && len(a.DisabledCalls[serv.cfg.Sandbox]) != 0 {
		disabled := make(map[string]string)
		for _, dc := range a.DisabledCalls[serv.cfg.Sandbox] {
			disabled[serv.cfg.Target.Syscalls[dc.ID].Name] = dc.Reason
		}
		/*
		for _, id := range serv.cfg.Syscalls {
			name := serv.cfg.Target.Syscalls[id].Name
			if reason := disabled[name]; reason != "" {
				log.Logf(0, "disabling %v: %v", name, reason)
			}
		}
		*/
	}
	if a.Error != "" {
		log.Logf(0, "machine check failed: %v", a.Error)
		serv.checkFailures++
		if serv.checkFailures == 10 {
			log.Fatalf("machine check failing")
		}
		return fmt.Errorf("machine check failed: %v", a.Error)
	}
	serv.targetEnabledSyscalls = make(map[*prog.Syscall]bool)
	for _, call := range a.EnabledCalls[serv.cfg.Sandbox] {
		serv.targetEnabledSyscalls[serv.cfg.Target.Syscalls[call]] = true
	}
	log.Logf(0, "%-24v: %v/%v", "syscalls", len(serv.targetEnabledSyscalls), len(serv.cfg.Target.Syscalls))
	for _, feat := range a.Features.Supported() {
		log.Logf(0, "%-24v: %v", feat.Name, feat.Reason)
	}
	serv.mgr.machineChecked(a, serv.targetEnabledSyscalls)
	a.DisabledCalls = nil
	serv.checkResult = a
	serv.rotator = prog.MakeRotator(serv.cfg.Target, serv.targetEnabledSyscalls, serv.rnd)
	return nil
}

func (srv *RPCServer) QueueSmashEnqueue(a *rpctype.NewInputArgs, r *int) error {
	srv.smashQueue = append(srv.smashQueue, a)
	log.Logf(0, "--- queue QueueSmashEnqueue")
	return nil
}

func (srv *RPCServer) QueueSmashDequeue(a *int, r *int) error {
	last := len(srv.smashQueue) - 1
	srv.smashQueue = srv.smashQueue[:last]
	log.Logf(0, "--- queue QueueSmashDequeue")
	return nil
}

func (srv *RPCServer) QueueTriageEnqueue(a *rpctype.NewInputArgs, r *int) error {
	srv.triageQueue = append(srv.triageQueue, a)
	log.Logf(0, "--- queue QueueTriageEnqueue")
	return nil
}

func (srv *RPCServer) QueueTriageDequeue(a *int, r *int) error {
	last := len(srv.triageQueue) - 1
	srv.triageQueue = srv.triageQueue[:last]
	log.Logf(0, "--- queue QueueTriageDequeue")
	return nil
}

func (srv *RPCServer) PollQueue(a *int, r *rpctype.PollQueueRes) error {
	r.Seeds = append(r.Seeds, srv.triageQueue...)
	r.Seeds = append(r.Seeds, srv.smashQueue...)
	srv.smashQueue = append(srv.smashQueue, srv.triageQueue...)
	srv.triageQueue = nil
	return nil
}

//

func (serv *RPCServer) NewInput(a *rpctype.NewInputArgs, r *int) error {
	inputCliSignal := a.CliSignal.Deserialize()
	inputSrvSignal := a.SrvSignal.Deserialize()
	log.Logf(4, "new input from %v for syscall %v (signal=%v, clientCover=%v, serverCover=%v)",
		a.Name, a.Call, inputCliSignal.Len()+inputSrvSignal.Len(), len(a.CliCover), len(a.SrvCover))
	bad, disabled := checkProgram(serv.cfg.Target, serv.targetEnabledSyscalls, a.RPCInput.Prog...)
	if bad || disabled {
		log.Logf(0, "rejecting program from fuzzer (bad=%v, disabled=%v):\n%s", bad, disabled, a.RPCInput.Prog)
		return nil
	}
	serv.mu.Lock()
	defer serv.mu.Unlock()

	f := serv.fuzzers[a.Name]
	// Note: f may be nil if we called shutdownInstance,
	// but this request is already in-flight.
	genuine := !serv.corpusCliSignal.Diff(inputCliSignal).Empty() || !serv.corpusSrvSignal.Diff(inputSrvSignal).Empty()
	rotated := false
	if !genuine && f != nil && f.rotated {
		rotated = !f.rotatedSignal.Diff(inputCliSignal).Empty() || !f.rotatedSignal.Diff(inputSrvSignal).Empty()
	}
	if !genuine && !rotated {
		return nil
	}

	if !serv.mgr.newInput(a.RPCInput, inputCliSignal, inputSrvSignal) {
		return nil
	}

	if f != nil && f.rotated {
		f.rotatedSignal.Merge(inputSrvSignal)
		f.rotatedSignal.Merge(inputCliSignal)
	}

	cliDiff := serv.corpusCliCover.MergeDiff(a.CliCover)
	srvDiff := serv.corpusSrvCover.MergeDiff(a.SrvCover)
	diff := append(cliDiff, srvDiff...)

	/*
		for _, cov := range(cliDiff) {
			log.Logf(0, "client cover:%x", cov)
		}
	*/

	/*
	if a.Call == ".extra" {
		log.Logf(0, "New covers from server side: srvCover (%d, %d), cliCover (%d, %d)",
			len(a.SrvCover), len(srvDiff), len(a.CliCover), len(cliDiff))
	} else if a.Call == "failure" {
		log.Logf(0, "New covers from failures side: srvCover (%d, %d), cliCover (%d, %d)",
			len(a.SrvCover), len(srvDiff), len(a.CliCover), len(cliDiff))
	} else {
		log.Logf(0, "New covers from client side: srvCover (%d, %d), cliCover (%d, %d)",
			len(a.SrvCover), len(srvDiff), len(a.CliCover), len(cliDiff))
	}
	*/

	serv.stats.corpusCliCover.set(len(serv.corpusCliCover))
	serv.stats.corpusSrvCover.set(len(serv.corpusSrvCover))
	if len(diff) != 0 && serv.coverFilter != nil {
		// Note: ReportGenerator is already initialized if coverFilter is enabled.
		rg, err := getReportGenerator(serv.cfg, serv.modules)
		if err != nil {
			return err
		}
		filtered := 0
		for _, pc := range diff {
			if serv.coverFilter[uint32(rg.RestorePC(pc))] != 0 {
				filtered++
			}
		}
		serv.stats.corpusCoverFiltered.add(filtered)
	}
	serv.stats.newInputs.inc()
	if rotated {
		serv.stats.rotatedInputs.inc()
	}

	if genuine {
		serv.corpusCliSignal.Merge(inputCliSignal)
		serv.corpusSrvSignal.Merge(inputSrvSignal)
		if a.Call == "failure" {
			serv.corpusFailSignal.Merge(inputCliSignal)
			serv.corpusFailSignal.Merge(inputSrvSignal)
		}
		serv.stats.corpusCliSignal.set(serv.corpusCliSignal.Len())
		serv.stats.corpusSrvSignal.set(serv.corpusSrvSignal.Len())
		serv.stats.corpusFailSignal.set(serv.corpusFailSignal.Len())

		a.RPCInput.CliCover = nil
		a.RPCInput.SrvCover = nil // Don't send coverage back to all fuzzers.
		for _, other := range serv.fuzzers {
			if other == f || other.rotated {
				continue
			}
			other.inputs = append(other.inputs, a.RPCInput)
		}
	}
	return nil
}

func (serv *RPCServer) Poll(a *rpctype.PollArgs, r *rpctype.PollRes) error {
	serv.stats.mergeNamed(a.Stats)

	serv.mu.Lock()
	defer serv.mu.Unlock()

	f := serv.fuzzers[a.Name]
	if f == nil {
		// This is possible if we called shutdownInstance,
		// but already have a pending request from this instance in-flight.
		log.Logf(1, "poll: fuzzer %v is not connected", a.Name)
		return nil
	}
	newMaxSignal := serv.maxSignal.Diff(a.MaxSignal.Deserialize())
	if !newMaxSignal.Empty() {
		serv.maxSignal.Merge(newMaxSignal)
		serv.stats.maxSignal.set(len(serv.maxSignal))
		for _, f1 := range serv.fuzzers {
			if f1 == f || f1.rotated {
				continue
			}
			f1.newMaxSignal.Merge(newMaxSignal)
		}
	}
	if f.rotated {
		// Let rotated VMs run in isolation, don't send them anything.
		return nil
	}
	r.MaxSignal = f.newMaxSignal.Split(2000).Serialize()
	if a.NeedCandidates {
		r.Candidates = serv.mgr.candidateBatch(serv.batchSize)
	}
	if len(r.Candidates) == 0 {
		batchSize := serv.batchSize
		// When the fuzzer starts, it pumps the whole corpus.
		// If we do it using the final batchSize, it can be very slow
		// (batch of size 6 can take more than 10 mins for 50K corpus and slow kernel).
		// So use a larger batch initially (we use no stats as approximation of initial pump).
		const initialBatch = 50
		if len(a.Stats) == 0 && batchSize < initialBatch {
			batchSize = initialBatch
		}
		for i := 0; i < batchSize && len(f.inputs) > 0; i++ {
			last := len(f.inputs) - 1
			r.NewInputs = append(r.NewInputs, f.inputs[last])
			f.inputs[last] = rpctype.RPCInput{}
			f.inputs = f.inputs[:last]
		}
		if len(f.inputs) == 0 {
			f.inputs = nil
		}
	}
	log.Logf(4, "poll from %v: candidates=%v inputs=%v maxsignal=%v",
		a.Name, len(r.Candidates), len(r.NewInputs), len(r.MaxSignal.Elems))
	return nil
}

func (serv *RPCServer) shutdownInstance(name string) []byte {
	serv.mu.Lock()
	defer serv.mu.Unlock()

	fuzzer := serv.fuzzers[name]
	if fuzzer == nil {
		return nil
	}
	delete(serv.fuzzers, name)
	return fuzzer.machineInfo
}
