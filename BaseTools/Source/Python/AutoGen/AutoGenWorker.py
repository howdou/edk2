## @file
# Create makefile for MS nmake and GNU make
#
# Copyright (c) 2019, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
from __future__ import absolute_import
import multiprocessing as mp
import threading
from Common.Misc import PathClass
from AutoGen.ModuleAutoGen import ModuleAutoGen
from AutoGen.ModuleAutoGenHelper import WorkSpaceInfo,AutoGenInfo
import Common.GlobalData as GlobalData
import Common.EdkLogger as EdkLogger
import os
from Common.MultipleWorkspace import MultipleWorkspace as mws
from AutoGen.AutoGen import AutoGen
from Workspace.WorkspaceDatabase import BuildDB
import time
from queue import Empty
import traceback
import sys
from AutoGen.DataPipe import MemoryDataPipe
class AutoGenManager(threading.Thread):
    def __init__(self,autogen_workers, feedback_q):
        super(AutoGenManager,self).__init__()
        self.autogen_workers = autogen_workers
        self.feedback_q = feedback_q
        self.terminate = False
        self.Status = True
    def run(self):
        try:
            while True:
                if self.terminate:
                    break
                if self.feedback_q.empty():
                    time.sleep(1)
                    continue
                badnews = self.feedback_q.get(False)
                if badnews:
                    print(badnews)
                    self.Status = False
                    self.TerminateWorkers()
                    break
        except Exception:
            return

    def kill(self):
        self.terminate = True

    def TerminateWorkers(self):
        for w in self.autogen_workers:
            if w.is_alive():
                w.terminate()

class AutoGenWorkerInProcess(mp.Process):
    def __init__(self,module_queue,data_pipe_file_path,feedback_q,file_lock, share_data):
        mp.Process.__init__(self)
        self.module_queue = module_queue
        self.data_pipe_file_path =data_pipe_file_path
        self.data_pipe = None
        self.feedback_q = feedback_q
        self.PlatformMetaFileSet = {}
        self.file_lock = file_lock
        self.share_data = share_data
    def GetPlatformMetaFile(self,filepath,root):
        try:
            return self.PlatformMetaFileSet[(filepath,root)]
        except:
            self.PlatformMetaFileSet[(filepath,root)]  = filepath
            return self.PlatformMetaFileSet[(filepath,root)]
    def run(self):
        try:
            taskname = "Init"
            with self.file_lock:
                if not os.path.exists(self.data_pipe_file_path):
                    self.feedback_q.put(taskname + ":" + "load data pipe %s failed." % self.data_pipe_file_path)
                self.data_pipe = MemoryDataPipe()
                self.data_pipe.load(self.data_pipe_file_path)
            EdkLogger.Initialize()
            loglevel = self.data_pipe.Get("LogLevel")
            if not loglevel:
                loglevel = EdkLogger.INFO
            EdkLogger.SetLevel(loglevel)
            logfile = self.data_pipe.Get("LogFile")
            if logfile:
                EdkLogger.SetLogFile(logfile)
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
            GlobalData.gDatabasePath = self.data_pipe.Get("DatabasePath")
            module_count = 0
            FfsCmd = self.data_pipe.Get("FfsCommand")
            if FfsCmd is None:
                FfsCmd = {}
            PlatformMetaFile = self.GetPlatformMetaFile(self.data_pipe.Get("P_Info").get("ActivePlatform"),
                                             self.data_pipe.Get("P_Info").get("WorkspaceDir"))
            while not self.module_queue.empty():
                module_count += 1
                module_file,module_root,module_path,module_basename,module_originalpath,module_arch,IsLib = self.module_queue.get()
                modulefullpath = os.path.join(module_root,module_file)
                taskname = " : ".join((modulefullpath,module_arch))
                module_metafile = PathClass(module_file,module_root)
                if module_path:
                    module_metafile.Path = module_path
                if module_basename:
                    module_metafile.BaseName = module_basename
                if module_originalpath:
                    module_metafile.OriginalPath = PathClass(module_originalpath,module_root)
                arch = module_arch
                target = self.data_pipe.Get("P_Info").get("Target")
                toolchain = self.data_pipe.Get("P_Info").get("ToolChain")
                Ma = ModuleAutoGen(self.Wa,module_metafile,target,toolchain,arch,PlatformMetaFile,self.data_pipe)
                Ma.IsLibrary = IsLib
                Ma.CreateCodeFile()
                Ma.CreateMakeFile(GenFfsList=FfsCmd.get((Ma.MetaFile.File, Ma.Arch),[]))
        except Empty:
            pass
        except:
            traceback.print_exc(file=sys.stdout)
            self.feedback_q.put(taskname)

    def printStatus(self):
        print("Processs ID: %d Run %d modules in AutoGen " % (os.getpid(),len(AutoGen.Cache())))
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
