"""Local serial worker admission and measured process resources.

POSIX retains the original affinity/3 GiB AS/40-second CPU policy. Windows
uses a native Job Object: one process, 3 GiB committed process memory, 40
seconds process user time, kill on close, and one logical CPU affinity.
These memory/CPU definitions differ; neither is a measured per-method peak.
The parent runner separately enforces its existing 44-second wall deadline.
"""
from __future__ import annotations
import json, os, runpy, sys, time

_job = None

def apply_limits():
    global _job
    if os.name != 'nt':
        import resource
        if hasattr(os,'sched_setaffinity'):
            os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
        resource.setrlimit(resource.RLIMIT_CPU,(40,45))
        return
    if _job is not None:
        return
    import ctypes as c
    from ctypes import wintypes as w
    class Basic(c.Structure):
        _fields_=[('process_time',c.c_longlong),('job_time',c.c_longlong),
                  ('flags',w.DWORD),('minimum_ws',c.c_size_t),('maximum_ws',c.c_size_t),
                  ('active_processes',w.DWORD),('affinity',c.c_size_t),
                  ('priority',w.DWORD),('scheduling',w.DWORD)]
    class IO(c.Structure):
        _fields_=[(name,c.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class Extended(c.Structure):
        _fields_=[('basic',Basic),('io',IO),('process_memory',c.c_size_t),
                  ('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
    k=c.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=w.HANDLE
    k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
    k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
    k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
    k.GetProcessAffinityMask.argtypes=[w.HANDLE,c.POINTER(c.c_size_t),c.POINTER(c.c_size_t)]
    k.SetProcessAffinityMask.argtypes=[w.HANDLE,c.c_size_t]
    process=k.GetCurrentProcess(); process_mask=c.c_size_t(); system_mask=c.c_size_t()
    def checked(value):
        if not value: raise c.WinError(c.get_last_error())
        return value
    checked(k.GetProcessAffinityMask(process,c.byref(process_mask),c.byref(system_mask)))
    checked(k.SetProcessAffinityMask(process,process_mask.value & -process_mask.value))
    handle=checked(k.CreateJobObjectW(None,None)); limits=Extended()
    limits.basic.process_time=40*10_000_000
    limits.basic.flags=0x2|0x8|0x100|0x2000
    limits.basic.active_processes=1;limits.process_memory=3*1024**3
    checked(k.SetInformationJobObject(handle,9,c.byref(limits),c.sizeof(limits)))
    checked(k.AssignProcessToJobObject(handle,process))
    _job=handle  # Kept open until process exit, not a capability for another PID.

def peak_rss_kib():
    if os.name != 'nt':
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value//1024 if sys.platform=='darwin' else value
    import ctypes as c
    from ctypes import wintypes as w
    class Memory(c.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(name,c.c_size_t) for name in
            ('peak_ws','working_set','peak_paged_pool','paged_pool','peak_nonpaged_pool',
             'nonpaged_pool','pagefile','peak_pagefile')]
    memory=Memory();memory.cb=c.sizeof(memory)
    k=c.WinDLL('kernel32',use_last_error=True); k.GetCurrentProcess.restype=w.HANDLE
    api=c.WinDLL('psapi',use_last_error=True)
    api.GetProcessMemoryInfo.argtypes=[w.HANDLE,c.c_void_p,w.DWORD]
    if not api.GetProcessMemoryInfo(k.GetCurrentProcess(),c.byref(memory),memory.cb):
        raise c.WinError(c.get_last_error())
    return memory.peak_ws//1024

def main():
    apply_limits()
    args=sys.argv[1:]
    if args[:1]==['--']:args=args[1:]
    try:
        if args[:1]==['-m'] and len(args)>1:
            sys.argv=args[1:];runpy.run_module(args[1],run_name='__main__',alter_sys=True)
        elif args:
            sys.argv=args;runpy.run_path(args[0],run_name='__main__')
        else: raise ValueError('worker command required')
    finally:
        print('P052_PROCESS_METRICS '+json.dumps(dict(cpu_seconds=time.process_time(),
              peak_rss_kib=peak_rss_kib())),flush=True)
if __name__=='__main__':
    # The command and the imported campaign must share the same limit handle.
    sys.modules['provenance.resources']=sys.modules[__name__]
    main()
