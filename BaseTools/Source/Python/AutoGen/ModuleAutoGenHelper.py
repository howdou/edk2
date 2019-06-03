## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
from Workspace.WorkspaceDatabase import WorkspaceDatabase
from Common.caching import cached_property
from AutoGen.BuildEngine import BuildRule,AutoGenReqBuildRuleVerNum
from AutoGen.AutoGen import AutoGen
import os

#
#This class is the pruned WorkSpaceAutoGen for ModuleAutoGen in multiple thread
#
class WorkSpaceInfo(AutoGen):
    def __init__(self,Workspace, MetaFile, Target, ToolChain, Arch):
        self._SrcTimeStamp = ""
        self.Db = WorkspaceDatabase()
        self.BuildDatabase = self.Db.BuildObject
        self.Target = Target
        self.ToolChain = ToolChain
        self.WorkspaceDir = Workspace
        self.ActivePlatform = MetaFile
        self.ArchList = Arch


class PlatformInfo(AutoGen):
    def __init__(self, Workspace, MetaFile, Target, ToolChain, Arch,DataPipe):
        self.Wa = Workspace
        self.WorkspaceDir = self.Wa.WorkspaceDir
        self.MetaFile = MetaFile
        self.Arch = Arch
        self.Target = Target
        self.ToolChain = ToolChain
        self.Platform = self.Wa.BuildDatabase[self.MetaFile, self.Arch, self.Target, self.ToolChain]

        self.ToolChainFamily = None
        self.BuildRuleFamily = None

        self.SourceDir = MetaFile.SubDir
        self.DataPipe = DataPipe
    def LoadToolDefine(self):
        pass

    def LoadBuildCommand(self):
        pass

    def LoadPackageList(self):
        pass

    @cached_property
    def PackageList(self):
        return self.LoadPackageList()

    ## Return the directory to store all intermediate and final files built
    @cached_property
    def BuildDir(self):
        if os.path.isabs(self.OutputDir):
            RetVal = os.path.join(
                                os.path.abspath(self.OutputDir),
                                self.Target + "_" + self.ToolChain,
                                )
        else:
            RetVal = os.path.join(
                                self.WorkspaceDir,
                                self.OutputDir,
                                self.Target + "_" + self.ToolChain,
                                )
        return RetVal

    ## Return the build output directory platform specifies
    @cached_property
    def OutputDir(self):
        return self.Platform.OutputDirectory

    ## Return platform name
    @cached_property
    def Name(self):
        return self.Platform.PlatformName

    ## Return meta-file GUID
    @cached_property
    def Guid(self):
        return self.Platform.Guid

    ## Return platform version
    @cached_property
    def Version(self):
        return self.Platform.Version

    ## Return paths of tools
    @cached_property
    def ToolDefinition(self):
        return self.LoadToolDefine()

    ## Return build command string
    #
    #   @retval     string  Build command string
    #
    @cached_property
    def BuildCommand(self):
        return self.LoadBuildCommand()

    @cached_property
    def PcdTokenNumber(self):
        return self.LoadPcdTokenNumber
        
    def ApplyPcdSetting(self,Module, Pcds):
        return list(Pcds.values())

    def Pcds(self):
        pass

    def ApplyBuildOptions(self):
        pass

    def ApplyLibraryInstance(self,Modules):
        return []
    
    ## Parse build_rule.txt in Conf Directory.
    #
    #   @retval     BuildRule object
    #
    @cached_property
    def BuildRule(self):
        WInfo = self.DataPipe.Get("P_Info")
        BuildRuleFile = WInfo.get("BuildRuleFile") 
        RetVal = BuildRule(BuildRuleFile)
        if RetVal._FileVersion == "":
            RetVal._FileVersion = AutoGenReqBuildRuleVerNum
        return RetVal