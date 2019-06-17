import pickle
import queue

from Common.Misc import PathClass
from AutoGen.ModuleAutoGen import ModuleAutoGen
from AutoGen.ModuleAutoGenHelper import WorkSpaceInfo
import Common.GlobalData as GlobalData
import os,time
import Common.EdkLogger as EdkLogger
from Common.MultipleWorkspace import MultipleWorkspace as mws
from AutoGen.DataPipe import MemoryDataPipe
import multiprocessing as mp
from AutoGen.AutoGenWorker import AutoGenWorkerInThread, AutoGenWorkerInProcess
from Workspace.WorkspaceDatabase import BuildDB

def standalone(gloabl_vars_path,tasks_path):
    with open(gloabl_vars_path,"rb") as fd:
        data_pipe = MemoryDataPipe()
        data_pipe.data_container = pickle.load(fd)
    taskq = queue.Queue()
    count = 1
    with open(tasks_path,"r") as fw:
        lines = fw.readlines()
        for line in lines:
            path,root,arch,islib = line.split(",")
            taskq.put((path,root,arch,bool(islib)))
            if count == 256:
                break
            count += 1
            
    EdkLogger.Initialize()
    EdkLogger.SetLevel(EdkLogger.QUIET)
    
    begin = time.perf_counter()
    target = data_pipe.Get("P_Info").get("Target")
    toolchain = data_pipe.Get("P_Info").get("ToolChain")
    archlist = data_pipe.Get("P_Info").get("ArchList")
    
    active_p = data_pipe.Get("P_Info").get("ActivePlatform")
    workspacedir = data_pipe.Get("P_Info").get("WorkspaceDir")
    PackagesPath = os.getenv("PACKAGES_PATH")
    mws.setWs(workspacedir, PackagesPath)
    Wa = WorkSpaceInfo(
        workspacedir,active_p,target,toolchain,archlist
        )
    GlobalData.gGlobalDefines = data_pipe.Get("G_defines")
    GlobalData.gCommandLineDefines = data_pipe.Get("CL_defines")
    os.environ._data = data_pipe.Get("Env_Var")
    GlobalData.gWorkspace = workspacedir
    GlobalData.gDisableIncludePathCheck = False
    module_count = 0
    FfsCmd = data_pipe.Get("FfsCommand")
    if FfsCmd is None:
        FfsCmd = {}
    print("Setup Global Vars: ",(time.perf_counter() - begin))
    begin = time.perf_counter()
    while not taskq.empty():
        module_count += 1
        module_file,module_root,module_arch,IsLib = taskq.get()
#             begin = time.perf_counter()
        module_metafile = PathClass(module_file,module_root)
        arch = module_arch
        target = data_pipe.Get("P_Info").get("Target")
        toolchain = data_pipe.Get("P_Info").get("ToolChain")
        PlatformMetaFile = PathClass(data_pipe.Get("P_Info").get("ActivePlatform"),
                                     data_pipe.Get("P_Info").get("WorkspaceDir"))
        
        Ma = ModuleAutoGen(Wa,module_metafile,target,toolchain,arch,PlatformMetaFile,data_pipe)
        Ma.IsLibrary = IsLib
        Ma.CreateCodeFile()
        Ma.CreateMakeFile(GenFfsList=FfsCmd.get((Ma.MetaFile.File, Ma.Arch),[]))

    print("Create  module autogen: ",(time.perf_counter() - begin))
    begin = time.perf_counter()
    print ("Processs ID: %d Run %d modules " % (os.getpid(),module_count), time.perf_counter() - begin)


def MultipleThread(gloabl_vars_path,tasks_path):
    with open(gloabl_vars_path,"rb") as fd:
        data_pipe = MemoryDataPipe()
        data_pipe.data_container = pickle.load(fd)
    taskq = queue.Queue()
    count = 1
    BuildDatabase = BuildDB.BuildObject
    workspacedir = data_pipe.Get("P_Info").get("WorkspaceDir")
    PackagesPath = os.getenv("PACKAGES_PATH")
    mws.setWs(workspacedir, PackagesPath)

    GlobalData.gGlobalDefines = data_pipe.Get("G_defines")
    GlobalData.gCommandLineDefines = data_pipe.Get("CL_defines")
    os.environ._data = data_pipe.Get("Env_Var")
    GlobalData.gWorkspace = workspacedir
    GlobalData.gDisableIncludePathCheck = False
    Pinfo = data_pipe.Get("P_Info") 
    WorkspaceDir = Pinfo.get("WorkspaceDir")
    Target = Pinfo.get("Target")
    ToolChain = Pinfo.get("ToolChain")
    ArchList = Pinfo.get("ArchList")
    ActivePlatform = Pinfo.get("ActivePlatform")
    GlobalData.gGlobalDefines['WORKSPACE'] = WorkspaceDir
    for arch in ArchList:
        pb = BuildDatabase[PathClass(ActivePlatform,WorkspaceDir),arch,Target,ToolChain]
        pb.Modules
    BuildDatabase[PathClass(ActivePlatform,WorkspaceDir),"COMMON",Target,ToolChain].Modules
    with open(tasks_path,"r") as fw:
        lines = fw.readlines()
        for line in lines:
            path,root,arch,islib = line.split(",")
            taskq.put((path,root,arch,bool(islib)))
            BuildDatabase[PathClass(path,root),arch,Target,ToolChain]
            if count == 256:
                break
            count += 1
    
    auto_workers = [AutoGenWorkerInThread(taskq,data_pipe) for i in range(4)]        
    for w in auto_workers:
        w.start()
    
    for w in auto_workers:
        w.join()
        
def MultipleProcess(gloabl_vars_path,tasks_path):
    with open(gloabl_vars_path,"rb") as fd:
        data_pipe = MemoryDataPipe()
        data_pipe.data_container = pickle.load(fd)
    taskq = mp.Queue()
    count = 1
    
    with open(tasks_path,"r") as fw:
        lines = fw.readlines()
        for line in lines:
            path,root,arch,islib = line.split(",")
            taskq.put((path,root,arch,bool(islib)))
            if count == 256:
                break
            count += 1
    
    auto_workers = [AutoGenWorkerInProcess(taskq,data_pipe) for i in range(4)]        
    for w in auto_workers:
        w.start()
    
    for w in auto_workers:
        w.join()
    
if __name__ == "__main__":
    gloabl_vars_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\GlobalVar_Ovmf_IA32.bin"
    tasks_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\Ovmf_files_IA32.txt"
    gloabl_vars_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\GlobalVar_Ovmf_X64.bin"
    tasks_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\Ovmf_files_X64.txt"
    
    begin = time.perf_counter()
#     
#     MultipleThread(gloabl_vars_path, tasks_path)
    MultipleProcess(gloabl_vars_path, tasks_path)
#     
    print("Create  module autogen: ",(time.perf_counter() - begin))
#     import cProfile,pstats
#     pr = cProfile.Profile()
#     pr.enable()
    begin = time.perf_counter()
#     standalone(gloabl_vars_path, tasks_path)
    print (time.perf_counter() - begin)
#     pr.disable()
#     sortby = 'tottime'
#     ps = pstats.Stats(pr).sort_stats(sortby)
#     ps.print_stats(50)
    
#     gloabl_vars_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\GlobalVar_Ovmf_X64.bin"
#     tasks_path = r"C:\BobFeng\ToolDev\EDKIITrunk\BobEdk2\edk2\Ovmf_files_X64.txt"
#     standalone(gloabl_vars_path, tasks_path)    
    