// Copyright 2021 syzkaller project authors. All rights reserved.
// Use of this source code is governed by Apache 2 LICENSE that can be found in the LICENSE file.

package main

import (
	"fmt"
	"log"
	"path/filepath"
	"time"

	syz_instance "monarch/pkg/instance"
	"monarch/pkg/osutil"
	"monarch/pkg/vcs"
)

type Checkout struct {
	Path      string
	Name      string
	Running   []*Instance
	Completed []*RunResult
}

func (checkout *Checkout) ArchiveRunning() error {
	for _, instance := range checkout.Running {
		result, err := instance.FetchResult()
		if err != nil {
			return err
		}
		checkout.Completed = append(checkout.Completed, result)
	}
	checkout.Running = []*Instance{}
	return nil
}

func (ctx *TestbedContext) NewCheckout(config *CheckoutConfig) (*Checkout, error) {
	checkout := &Checkout{
		Name: config.Name,
		Path: filepath.Join(ctx.Config.Workdir, "checkouts", config.Name),
	}
	log.Printf("[%s] Checking out", checkout.Name)
	if osutil.IsExist(checkout.Path) {
		return nil, fmt.Errorf("path %s already exists", checkout.Path)
	}
	repo := vcs.NewSyzkallerRepo(checkout.Path)
	commit, err := repo.Poll(config.Repo, config.Branch)
	if err != nil {
		return nil, fmt.Errorf("failed to checkout %s (%s): %s", config.Repo, config.Branch, err)
	}
	log.Printf("[%s] Done. Latest commit: %s", checkout.Name, commit)
	log.Printf("[%s] Building", checkout.Name)
	if _, err := osutil.RunCmd(time.Hour, checkout.Path, syz_instance.MakeBin); err != nil {
		return nil, fmt.Errorf("[%s] Make failed: %s", checkout.Name, err)
	}
	return checkout, nil
}
