#!/usr/bin/env python3

import gc
import sys
import argparse
from pathlib import Path
from typing import Dict, List 
from pebble import ProcessPool
from multiprocessing import cpu_count


from shared import (
    BASE_DIR,
    DEWOLF_DIR,
    SRC_DIR,
    RES_DIR,
    BINS_DIR,
    DECOMP_DIR,
    SRC_FUNC_DIR,
    DECOMP_FUNC_DIR,
    NAMES_TO_IGNORE,
    GRAPH_EDIT_DISTANCE_TIMEOUT,
    save_jobs,
    create_dir,
    clear_and_create_dir,
)

# Add the 'dewolf' directory to sys.path
sys.path.insert(0, str(DEWOLF_DIR))

# Import decompiler
try:
    from decompile import Decompiler #type: ignore
except ImportError:
    print("Error importing dewolf")
    sys.exit(1)

def _init_dirs():
    clear_and_create_dir(DECOMP_DIR)
    clear_and_create_dir(SRC_FUNC_DIR)
    clear_and_create_dir(DECOMP_FUNC_DIR)
    clear_and_create_dir(RES_DIR)

def _prepare_jobs_for_binary(args) -> List[Dict[str, str]]:
    bin_path, ssa_method, graph_edit_timeout = args

    ret = []
    decompiler = None
    try:
        bin_name = bin_path.name
        src_path = SRC_DIR / (bin_name + ".c")
        if(not src_path.exists()):
            raise FileNotFoundError(f"src file {bin_name}.c not found!")
        
        res_p_path          = RES_DIR / bin_name
        decomp_p_path       = DECOMP_DIR / bin_name
        src_func_p_path     = SRC_FUNC_DIR / bin_name
        decomp_func_p_path  = DECOMP_FUNC_DIR / bin_name

        create_dir(res_p_path)
        create_dir(decomp_p_path)
        create_dir(src_func_p_path)
        create_dir(decomp_func_p_path)

        decompiler = Decompiler.from_path(bin_path)
        for func_name in decompiler._frontend.get_all_function_names(): 
            res_path            = res_p_path / (func_name + ".json")
            src_func_path       = src_func_p_path / func_name
            decomp_out_path     = decomp_p_path / func_name
            decomp_func_path    = decomp_func_p_path / func_name

            ret.append(
                {
                    "bin_path": str(bin_path),
                    "src_path": str(src_path),
                    "res_path": str(res_path),
                    "decomp_out_path": str(decomp_out_path),
                    "src_func_path": str(src_func_path),
                    "decomp_func_path": str(decomp_func_path),
                    "func_name": func_name,
                    "ssa_method": ssa_method,
                    "graph_edit_timeout": graph_edit_timeout
                }
            ) 
    except Exception as e:
        print(f"[-] Error preparing jobs for binary {bin_path}: {e}", file=sys.stderr)
    finally:
        del decompiler
        gc.collect()

    return ret

def prepare_jobs(worker_count: int, ssa_method: str, graph_edit_timeout: int):
    jobs = []

    _init_dirs()

    args = [
            (f, ssa_method, graph_edit_timeout) 
            for f in Path(BINS_DIR).iterdir() 
            if f.is_file() and f.name not in NAMES_TO_IGNORE
    ]
    print(f"[*] Preparing jobs for {len(args)} binaries using {worker_count} workers...")
    
    with ProcessPool(max_workers=worker_count) as pool:
        future = pool.map(_prepare_jobs_for_binary, args)
        
        try:
            for res in future.result():
                jobs.extend(res)
        except Exception as e:
            print(f"[-] Error during job preparation: {e}", file=sys.stderr)

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
        "-m", "--ssa-method", 
        type=str, 
        default="conditional",
        help="SSA translation mode (default: 'conditional')"
    )
    parser.add_argument(
        "-t", "--graph-edit-timeout", 
        type=int,
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help=f"Timeout for the networkx graph edit distance approx. algorithm (default {GRAPH_EDIT_DISTANCE_TIMEOUT}"
    )

    args = parser.parse_args()
    prepare_jobs(args.processes, args.ssa_method, args.graph_edit_timeout)

if __name__ == "__main__":
    main()
