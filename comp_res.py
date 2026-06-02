#!/usr/bin/env python3

import sys
import json
import traceback
from typing import Dict, List
import processVariable
import argparse
from pebble import ProcessPool
from multiprocessing import cpu_count
from sim_matching import SimilarityMatching
from dependencyGraphfromC2 import DependencyGraphfromCFunction
from shared import (
        SSA_ALGOS,
        MEM_LIMIT_GB,
        GRAPH_EDIT_DISTANCE_TIMEOUT,
        DECOMP_COMP_TRESHOLD,
        init_worker,
        log_and_print,
        load_jobs, 
        get_res_file,
        get_dict_file,
        get_src_func_file,
        get_decomp_func_file,
)
from compareDicts import are_the_same
from traceback import format_tb

def _comp_res_for_job(args):
    bin = args.get("bin")
    func = args.get("func")
    fresh = args.get("fresh")
    ssa_algo = args.get("ssa_algo")
    ged_timeout = args.get("ged_timeout")

    res_path = get_res_file(ssa_algo, bin, func)
    src_func_path = get_src_func_file(ssa_algo, bin, func)
    decomp_func_path = get_decomp_func_file(ssa_algo, bin, func)

    if res_path.exists() and not fresh:
        return

    src_func_code = src_func_path.read_text()
    decomp_func_code = decomp_func_path.read_text()
    sm = SimilarityMatching(src_func_code, decomp_func_code,func=="stbi_write_bmp_core")
    stats = sm.computeGraphEditDistance(ged_timeout)
            
    res_path.write_text(json.dumps(stats.to_dict(), indent=4))

def _init_worker(limit_gb: int):
    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()
    init_worker(limit_gb)

def _filter_jobs(jobs_in: List[Dict[str, str]], threshold: float) -> List[Dict[str,str]]:
    jobs_out = []

    for j in jobs_in:
        bin = j["bin"]
        func = j["func"]

        missing_file = False
        dict_files = []
        for ssa_algo in SSA_ALGOS:
            dict_f = get_dict_file(ssa_algo, bin, func)
            src_func_f = get_src_func_file(ssa_algo, bin, func)
            decomp_func_f = get_decomp_func_file(ssa_algo, bin, func)

            if not (dict_f.exists() and src_func_f.exists() and decomp_func_f.exists()):
                missing_file = True
                break

            dict_files.append(dict_f)
            
        if missing_file or are_the_same(dict_files, threshold):
            continue

        jobs_out.append(j)

    return jobs_out

def comp_res(worker_count: int, mem_limit: int, ged_timeout: int, threshold: float, fresh: bool):
    jobs = load_jobs() 
    if not jobs:
        log_and_print("[-] No jobs found! Try running prepare_jobs.py", print_file=sys.stderr)
        return

    jobs = [{**d, "ged_timeout": ged_timeout, "fresh": fresh } 
                  for d in _filter_jobs(jobs, threshold)]

    for ssa_algo in SSA_ALGOS:
        c_jobs = [{ **d, "ssa_algo": ssa_algo } for d in jobs]
        log_and_print(f"[*] Computing results for ssa algorithm {ssa_algo} using {worker_count} workers...")
    
        with ProcessPool(max_workers=worker_count, initializer=_init_worker, initargs=(mem_limit,)) as pool:
            iterator = pool.map(_comp_res_for_job, c_jobs).result()
            for job in c_jobs:
                try:
                    next(iterator)
                except StopIteration:
                    break
                except Exception as e:
                    bin = job["bin"]
                    func = job["func"]
                    ssa_algo = job["ssa_algo"]
                    res_path = get_res_file(ssa_algo, bin, func)
                    log_and_print(f"[-] Error processing {res_path}: {e}, Traceback: {format_tb(e.__traceback__)}", print_file=sys.stderr)
    
        log_and_print("")

def main():
    parser = argparse.ArgumentParser(description="Parallel Similarity Matching Stats")
    parser.add_argument(
        "-f", "--fresh",
        action=argparse.BooleanOptionalAction,
        help=f"Overwrite exisitng files (default: {False})"
    )
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help="Number of processes"
    )
    parser.add_argument("-m", "--mem-limit",
        type=int,
        default=MEM_LIMIT_GB,
        help=f"Memory limit for worker processes in GB (default: {MEM_LIMIT_GB}GB)"
    )
    parser.add_argument(
        "-g", "--graph-edit-timeout", 
        type=int,
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help=f"Timeout for the graph edit distance approx. algorithm in seconds (default {GRAPH_EDIT_DISTANCE_TIMEOUT}s)"
    )
    parser.add_argument(
        "-s", "--decomp-comp-threshold", 
        type=float,
        default=DECOMP_COMP_TRESHOLD,
        help=f"Treshold for deciding wether the output of the diffrent ssa algpeorithm is the same as percentage (default {DECOMP_COMP_TRESHOLD}s)"
    )

    args = parser.parse_args()
    comp_res(args.processes, args.mem_limit, args.graph_edit_timeout, 
             args.decomp_comp_threshold, args.fresh)

if __name__ == "__main__":
    main()
