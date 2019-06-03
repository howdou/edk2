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

