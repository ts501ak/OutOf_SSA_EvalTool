#!/usr/bin/env python3

import re
import gc
import os
import sys
import argparse
import contextlib
from pathlib import Path
from typing import Dict, List 
from pebble import ProcessPool
from multiprocessing import cpu_count

from shared import (
    DEWOLF_DIR,
    SRC_DIR,
    BINS_DIR,
    SSA_ALGOS,
    NAMES_TO_IGNORE,
    MEM_LIMIT_GB,
    log_and_print,
    init_worker,
    get_base_dir,
    get_decomp_dir,
    get_src_func_dir,
    get_decomp_func_dir,
    get_res_dir,
    get_decomp_bin_dir,
    get_src_func_bin_dir,
    get_decomp_func_bin_dir,
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
    for ssa_algo in SSA_ALGOS:
        clear_and_create_dir(get_base_dir(ssa_algo))
        clear_and_create_dir(get_decomp_dir(ssa_algo))
        clear_and_create_dir(get_src_func_dir(ssa_algo)) 
        clear_and_create_dir(get_decomp_func_dir(ssa_algo))
        clear_and_create_dir(get_res_dir(ssa_algo))

    for bin_name in bin_names:
        for ssa_algo in SSA_ALGOS:
            clear_and_create_dir(get_decomp_bin_dir(ssa_algo, bin_name))
            clear_and_create_dir(get_decomp_func_bin_dir(ssa_algo, bin_name))
            clear_and_create_dir(get_src_func_bin_dir(ssa_algo, bin_name))
            clear_and_create_dir(get_res_bin_dir(ssa_algo, bin_name))


def _prepare_jobs_for_binary(bin_name: str) -> List[Dict[str, str]]:
    ret = []
    decompiler = None
    try:
        bin_path = BINS_DIR / bin_name
        src_path = SRC_DIR / (bin_name + ".c")
        if(not src_path.exists()):
            raise FileNotFoundError(f"src file {bin_name}.c not found!")
        
        functions = []
        try:
            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    decompiler = Decompiler.from_path(bin_path)
                    functions = decompiler._frontend.get_all_function_names()
        except Exception as e:
            log_and_print(f"[-] Error obtaining functions for binary {bin_name}: {e}", print_file=sys.stderr)

        for func_name in functions:
            if SUB_PATTERN.fullmatch(func_name):
                continue

            ret.append(
                {
                    "bin": bin_name,
                    "func": func_name,
                }
            ) 
    except Exception as e:
        log_and_print(f"[-] Error preparing jobs for binary {bin_name}: {e}", print_file=sys.stderr)
    finally:
        del decompiler
        gc.collect()

    return ret

def prepare_jobs(worker_count: int, mem_limit: int):
    jobs = []
    args = [f.name for f in BINS_DIR.iterdir() if f.name not in NAMES_TO_IGNORE]

    _init_dirs(args)
    log_and_print(f"[*] Preparing jobs for {len(args)} binaries using {worker_count} workers...")

    with ProcessPool(max_workers=worker_count, initializer=init_worker, initargs=(mem_limit, )) as pool:
        future = pool.map(_prepare_jobs_for_binary, args)
        try:
            for res in future.result():
                jobs.extend(res)
        except Exception as e:
            log_and_print(f"[-] Error during job preparation: {e}", print_file=sys.stderr)

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
        help=f"Memory limit for worker processes in GB (default: {MEM_LIMIT_GB} GB)"
    )

    args = parser.parse_args()
    prepare_jobs(args.processes, args.mem_limit)

if __name__ == "__main__":
    main()
