## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
import os

class ModuleBuildCacheIR():
    def __init__(self, Path, Arch):
        self.ModulePath = Path
        self.ModuleArch = Arch
        self.ModuleFilesHashDigest = None
        self.ModuleFilesHashHexDigest = None
        self.ModuleFilesChain = []
        self.PreMakefileHashHexDigest = None
        self.CreateCodeFileDone = False
        self.CreateMakeFileDone = False
        self.MakefilePath = None
        self.DependencyHeaderFileSet = None
        self.MakeHeaderFilesHashChain = None
        self.MakeHeaderFilesHashDigest = None
        self.MakeHeaderFilesHashChain = []
        self.MakeHashDigest = None
        self.MakeHashHexDigest = None
        self.MakeHashChain = []
        self.PreMakeCacheHit = False
        self.MakeCacheHit = False
