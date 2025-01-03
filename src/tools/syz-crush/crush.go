// Copyright 2016 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

// syz-crush replays crash log on multiple VMs. Usage:
//   syz-crush -config=config.file execution.log
// Intended for reproduction of particularly elusive crashes.
package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"time"

	"monarch/pkg/csource"
	"monarch/pkg/hash"
	"monarch/pkg/instance"
	"monarch/pkg/mgrconfig"
	"monarch/pkg/osutil"
	"monarch/pkg/report"
	"monarch/vm"
)

var (
	flagConfig      = flag.String("config", "", "manager configuration file")
	flagDebug       = flag.Bool("debug", false, "dump all VM output to console")
	flagRestartTime = flag.Duration("restart_time", 0, "how long to run the test")
	flagInfinite    = flag.Bool("infinite", true, "by default test is run for ever, -infinite=false to stop on crash")
)

type FileType int

const (
	LogFile FileType = iota
	CProg
)

func main() {
	flag.Parse()
	if len(flag.Args()) != 1 || *flagConfig == "" {
		fmt.Fprintf(os.Stderr, "usage: syz-crush [flags] <execution.log|creprog.c>\n")
		flag.PrintDefaults()
		os.Exit(1)
	}
	cfg, err := mgrconfig.LoadFile(*flagConfig)
	if err != nil {
		log.Fatal(err)
	}
	if *flagRestartTime == 0 {
		*flagRestartTime *= cfg.Timeouts.VMRunningTime
	}
	if *flagInfinite {
		log.Printf("running infinitely and restarting VM every %v", *flagRestartTime)
	} else {
		log.Printf("running until crash is found or till %v", *flagRestartTime)
	}

	vmPool, err := vm.Create(cfg, *flagDebug)
	if err != nil {
		log.Fatalf("%v", err)
	}

	reporter, err := report.NewReporter(cfg)
	if err != nil {
		log.Fatalf("%v", err)
	}

	reproduceMe := flag.Args()[0]
	if cfg.Tag == "" {
		// If no tag is given, use reproducer name as the tag.
		cfg.Tag = filepath.Base(reproduceMe)
	}
	runType := LogFile
	if strings.HasSuffix(reproduceMe, ".c") {
		runType = CProg
	}
	if runType == CProg {
		execprog, err := ioutil.ReadFile(reproduceMe)
		if err != nil {
			log.Fatalf("error reading source file from '%s'", reproduceMe)
		}

		cfg.ExecprogBin, err = csource.BuildNoWarn(cfg.Target, execprog)
		if err != nil {
			log.Fatalf("failed to build source file: %v", err)
		}

		log.Printf("compiled csource %v to cprog: %v", reproduceMe, cfg.ExecprogBin)
	} else {
		log.Printf("reproducing from log file: %v", reproduceMe)
	}

	log.Printf("booting %v test machines...", vmPool.Count())
	runDone := make(chan *report.Report)
	var shutdown, stoppedWorkers uint32

	for i := 0; i < vmPool.Count(); i++ {
		go func(index int) {
			for {
				runDone <- runInstance(cfg, reporter, vmPool, index, *flagRestartTime, runType)
				if atomic.LoadUint32(&shutdown) != 0 || !*flagInfinite {
					// If this is the last worker then we can close the channel.
					if atomic.AddUint32(&stoppedWorkers, 1) == uint32(vmPool.Count()) {
						log.Printf("vm-%v: closing channel", index)
						close(runDone)
					}
					break
				}
			}
			log.Printf("vm-%v: done", index)
		}(i)
	}

	shutdownC := make(chan struct{})
	osutil.HandleInterrupts(shutdownC)
	go func() {
		<-shutdownC
		atomic.StoreUint32(&shutdown, 1)
		close(vm.Shutdown)
	}()

	var count, crashes int
	for rep := range runDone {
		count++
		if rep != nil {
			crashes++
			storeCrash(cfg, rep)
		}
		log.Printf("instances executed: %v, crashes: %v", count, crashes)
	}

	log.Printf("all done. reproduced %v crashes. reproduce rate %.2f%%", crashes, float64(crashes)/float64(count)*100.0)
}

func storeCrash(cfg *mgrconfig.Config, rep *report.Report) {
	id := hash.String([]byte(rep.Title))
	dir := filepath.Join(filepath.Dir(flag.Args()[0]), "crashes", id)
	osutil.MkdirAll(dir)

	index := 0
	for ; osutil.IsExist(filepath.Join(dir, fmt.Sprintf("log%v", index))); index++ {
	}
	log.Printf("saving crash '%v' with index %v in %v", rep.Title, index, dir)

	if err := osutil.WriteFile(filepath.Join(dir, "description"), []byte(rep.Title+"\n")); err != nil {
		log.Printf("failed to write crash description: %v", err)
	}
	if err := osutil.WriteFile(filepath.Join(dir, fmt.Sprintf("log%v", index)), rep.Output); err != nil {
		log.Printf("failed to write crash log: %v", err)
	}
	if err := osutil.WriteFile(filepath.Join(dir, fmt.Sprintf("tag%v", index)), []byte(cfg.Tag)); err != nil {
		log.Printf("failed to write crash tag: %v", err)
	}
	if len(rep.Report) > 0 {
		if err := osutil.WriteFile(filepath.Join(dir, fmt.Sprintf("report%v", index)), rep.Report); err != nil {
			log.Printf("failed to write crash report: %v", err)
		}
	}
	if err := osutil.CopyFile(flag.Args()[0], filepath.Join(dir, fmt.Sprintf("reproducer%v", index))); err != nil {
		log.Printf("failed to write crash reproducer: %v", err)
	}
}

func runInstance(cfg *mgrconfig.Config, reporter *report.Reporter,
	vmPool *vm.Pool, index int, timeout time.Duration, runType FileType) *report.Report {
	log.Printf("vm-%v: starting", index)
	inst, err := vmPool.Create(index)
	if err != nil {
		log.Printf("failed to create instance: %v", err)
		return nil
	}
	defer inst.Close()

	execprogBin, err := inst.Copy(cfg.ExecprogBin)
	if err != nil {
		log.Printf("failed to copy execprog: %v", err)
		return nil
	}

	cmd := ""
	if runType == LogFile {
		// If SyzExecutorCmd is provided, it means that syz-executor is already in
		// the image, so no need to copy it.
		executorBin := cfg.SysTarget.ExecutorBin
		if executorBin == "" {
			executorBin, err = inst.Copy(cfg.ExecutorBin)
			if err != nil {
				log.Printf("failed to copy executor: %v", err)
				return nil
			}
		}
		logFile, err := inst.Copy(flag.Args()[0])
		if err != nil {
			log.Printf("failed to copy log: %v", err)
			return nil
		}

		cmd = instance.ExecprogCmd(execprogBin, executorBin, cfg.TargetOS, cfg.TargetArch, cfg.Sandbox,
			true, true, true, cfg.Procs, -1, -1, true, cfg.Timeouts.Slowdown, logFile)
	} else {
		cmd = execprogBin
	}

	outc, errc, err := inst.Run(timeout, nil, cmd)
	if err != nil {
		log.Printf("failed to run execprog: %v", err)
		return nil
	}

	log.Printf("vm-%v: crushing...", index)
	rep := inst.MonitorExecution(outc, errc, reporter, vm.ExitTimeout)
	if rep != nil {
		log.Printf("vm-%v: crash: %v", index, rep.Title)
		return rep
	}
	log.Printf("vm-%v: running long enough, stopping", index)
	return nil
}
