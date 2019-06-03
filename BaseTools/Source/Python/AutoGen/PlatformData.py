## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#

class PCD_DATA():
    def __init__(self,TokenCName,TokenSpaceGuidCName,Type,DatumType,SkuInfoList,DefaultValue):
        self.TokenCName = TokenCName 
        self.TokenSpaceGuidCName = TokenSpaceGuidCName
        self.Type = Type
        self.DatumType = DatumType
        self.SkuInfoList = SkuInfoList
        self.DefaultValue = DefaultValue

class MODULE_PCD_DATA(PCD_DATA):
    def __init__(self,TokenCName,TokenSpaceGuidCName,Type,DatumType,SkuInfoList,DefaultValue,ModulePath):
        super(self,MODULE_PCD_DATA).__init__(TokenCName,TokenSpaceGuidCName,Type,DatumType,SkuInfoList,DefaultValue)
        self.ModulePath = ModulePath
        
class MODULE_INFO():
    def __init__(self):
        self.Dependency = []
        self.DscModulePcd = None
        self.DscModuleBuildOptions = None

class BUILD_CONFIG():
    def __init__(self):
        self.build_rule = None
        self.build_tool = None
        self.Build_conf = None
        
class PLATFORM_INFO():
    def __init__(self):
        self.ArchList = []
        self.Target = ""
        self.ToolChain = ""