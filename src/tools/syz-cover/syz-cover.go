// Copyright 2018 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

// syz-cover generates coverage HTML report from raw coverage files.
// Raw coverage files are text files with one PC in hex form per line, e.g.:
//
//	0xffffffff8398658d
//	0xffffffff839862fc
//	0xffffffff8398633f
//
// Raw coverage files can be obtained either from /rawcover manager HTTP handler,
// or from syz-execprog with -coverfile flag.
//
// Usage:
//	syz-cover [-os=OS -arch=ARCH -kernel_src=. -kernel_obj=.] rawcover.file*
package main

import (
	"bufio"
	"bytes"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"

	"monarch/pkg/cover"
	"monarch/pkg/osutil"
	"monarch/pkg/tool"
	"monarch/sys/targets"
)

func main() {
	var (
		flagOS             = flag.String("os", runtime.GOOS, "target os")
		flagArch           = flag.String("arch", runtime.GOARCH, "target arch")
		flagVM             = flag.String("vm", "", "VM type")
		flagKernelSrc      = flag.String("kernel_src", "", "path to kernel sources")
		flagKernelBuildSrc = flag.String("kernel_build_src", "", "path to kernel image's build dir (optional)")
		flagKernelObj      = flag.String("kernel_obj", "", "path to kernel build/obj dir")
		flagExport         = flag.String("csv", "", "export coverage data in csv format (optional)")
	)
	defer tool.Init()()

	if len(flag.Args()) == 0 {
		fmt.Fprintf(os.Stderr, "usage: syz-cover [flags] rawcover.file\n")
		flag.PrintDefaults()
		os.Exit(1)
	}
	if *flagKernelSrc == "" {
		*flagKernelSrc = "."
	}
	if *flagKernelObj == "" {
		*flagKernelObj = *flagKernelSrc
	}
	if *flagKernelBuildSrc == "" {
		*flagKernelBuildSrc = *flagKernelSrc
	}
	target := targets.Get(*flagOS, *flagArch)
	if target == nil {
		tool.Failf("unknown target %v/%v", *flagOS, *flagArch)
	}
	pcs, err := readPCs(flag.Args())
	if err != nil {
		tool.Fail(err)
	}
	rg, err := cover.MakeReportGenerator(target, *flagVM, *flagKernelObj,
		*flagKernelSrc, *flagKernelBuildSrc, nil, nil, nil)
	if err != nil {
		tool.Fail(err)
	}
	progs := []cover.Prog{{PCs: pcs}}
	buf := new(bytes.Buffer)
	if *flagExport != "" {
		if err := rg.DoCSV(buf, progs, nil); err != nil {
			tool.Fail(err)
		}
		if err := osutil.WriteFile(*flagExport, buf.Bytes()); err != nil {
			tool.Fail(err)
		}
		return
	}
	if err := rg.DoHTML(buf, progs, nil); err != nil {
		tool.Fail(err)
	}
	fn, err := osutil.TempFile("syz-cover")
	if err != nil {
		tool.Fail(err)
	}
	fn += ".html"
	if err := osutil.WriteFile(fn, buf.Bytes()); err != nil {
		tool.Fail(err)
	}
	if err := exec.Command("xdg-open", fn).Start(); err != nil {
		tool.Failf("failed to start browser: %v", err)
	}
}

func readPCs(files []string) ([]uint64, error) {
	var pcs []uint64
	for _, file := range files {
		data, err := ioutil.ReadFile(file)
		if err != nil {
			return nil, err
		}
		for s := bufio.NewScanner(bytes.NewReader(data)); s.Scan(); {
			line := strings.TrimSpace(s.Text())
			if line == "" {
				continue
			}
			pc, err := strconv.ParseUint(line, 0, 64)
			if err != nil {
				return nil, err
			}
			pcs = append(pcs, pc)
		}
	}
	return pcs, nil
}
