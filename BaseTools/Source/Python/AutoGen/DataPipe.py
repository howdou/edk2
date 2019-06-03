## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#

from AutoGen.PlatformData import *
from Workspace.WorkspaceDatabase import BuildDB
from Workspace.WorkspaceCommon import GetModuleLibInstances
import Common.GlobalData as GlobalData

class DataPipe(object):
    def __init__(self, BuildDir=None):
        self.data_container = {}
        self.BuildDir = BuildDir
    
class MemoryDataPipe(DataPipe):

    def Get(self,key):
        return self.data_container.get(key)
    
    @property
    def DataContainer(self):
        return self.data_container
    @DataContainer.setter
    def DataContainer(self,data):
        self.data_container.update(data)

    def FillData(self,PlatformInfo):
        #Platform Pcds
        self.DataContainer = {
            "PLA_PCD" : [PCD_DATA(
            pcd.TokenCName,pcd.TokenSpaceGuidCName,pcd.Type,
            pcd.DatumType,pcd.SkuInfoList,pcd.DefaultValue,
            pcd.MaxDatumSize,pcd.UserDefinedDefaultStoresFlag,pcd.validateranges,
                 pcd.validlists,pcd.expressions,pcd.CustomAttribute,pcd.TokenValue) 
            for pcd in PlatformInfo.Platform.Pcds.values()]
            }
         
        #Platform Module Pcds
        ModulePcds = {}
        for m in PlatformInfo.Platform.Modules:
            m_pcds =  PlatformInfo.Platform.Modules[m].Pcds
            if m_pcds:
                ModulePcds[(m.File,m.Root)] = [PCD_DATA(
            pcd.TokenCName,pcd.TokenSpaceGuidCName,pcd.Type,
            pcd.DatumType,pcd.SkuInfoList,pcd.DefaultValue,
            pcd.MaxDatumSize,pcd.UserDefinedDefaultStoresFlag,pcd.validateranges,
                 pcd.validlists,pcd.expressions,pcd.CustomAttribute,pcd.TokenValue) 
            for pcd in PlatformInfo.Platform.Modules[m].Pcds.values()]
             
         
        self.DataContainer = {"MOL_PCDS":ModulePcds}
        
        #Module's Library Instance
        ModuleLibs = {}
        for m in PlatformInfo.Platform.Modules:
            module_obj = BuildDB.BuildObject[m,PlatformInfo.Arch,PlatformInfo.BuildTarget,PlatformInfo.ToolChain]
            Libs = GetModuleLibInstances(module_obj, PlatformInfo.Platform, BuildDB.BuildObject, PlatformInfo.Arch,PlatformInfo.BuildTarget,PlatformInfo.ToolChain)
            ModuleLibs[m] = Libs
        self.DataContainer = {"DEPS":ModuleLibs}
        
        #Platform BuildOptions
        
        platform_build_opt =  PlatformInfo.EdkIIBuildOption
        
        ToolDefinition = PlatformInfo.ToolDefinition
        module_build_opt = {}
        for m in PlatformInfo.Platform.Modules:
            ModuleTypeOptions, PlatformModuleOptions = PlatformInfo.GetGlobalBuildOptions(BuildDB.BuildObject[m,PlatformInfo.Arch,PlatformInfo.BuildTarget,PlatformInfo.ToolChain])
            if ModuleTypeOptions or PlatformModuleOptions:
                module_build_opt.update({(m.File,m.Root): {"ModuleTypeOptions":ModuleTypeOptions, "PlatformModuleOptions":PlatformModuleOptions}})
                
        self.DataContainer = {"PLA_BO":platform_build_opt,
                              "TOOLDEF":ToolDefinition,
                              "MOL_BO":module_build_opt
                              }
        
        
        
        #Platform Info
        PInfo = {
            "WorkspaceDir":PlatformInfo.Workspace.WorkspaceDir,
            "Target":PlatformInfo.BuildTarget,
            "ToolChain":PlatformInfo.Workspace.ToolChain,
            "BuildRuleFile":PlatformInfo.BuildRule,
            "Arch": PlatformInfo.Arch,
            "ArchList":PlatformInfo.Workspace.ArchList,
            "ActivePlatform":PlatformInfo.MetaFile
            }
        self.DataContainer = {'P_Info':PInfo}
        
        self.DataContainer = {'M_Name':PlatformInfo.UniqueBaseName}
        
        self.DataContainer = {"ToolChainFamily": PlatformInfo.ToolChainFamily}
        
        self.DataContainer = {"BuildRuleFamily": PlatformInfo.BuildRuleFamily}
        
        self.DataContainer = {"MixedPcd":GlobalData.MixedPcd}
        
        self.DataContainer = {"BuildOptPcd":GlobalData.MixedPcd}
