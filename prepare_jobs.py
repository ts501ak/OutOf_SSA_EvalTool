#!/usr/bin/env python3

import re
import os
import sys
import argparse
import contextlib
from typing import Dict, List 
from pebble import ProcessPool
from multiprocessing import cpu_count

from shared import (
    DEWOLF_DIR,
    BINS_DIR,
    SSA_ALGOS,
    RES_DIR,
    NAMES_TO_IGNORE,
    MEM_LIMIT_GB,
    log_and_print,
    init_worker,
    get_res_dir,
    get_res_bin_dir,
    save_jobs,
    clear_and_create_dir,
)

# Add the 'dewolf' directory to sys.path
sys.path.insert(0, str(DEWOLF_DIR))

# Import decompiler
try:
    from decompile import Decompiler #type: ignore
except ImportError:
    log_and_print("Error importing dewolf", print_file=sys.stderr)
    sys.exit(1)

SUB_PATTERN = re.compile(r"^(?:j_)?sub_[a-f0-9]+$")

def _init_dirs(bin_names: List[str]):
    clear_and_create_dir(RES_DIR)
    for ssa_algo in SSA_ALGOS:
        clear_and_create_dir(get_res_dir(ssa_algo))

    for bin_name in bin_names:
        for ssa_algo in SSA_ALGOS:
            clear_and_create_dir(get_res_bin_dir(ssa_algo, bin_name))

def _prepare_jobs_for_binary(bin_name: str) -> List[Dict[str, str]]:
    bin_path = BINS_DIR / bin_name
        
    functions = []
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            decompiler = Decompiler.from_path(bin_path)
            functions = decompiler._frontend.get_all_function_names()

    ret = []
    for func_name in functions:
        if SUB_PATTERN.fullmatch(func_name):
            continue

        ret.append({"bin": bin_name, "func": func_name}) 

    return ret

def prepare_jobs(worker_count: int, mem_limit: int):
    jobs = []
    bin_names = [f.name for f in BINS_DIR.iterdir() if f.name not in NAMES_TO_IGNORE]

    _init_dirs(bin_names)
    log_and_print(f"[*] Preparing jobs for {len(bin_names)} binaries using {worker_count} workers...")

    with ProcessPool(max_workers=worker_count, initializer=init_worker, initargs=(mem_limit, )) as pool:
        iterator = pool.map(_prepare_jobs_for_binary, bin_names).result()
        for bin in bin_names:
            try:
                res = next(iterator)
                jobs.extend(res)
            except StopIteration:
                break
            except Exception as e:
                log_and_print(f"[-] Error during job preparation for {bin}: {e}", print_file=sys.stderr)

    log_and_print("")
    save_jobs(jobs) 

def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes (default: {cpu_count()})"
    )
    parser.add_argument(
        "-m", "--mem-limit",
        type=int,
        default=MEM_LIMIT_GB,
        help=f"Memory limit for worker processes in GB (default: {MEM_LIMIT_GB}GB)"
    )

    args = parser.parse_args()
    prepare_jobs(args.processes, args.mem_limit)

if __name__ == "__main__":
    main()
