## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
from __future__ import absolute_import
import multiprocessing as mp
from Common.Misc import PathClass
from AutoGen.ModuleAutoGen import ModuleAutoGen
from AutoGen.ModuleAutoGenHelper import WorkSpaceInfo,AutoGenInfo
import Common.GlobalData as GlobalData
import os,time
import Common.EdkLogger as EdkLogger
from Common.MultipleWorkspace import MultipleWorkspace as mws
import threading
from AutoGen.AutoGen import AutoGen
from Workspace.WorkspaceDatabase import BuildDB
class Worker():
    def __init__(self,module_queue,data_pipe,share_data):
        self.module_queue = module_queue
        self.data_pipe = data_pipe
        self.share_data = share_data
    def test_run(self):

        target = self.data_pipe.Get("P_Info").get("Target")
        toolchain = self.data_pipe.Get("P_Info").get("ToolChain")
        archlist = self.data_pipe.Get("P_Info").get("ArchList")
        
        active_p = self.data_pipe.Get("P_Info").get("ActivePlatform")
        workspacedir = self.data_pipe.Get("P_Info").get("WorkspaceDir")
        PackagesPath = os.getenv("PACKAGES_PATH")
        mws.setWs(workspacedir, PackagesPath)
        self.Wa = WorkSpaceInfo(
            workspacedir,active_p,target,toolchain,archlist
            )
        GlobalData.gGlobalDefines = self.data_pipe.Get("G_defines")
        GlobalData.gCommandLineDefines = self.data_pipe.Get("CL_defines")
        os.environ._data = self.data_pipe.Get("Env_Var")
        GlobalData.gWorkspace = workspacedir
        GlobalData.gDisableIncludePathCheck = False
        GlobalData.gFdfParser = self.data_pipe.Get("FdfParser")
        module_count = 0
        FfsCmd = self.data_pipe.Get("FfsCommand")
        if FfsCmd is None:
            FfsCmd = {}
        while not self.module_queue.empty():
            module_count += 1
            module_file,module_root,module_arch,IsLib = self.module_queue.get()
#             begin = time.perf_counter()
            module_metafile = PathClass(module_file,module_root)
            arch = module_arch
            target = self.data_pipe.Get("P_Info").get("Target")
            toolchain = self.data_pipe.Get("P_Info").get("ToolChain")
            PlatformMetaFile = PathClass(self.data_pipe.Get("P_Info").get("ActivePlatform"),
                                         self.data_pipe.Get("P_Info").get("WorkspaceDir"))
            
            Ma = ModuleAutoGen(self.Wa,module_metafile,target,toolchain,arch,PlatformMetaFile,self.data_pipe)
            Ma.IsLibrary = IsLib

            # print("GlobalData.gCacheSource = %s " % GlobalData.gCacheSource)
            # print("GlobalData.gCacheDest = %s " % GlobalData.gCacheDest)

            if not self.ignore_make:
                Ma.CreateCodeFile()
                Ma.CreateMakeFile(GenFfsList=FfsCmd.get((Ma.MetaFile.File, Ma.Arch),[]))
                Ma.GenLibHashChainInChildProcess(self.share_data)
            else:
                Ma.GenDriverHashInChildProcess(self.share_data)
                Ma.SaveHashChainFileToCacheInChildProcess(self.share_data)
                Ma.CanSkipbyMakeCacheInChildProcess(self.share_data)
                Ma.PrintFirstCacheMissFileInChildProcess(self.share_data)

            #self.share_data[(Ma.MetaFile.Path, Ma.Arch)]= str(Ma)
            #print(str(Ma))
            #EdkLogger.quiet("EdkLogger.quiet: %s" % str(Ma))


class AutoGenWorkerInThread(threading.Thread,Worker):
    def __init__(self,module_queue,data_pipe):
        threading.Thread.__init__(self)
        Worker.__init__(self,module_queue,data_pipe)
        self.module_queue = module_queue
        self.data_pipe = data_pipe
    
    def run(self):
#         import cProfile,pstats
#         pr = cProfile.Profile()
#         pr.enable()
#         begin = time.perf_counter()
        self.test_run()
#         print (time.perf_counter() - begin)
#         pr.disable()
#         sortby = 'tottime'
#         with open('statistics_%d.txt' % os.getpid(), 'w') as stream:
#             ps = pstats.Stats(pr,stream=stream).sort_stats(sortby)
#             ps.print_stats(50)

class AutoGenWorkerInProcess(mp.Process,Worker):
    def __init__(self,module_queue,data_pipe,share_data,ignore_make=False):
        mp.Process.__init__(self)
        Worker.__init__(self,module_queue,data_pipe,share_data)
        self.module_queue = module_queue
        self.data_pipe = data_pipe
        self.share_data = share_data
        self.ignore_make = ignore_make

    def printStatus(self):
        print("Processs ID: %d Run %d modules in AutoGen " % (os.getpid(),len(AutoGen.GetCache())))
        print("Processs ID: %d Run %d modules in AutoGenInfo " % (os.getpid(),len(AutoGenInfo.GetCache())))
        groupobj = {}
        for buildobj in BuildDB.BuildObject.GetCache().values():
            if str(buildobj).lower().endswith("dec"):
                try:
                    groupobj['dec'].append(str(buildobj))
                except:
                    groupobj['dec'] = [str(buildobj)]
            if str(buildobj).lower().endswith("dsc"):
                try:
                    groupobj['dsc'].append(str(buildobj))
                except:
                    groupobj['dsc'] = [str(buildobj)]

            if str(buildobj).lower().endswith("inf"):
                try:
                    groupobj['inf'].append(str(buildobj))
                except:
                    groupobj['inf'] = [str(buildobj)]

        print("Processs ID: %d Run %d pkg in WDB " % (os.getpid(),len(groupobj.get("dec",[]))))
        print("Processs ID: %d Run %d pla in WDB " % (os.getpid(),len(groupobj.get("dsc",[]))))
        print("Processs ID: %d Run %d inf in WDB " % (os.getpid(),len(groupobj.get("inf",[]))))
    
    def run(self):
#         import cProfile,pstats
#         pr = cProfile.Profile()
#         pr.enable()
#         begin = time.perf_counter()
        EdkLogger.Initialize()
        EdkLogger.SetLevel(EdkLogger.QUIET)
        self.test_run()
        self.printStatus()
#         print (time.perf_counter() - begin)
#         pr.disable()
#         sortby = 'tottime'
#         with open('statistics_%d.txt' % os.getpid(), 'w') as stream:
#             ps = pstats.Stats(pr,stream=stream).sort_stats(sortby)
#             ps.print_stats(50)
