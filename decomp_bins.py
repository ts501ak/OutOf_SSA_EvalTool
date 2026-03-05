#!/usr/bin/env python3

import os
import sys
import gc
import argparse
import contextlib
from multiprocessing import cpu_count
from pebble import ProcessPool

from shared import (
    DEWOLF_DIR,
    SSA_ALGOS,
    DECOMP_MEM_LIMIT_GB,
    DECOMP_TIMEOUT_SECONDS,
    log_and_print,
    get_bin_file,
    get_dict_file,
    get_decomp_file,
    load_jobs,
    init_worker,
)

# Add the 'dewolf' directory to sys.path
sys.path.insert(0, str(DEWOLF_DIR))

# Import decompiler
try:
    from decompile import Decompiler #type: ignore
except ImportError:
    log_and_print("Error importing dewolf", print_file=sys.stderr)
    sys.exit(1)

def _decompile_func(args):
    bin = args.get("bin")
    func = args.get("func")
    fresh = args.get("fresh")
    ssa_algo = args.get("ssa_algo")

    bin_path = get_bin_file(bin);
    dict_path = get_dict_file(ssa_algo, bin, func)
    decomp_path = get_decomp_file(ssa_algo, bin, func)

    if (dict_path.exists() and decomp_path.exists()) and not fresh:
        return

    success = False
    decompiler = None
    os.environ["SSA_DICT_OUT"] = str(dict_path.absolute())
    try:
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                options = Decompiler.create_options()
                options.update({"out-of-ssa-translation.mode": ssa_algo})
                
                decompiler = Decompiler.from_path(bin_path)
                task, code = decompiler.decompile(func)
                success = not task.failed

        if not success:
            raise Exception(task.failure_origin)

        decomp_path.write_text(code)

    except Exception as e:
        log_and_print(f"[-] Error decompiling function {func} in {bin}: {e}", print_file=sys.stderr)
    finally:
        del decompiler
        gc.collect()

def decomp_bins(worker_count: int, decompile_timeout: int, mem_limit: int, fresh: bool = True):
    jobs = load_jobs()
    if(not jobs):
        log_and_print("[-] jobs.json not found! Try running prepare_jobs.py", print_file=sys.stderr)
        return

    for ssa_algo in SSA_ALGOS: 
        jobs = [{**d, "ssa_algo": ssa_algo, "fresh": fresh} for d in jobs]
        log_and_print(f"[*] Decompiling {len(jobs)} functions with ssa algorithm {ssa_algo} using {worker_count} workers...")
        with ProcessPool(max_workers=worker_count, initializer=init_worker, initargs=(mem_limit,)) as pool:
            future = pool.map(_decompile_func, jobs, timeout=decompile_timeout)
            try:
                for _ in future.result():
                    pass
            except Exception as e:
                print(f"[-] Error during decompilation pool execution: {e}", file=sys.stderr)
                gc.collect()

        log_and_print("")

def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-f", "--fresh",
        action=argparse.BooleanOptionalAction,
        help=f"Overwrite exisitng files (default: {False})"
    )
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes (default: {cpu_count()})"
    )
    parser.add_argument(
        "-t", "--decompile-timeout", 
        type=int, 
        default=DECOMP_TIMEOUT_SECONDS,
        help=f"Dewolf decompile timeout (default: {DECOMP_TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        "-m", "--mem-limit",
        type=int,
        default=DECOMP_MEM_LIMIT_GB,
        help=f"Memory limit for worker processes in GB (default: {DECOMP_MEM_LIMIT_GB} GB)"
    )
    args = parser.parse_args()
    decomp_bins(args.processes, args.decompile_timeout, args.mem_limit, args.fresh)

if __name__ == "__main__":
    main()
