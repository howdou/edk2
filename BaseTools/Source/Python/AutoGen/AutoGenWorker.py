## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
import multiprocessing as mp
from Common.Misc import PathClass
from AutoGen.ModuleAutoGen import ModuleAutoGen
from AutoGen.ModuleAutoGenHelper import WorkSpaceInfo
import Common.GlobalData as GlobalData
import os,time
import Common.EdkLogger as EdkLogger
from Common.MultipleWorkspace import MultipleWorkspace as mws

class AutoGenWorker(mp.Process):
    def __init__(self,module_queue,data_pipe):
        super(AutoGenWorker,self).__init__()
        self.module_queue = module_queue
        self.data_pipe = data_pipe
    
    def test_run(self):
        
        EdkLogger.Initialize()
        EdkLogger.SetLevel(EdkLogger.QUIET)
        
        begin = time.perf_counter()
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
        os.environ._data = self.data_pipe.Get("Env_Var")
        GlobalData.gWorkspace = workspacedir
        GlobalData.gDisableIncludePathCheck = False
        module_count = 0
        while not self.module_queue.empty():
            module_count += 1
            module_file,module_root,module_arch = self.module_queue.get()
#             begin = time.perf_counter()
            module_metafile = PathClass(module_file,module_root)
            arch = module_arch
            target = self.data_pipe.Get("P_Info").get("Target")
            toolchain = self.data_pipe.Get("P_Info").get("ToolChain")
            PlatformMetaFile = PathClass(self.data_pipe.Get("P_Info").get("ActivePlatform"),
                                         self.data_pipe.Get("P_Info").get("WorkspaceDir"))
            
            Ma = ModuleAutoGen(self.Wa,module_metafile,target,toolchain,arch,PlatformMetaFile,self.data_pipe)
            Ma.CreateCodeFile(True)
            Ma.CreateMakeFile()
            Ma.CreateAsBuiltInf()
#             print ("Processs ID: %d" % os.getpid(), module_file, time.perf_counter() - begin)
        print ("Processs ID: %d Run %d modules " % (os.getpid(),module_count), time.perf_counter() - begin)
    def run(self):
#         import cProfile,pstats
#         pr = cProfile.Profile()
#         pr.enable()
#         begin = time.perf_counter()
        self.test_run()
#         print (time.perf_counter() - begin)
#         pr.disable()
#         sortby = 'tottime'
#         ps = pstats.Stats(pr).sort_stats(sortby)
#         ps.print_stats(50)
        
        