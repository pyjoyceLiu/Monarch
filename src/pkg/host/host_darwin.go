// Copyright 2018 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package host

import (
	"monarch/prog"
)

func isSupported(c *prog.Syscall, target *prog.Target, sandbox string) (bool, string) {
	return true, ""
}

func init() {
	checkFeature[FeatureCoverage] = unconditionallyEnabled
}
