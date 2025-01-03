// Copyright 2015 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

// mutates mutates a given program and prints result.
package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"runtime"
	"strings"
	"time"

	"monarch/pkg/db"
	"monarch/pkg/mgrconfig"
	"monarch/prog"
	_ "monarch/sys"
)

var (
	flagOS     = flag.String("os", runtime.GOOS, "target os")
	flagArch   = flag.String("arch", runtime.GOARCH, "target arch")
	flagSeed   = flag.Int("seed", -1, "prng seed")
	flagLen    = flag.Int("len", prog.RecommendedCalls, "number of calls in programs")
	flagEnable = flag.String("enable", "", "comma-separated list of enabled syscalls")
	flagCorpus = flag.String("corpus", "", "name of the corpus file")
)

func main() {
	flag.Parse()
	target, err := prog.GetTarget(*flagOS, *flagArch)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(1)
	}
	var syscalls map[*prog.Syscall]bool
	if *flagEnable != "" {
		enabled := strings.Split(*flagEnable, ",")
		syscallsIDs, err := mgrconfig.ParseEnabledSyscalls(target, enabled, nil)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to parse enabled syscalls: %v\n", err)
			os.Exit(1)
		}
		syscalls = make(map[*prog.Syscall]bool)
		for _, id := range syscallsIDs {
			syscalls[target.Syscalls[id]] = true
		}
		var disabled map[*prog.Syscall]string
		syscalls, disabled = target.TransitivelyEnabledCalls(syscalls)
		for c, reason := range disabled {
			fmt.Fprintf(os.Stderr, "disabling %v: %v\n", c.Name, reason)
		}
	}
	seed := time.Now().UnixNano()
	if *flagSeed != -1 {
		seed = int64(*flagSeed)
	}
	corpus, err := db.ReadCorpus(*flagCorpus, target)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to read corpus: %v\n", err)
		os.Exit(1)
	}
	rs := rand.NewSource(seed)
	//tao modified
	var tmp_corpus [][]*prog.Prog
	tmp_corpus = append(tmp_corpus, corpus)
	ct := target.BuildChoiceTable(tmp_corpus, syscalls)
	//tao end

	var p *prog.Prog
	if flag.NArg() == 0 {
		p = target.Generate(rs, *flagLen, ct)
	} else {
		data, err := ioutil.ReadFile(flag.Arg(0))
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to read prog file: %v\n", err)
			os.Exit(1)
		}
		p, err = target.Deserialize(data, prog.Strict)
		if err != nil {
			fmt.Fprintf(os.Stderr, "failed to deserialize the program: %v\n", err)
			os.Exit(1)
		}
		//tao modified
		//p.Mutate(rs, *flagLen, ct, corpus)
		p.Mutate(rs, *flagLen, ct, tmp_corpus)
		//tao end
	}
	fmt.Printf("%s\n", p.Serialize())
}
