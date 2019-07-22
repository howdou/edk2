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
try:
    from queue import Empty
except:
    from Queue import Empty
import traceback
import sys
from AutoGen.DataPipe import MemoryDataPipe
import logging

class LogAgent(threading.Thread):
    def __init__(self,log_q,log_level,log_file=None):
        super(LogAgent,self).__init__()
        self.log_q = log_q
        self.log_level = log_level
        self.log_file = log_file
    def InitLogger(self):
        # For DEBUG level (All DEBUG_0~9 are applicable)
        self._DebugLogger_agent = logging.getLogger("tool_debug_agent")
        _DebugFormatter = logging.Formatter("[%(asctime)s.%(msecs)d]: %(message)s", datefmt="%H:%M:%S")
        self._DebugLogger_agent.setLevel(self.log_level)
        _DebugChannel = logging.StreamHandler(sys.stdout)
        _DebugChannel.setFormatter(_DebugFormatter)
        self._DebugLogger_agent.addHandler(_DebugChannel)

        # For VERBOSE, INFO, WARN level
        self._InfoLogger_agent = logging.getLogger("tool_info_agent")
        _InfoFormatter = logging.Formatter("%(message)s")
        self._InfoLogger_agent.setLevel(self.log_level)
        _InfoChannel = logging.StreamHandler(sys.stdout)
        _InfoChannel.setFormatter(_InfoFormatter)
        self._InfoLogger_agent.addHandler(_InfoChannel)

        # For ERROR level
        self._ErrorLogger_agent = logging.getLogger("tool_error_agent")
        _ErrorFormatter = logging.Formatter("%(message)s")
        self._ErrorLogger_agent.setLevel(self.log_level)
        _ErrorCh = logging.StreamHandler(sys.stderr)
        _ErrorCh.setFormatter(_ErrorFormatter)
        self._ErrorLogger_agent.addHandler(_ErrorCh)

        if self.log_file:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            _Ch = logging.FileHandler(self.log_file)
            _Ch.setFormatter(_DebugFormatter)
            self._DebugLogger_agent.addHandler(_Ch)

            _Ch= logging.FileHandler(self.log_file)
            _Ch.setFormatter(_InfoFormatter)
            self._InfoLogger_agent.addHandler(_Ch)

            _Ch = logging.FileHandler(self.log_file)
            _Ch.setFormatter(_ErrorFormatter)
            self._ErrorLogger_agent.addHandler(_Ch)

    def run(self):
        self.InitLogger()
        while True:
            log_message = self.log_q.get()
            if log_message is None:
                break
            if log_message.name == "tool_error":
                self._ErrorLogger_agent.log(log_message.levelno,log_message.getMessage())
            elif log_message.name == "tool_info":
                self._InfoLogger_agent.log(log_message.levelno,log_message.getMessage())
            elif log_message.name == "tool_debug":
                self._DebugLogger_agent.log(log_message.levelno,log_message.getMessage())
            else:
                self._InfoLogger_agent.log(log_message.levelno,log_message.getMessage())

    def kill(self):
        self.log_q.put(None)
class AutoGenManager(threading.Thread):
    def __init__(self,autogen_workers, feedback_q):
        super(AutoGenManager,self).__init__()
        self.autogen_workers = autogen_workers
        self.feedback_q = feedback_q
        self.Status = True
    def run(self):
        try:
            while True:
                badnews = self.feedback_q.get()
                if badnews is None:
                    self.Status = False
                    self.TerminateWorkers()
                    break
        except Exception:
            return

    def kill(self):
        self.feedback_q.put(None)

    def TerminateWorkers(self):
        for w in self.autogen_workers:
            if w.is_alive():
                w.terminate()

class AutoGenWorkerInProcess(mp.Process):
    def __init__(self,module_queue,data_pipe_file_path,feedback_q,file_lock, share_data,log_q):
        mp.Process.__init__(self)
        self.module_queue = module_queue
        self.data_pipe_file_path =data_pipe_file_path
        self.data_pipe = None
        self.feedback_q = feedback_q
        self.PlatformMetaFileSet = {}
        self.file_lock = file_lock
        self.share_data = share_data
        self.log_q = log_q
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
            EdkLogger.LogClientInitialize(self.log_q)
            loglevel = self.data_pipe.Get("LogLevel")
            if not loglevel:
                loglevel = EdkLogger.INFO
            EdkLogger.SetLevel(loglevel)
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
            GlobalData.gBinCacheSource = self.data_pipe.Get("BinCacheSource")
            GlobalData.gBinCacheDest = self.data_pipe.Get("BinCacheDest")
            GlobalData.gCacheIR = self.data_pipe.Get("CacheIR")
            GlobalData.gEnableGenfdsMultiThread = self.data_pipe.Get("EnableGenfdsMultiThread")
            GlobalData.file_lock = self.file_lock
            module_count = 0
            FfsCmd = self.data_pipe.Get("FfsCommand")
            if FfsCmd is None:
                FfsCmd = {}
            GlobalData.FfsCmd = FfsCmd
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
                if GlobalData.gBinCacheSource:
                    Ma.GenModuleFilesHash(GlobalData.gCacheIR)
                    Ma.GenPreMakefileHash(GlobalData.gCacheIR)
                    if Ma.CanSkipbyPreMakefileCache(GlobalData.gCacheIR):
                       continue

                Ma.CreateCodeFile()
                Ma.CreateMakeFile(GenFfsList=FfsCmd.get((Ma.MetaFile.File, Ma.Arch),[]))

                if GlobalData.gBinCacheSource:
                    Ma.GenMakeHeaderFilesHash(GlobalData.gCacheIR)
                    Ma.GenMakeHash(GlobalData.gCacheIR)
                    if Ma.CanSkipbyMakeCache(GlobalData.gCacheIR):
                        continue
                    else:
                        Ma.PrintFirstMakeCacheMissFile(GlobalData.gCacheIR)
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
