#!/usr/bin/env python3

import sys
import json
from typing import Dict, List
import processVariable
import argparse
from pebble import ProcessPool
from multiprocessing import cpu_count
from concurrent.futures import TimeoutError
from sim_matching import SimilarityMatching
from dependencyGraphfromC import DependencyGraphfromCFunction
from shared import (
        SSA_ALGOS,
        MEM_LIMIT_GB,
        GRAPH_EDIT_DISTANCE_TIMEOUT,
        init_worker,
        log_and_print,
        load_jobs, 
        get_res_file,
        get_dict_file,
        get_src_func_file,
        get_decomp_func_file,
) 


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

    try:
        src_func_code = src_func_path.read_text()
        decomp_func_code = decomp_func_path.read_text()
            
        sm = SimilarityMatching(src_func_code, decomp_func_code)
        stats = sm.computeGraphEditDistance(ged_timeout)
            
        res_path.write_text(json.dumps(stats.to_dict(), indent=4))
    except Exception as e:
        log_and_print(f"[-] Error processing {res_path}: {e}", print_file=sys.stderr)

def _init_worker(limit_gb: int):
    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()
    init_worker(limit_gb)

def _filter_jobs(jobs_in: List[Dict[str, str]]) -> List[Dict[str,str]]:
    jobs_out = []

    for j in jobs_in:
        tmp = []    
        bin = j["bin"]
        func = j["func"]

        for ssa_algo in SSA_ALGOS:
            tmp.append({
                #"dict": get_dict_file(ssa_algo, bin, func),
                "src_func": get_src_func_file(ssa_algo, bin, func),
                "decomp_func": get_decomp_func_file(ssa_algo, bin, func) 
            })  

        if any(
            not t[label].exists() 
            for t in tmp 
            for label in ["src_func", "decomp_func"]
            #for label in ["dict", "src_func, decomp_func"]
        ):
            continue

        #if are_the_same([t["dict"] for t in tmp]):
        #    log_and_print(f"[-] Skipping function {func} in binary {bin} since they are the same", print_file=sys.stderr)
        #    continue

        jobs_out.append(j)

    return jobs_out

def comp_res(worker_count: int, mem_limit: int, ged_timeout: int, fresh: bool = True):
    jobs = load_jobs() 
    if not jobs:
        log_and_print("[-] jobs.json not found! Try running prepare_jobs.py", print_file=sys.stderr)
        return

    jobs = _filter_jobs(jobs)
    for ssa_algo in SSA_ALGOS:
        jobs = [{**d, "ssa_algo": ssa_algo, "ged_timeout": ged_timeout, "fresh": fresh } for d in jobs]
        log_and_print(f"[*] Computing results for ssa algorithm {ssa_algo} using {worker_count} workers...")
    
        with ProcessPool(max_workers=worker_count, initializer=_init_worker, initargs=(mem_limit,)) as pool:
            future = pool.map(_comp_res_for_job, jobs)
            iterator = future.result()
            
            for job in jobs:
                try:
                    next(iterator)
                except StopIteration:
                    break
                except TimeoutError:
                    log_and_print(f"[-] Timeout reached for: {job.get('res_path')}", print_file=sys.stderr)
                except Exception as e:
                    log_and_print(f"[-] Error during job execution: {e}", print_file=sys.stderr)

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
        help=f"Memory limit for worker processes in GB (default: {MEM_LIMIT_GB} GB)"
    )
    parser.add_argument(
        "-g", "--graph-edit-timeout", 
        type=int,
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help=f"Timeout for the graph edit distance approx. algorithm (default {GRAPH_EDIT_DISTANCE_TIMEOUT})"
    )
    args = parser.parse_args()
    comp_res(args.processes, args.mem_limit, args.graph_edit_timeout, args.fresh)

if __name__ == "__main__":
    main()
