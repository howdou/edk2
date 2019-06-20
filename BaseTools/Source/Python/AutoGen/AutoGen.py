## @file
# Generate AutoGen.h, AutoGen.c and *.depex files
#
# Copyright (c) 2007 - 2019, Intel Corporation. All rights reserved.<BR>
# Copyright (c) 2018, Hewlett Packard Enterprise Development, L.P.<BR>
# Copyright (c) 2019, American Megatrends, Inc. All rights reserved.<BR>
#
# SPDX-License-Identifier: BSD-2-Clause-Patent
#

## Import Modules
#
from __future__ import print_function
from __future__ import absolute_import
from Common.DataType import *

## Split command line option string to list
#
# subprocess.Popen needs the args to be a sequence. Otherwise there's problem
# in non-windows platform to launch command
#
def _SplitOption(OptionString):
    OptionList = []
    LastChar = " "
    OptionStart = 0
    QuotationMark = ""
    for Index in range(0, len(OptionString)):
        CurrentChar = OptionString[Index]
        if CurrentChar in ['"', "'"]:
            if QuotationMark == CurrentChar:
                QuotationMark = ""
            elif QuotationMark == "":
                QuotationMark = CurrentChar
            continue
        elif QuotationMark:
            continue

        if CurrentChar in ["/", "-"] and LastChar in [" ", "\t", "\r", "\n"]:
            if Index > OptionStart:
                OptionList.append(OptionString[OptionStart:Index - 1])
            OptionStart = Index
        LastChar = CurrentChar
    OptionList.append(OptionString[OptionStart:])
    return OptionList

#
# The priority list while override build option
#
PrioList = {"0x11111"  : 16,     #  TARGET_TOOLCHAIN_ARCH_COMMANDTYPE_ATTRIBUTE (Highest)
            "0x01111"  : 15,     #  ******_TOOLCHAIN_ARCH_COMMANDTYPE_ATTRIBUTE
            "0x10111"  : 14,     #  TARGET_*********_ARCH_COMMANDTYPE_ATTRIBUTE
            "0x00111"  : 13,     #  ******_*********_ARCH_COMMANDTYPE_ATTRIBUTE
            "0x11011"  : 12,     #  TARGET_TOOLCHAIN_****_COMMANDTYPE_ATTRIBUTE
            "0x01011"  : 11,     #  ******_TOOLCHAIN_****_COMMANDTYPE_ATTRIBUTE
            "0x10011"  : 10,     #  TARGET_*********_****_COMMANDTYPE_ATTRIBUTE
            "0x00011"  : 9,      #  ******_*********_****_COMMANDTYPE_ATTRIBUTE
            "0x11101"  : 8,      #  TARGET_TOOLCHAIN_ARCH_***********_ATTRIBUTE
            "0x01101"  : 7,      #  ******_TOOLCHAIN_ARCH_***********_ATTRIBUTE
            "0x10101"  : 6,      #  TARGET_*********_ARCH_***********_ATTRIBUTE
            "0x00101"  : 5,      #  ******_*********_ARCH_***********_ATTRIBUTE
            "0x11001"  : 4,      #  TARGET_TOOLCHAIN_****_***********_ATTRIBUTE
            "0x01001"  : 3,      #  ******_TOOLCHAIN_****_***********_ATTRIBUTE
            "0x10001"  : 2,      #  TARGET_*********_****_***********_ATTRIBUTE
            "0x00001"  : 1}      #  ******_*********_****_***********_ATTRIBUTE (Lowest)

## Base class for AutoGen
#
#   This class just implements the cache mechanism of AutoGen objects.
#
class AutoGen(object):
    # database to maintain the objects in each child class
    __ObjectCache = {}    # (BuildTarget, ToolChain, ARCH, platform file): AutoGen object

    ## Factory method
    #
    #   @param  Class           class object of real AutoGen class
    #                           (WorkspaceAutoGen, ModuleAutoGen or PlatformAutoGen)
    #   @param  Workspace       Workspace directory or WorkspaceAutoGen object
    #   @param  MetaFile        The path of meta file
    #   @param  Target          Build target
    #   @param  Toolchain       Tool chain name
    #   @param  Arch            Target arch
    #   @param  *args           The specific class related parameters
    #   @param  **kwargs        The specific class related dict parameters
    #
    @classmethod
    def GetCache(self):
        return AutoGen.__ObjectCache
    def __new__(cls, Workspace, MetaFile, Target, Toolchain, Arch, *args, **kwargs):
        # check if the object has been created
        Key = (Target, Toolchain, Arch, MetaFile)
        if Key in cls.__ObjectCache:
            # if it exists, just return it directly
            return cls.__ObjectCache[Key]
            # it didnt exist. create it, cache it, then return it
        RetVal = cls.__ObjectCache[Key] = super(AutoGen, cls).__new__(cls)
        return RetVal


    ## hash() operator
    #
    #  The file path of platform file will be used to represent hash value of this object
    #
    #   @retval int     Hash value of the file path of platform file
    #
    def __hash__(self):
        return hash(self.MetaFile)

    ## str() operator
    #
    #  The file path of platform file will be used to represent this object
    #
    #   @retval string  String of platform file path
    #
    def __str__(self):
        return str(self.MetaFile)

    ## "==" operator
    def __eq__(self, Other):
        return Other and self.MetaFile == Other

    @classmethod
    def Cache(cls):
        return cls.__ObjectCache

    ## Calculate the priority value of the build option
    #
    # @param    Key    Build option definition contain: TARGET_TOOLCHAIN_ARCH_COMMANDTYPE_ATTRIBUTE
    #
    # @retval   Value  Priority value based on the priority list.
    #
    def CalculatePriorityValue(self, Key):
        Target, ToolChain, Arch, CommandType, Attr = Key.split('_')
        PriorityValue = 0x11111
        if Target == TAB_STAR:
            PriorityValue &= 0x01111
        if ToolChain == TAB_STAR:
            PriorityValue &= 0x10111
        if Arch == TAB_STAR:
            PriorityValue &= 0x11011
        if CommandType == TAB_STAR:
            PriorityValue &= 0x11101
        if Attr == TAB_STAR:
            PriorityValue &= 0x11110
    
        return PrioList["0x%0.5x" % PriorityValue]


    ## Expand * in build option key
    #
    #   @param  Options     Options to be expanded
    #   @param  ToolDef     Use specified ToolDef instead of full version.
    #                       This is needed during initialization to prevent
    #                       infinite recursion betweeh BuildOptions,
    #                       ToolDefinition, and this function.
    #
    #   @retval options     Options expanded
    #
    def _ExpandBuildOption(self, Options, ModuleStyle=None, ToolDef=None):
        if not ToolDef:
            ToolDef = self.ToolDefinition
        BuildOptions = {}
        FamilyMatch  = False
        FamilyIsNull = True

        OverrideList = {}
        #
        # Construct a list contain the build options which need override.
        #
        for Key in Options:
            #
            # Key[0] -- tool family
            # Key[1] -- TARGET_TOOLCHAIN_ARCH_COMMANDTYPE_ATTRIBUTE
            #
            if (Key[0] == self.BuildRuleFamily and
                (ModuleStyle is None or len(Key) < 3 or (len(Key) > 2 and Key[2] == ModuleStyle))):
                Target, ToolChain, Arch, CommandType, Attr = Key[1].split('_')
                if (Target == self.BuildTarget or Target == TAB_STAR) and\
                    (ToolChain == self.ToolChain or ToolChain == TAB_STAR) and\
                    (Arch == self.Arch or Arch == TAB_STAR) and\
                    Options[Key].startswith("="):

                    if OverrideList.get(Key[1]) is not None:
                        OverrideList.pop(Key[1])
                    OverrideList[Key[1]] = Options[Key]

        #
        # Use the highest priority value.
        #
        if (len(OverrideList) >= 2):
            KeyList = list(OverrideList.keys())
            for Index in range(len(KeyList)):
                NowKey = KeyList[Index]
                Target1, ToolChain1, Arch1, CommandType1, Attr1 = NowKey.split("_")
                for Index1 in range(len(KeyList) - Index - 1):
                    NextKey = KeyList[Index1 + Index + 1]
                    #
                    # Compare two Key, if one is included by another, choose the higher priority one
                    #
                    Target2, ToolChain2, Arch2, CommandType2, Attr2 = NextKey.split("_")
                    if (Target1 == Target2 or Target1 == TAB_STAR or Target2 == TAB_STAR) and\
                        (ToolChain1 == ToolChain2 or ToolChain1 == TAB_STAR or ToolChain2 == TAB_STAR) and\
                        (Arch1 == Arch2 or Arch1 == TAB_STAR or Arch2 == TAB_STAR) and\
                        (CommandType1 == CommandType2 or CommandType1 == TAB_STAR or CommandType2 == TAB_STAR) and\
                        (Attr1 == Attr2 or Attr1 == TAB_STAR or Attr2 == TAB_STAR):

                        if self.CalculatePriorityValue(NowKey) > self.CalculatePriorityValue(NextKey):
                            if Options.get((self.BuildRuleFamily, NextKey)) is not None:
                                Options.pop((self.BuildRuleFamily, NextKey))
                        else:
                            if Options.get((self.BuildRuleFamily, NowKey)) is not None:
                                Options.pop((self.BuildRuleFamily, NowKey))

        for Key in Options:
            if ModuleStyle is not None and len (Key) > 2:
                # Check Module style is EDK or EDKII.
                # Only append build option for the matched style module.
                if ModuleStyle == EDK_NAME and Key[2] != EDK_NAME:
                    continue
                elif ModuleStyle == EDKII_NAME and Key[2] != EDKII_NAME:
                    continue
            Family = Key[0]
            Target, Tag, Arch, Tool, Attr = Key[1].split("_")
            # if tool chain family doesn't match, skip it
            if Tool in ToolDef and Family != "":
                FamilyIsNull = False
                if ToolDef[Tool].get(TAB_TOD_DEFINES_BUILDRULEFAMILY, "") != "":
                    if Family != ToolDef[Tool][TAB_TOD_DEFINES_BUILDRULEFAMILY]:
                        continue
                elif Family != ToolDef[Tool][TAB_TOD_DEFINES_FAMILY]:
                    continue
                FamilyMatch = True
            # expand any wildcard
            if Target == TAB_STAR or Target == self.BuildTarget:
                if Tag == TAB_STAR or Tag == self.ToolChain:
                    if Arch == TAB_STAR or Arch == self.Arch:
                        if Tool not in BuildOptions:
                            BuildOptions[Tool] = {}
                        if Attr != "FLAGS" or Attr not in BuildOptions[Tool] or Options[Key].startswith('='):
                            BuildOptions[Tool][Attr] = Options[Key]
                        else:
                            # append options for the same tool except PATH
                            if Attr != 'PATH':
                                BuildOptions[Tool][Attr] += " " + Options[Key]
                            else:
                                BuildOptions[Tool][Attr] = Options[Key]
        # Build Option Family has been checked, which need't to be checked again for family.
        if FamilyMatch or FamilyIsNull:
            return BuildOptions

        for Key in Options:
            if ModuleStyle is not None and len (Key) > 2:
                # Check Module style is EDK or EDKII.
                # Only append build option for the matched style module.
                if ModuleStyle == EDK_NAME and Key[2] != EDK_NAME:
                    continue
                elif ModuleStyle == EDKII_NAME and Key[2] != EDKII_NAME:
                    continue
            Family = Key[0]
            Target, Tag, Arch, Tool, Attr = Key[1].split("_")
            # if tool chain family doesn't match, skip it
            if Tool not in ToolDef or Family == "":
                continue
            # option has been added before
            if Family != ToolDef[Tool][TAB_TOD_DEFINES_FAMILY]:
                continue

            # expand any wildcard
            if Target == TAB_STAR or Target == self.BuildTarget:
                if Tag == TAB_STAR or Tag == self.ToolChain:
                    if Arch == TAB_STAR or Arch == self.Arch:
                        if Tool not in BuildOptions:
                            BuildOptions[Tool] = {}
                        if Attr != "FLAGS" or Attr not in BuildOptions[Tool] or Options[Key].startswith('='):
                            BuildOptions[Tool][Attr] = Options[Key]
                        else:
                            # append options for the same tool except PATH
                            if Attr != 'PATH':
                                BuildOptions[Tool][Attr] += " " + Options[Key]
                            else:
                                BuildOptions[Tool][Attr] = Options[Key]
        return BuildOptions