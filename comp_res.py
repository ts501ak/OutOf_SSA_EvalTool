#!/usr/bin/env python3

import sys
import json
import argparse
from pathlib import Path
from pebble import ProcessPool
from concurrent.futures import TimeoutError # Added for timeout handling
from multiprocessing import cpu_count
from sim_matching import SimilarityMatching
from shared import load_jobs, COMP_RES_TIMEOUT
from dependencyGraphfromC import DependencyGraphfromCFunction
import processVariable

def _comp_res_for_job(args):
    res_path = args.get("res_path")
    src_func_path = args.get("src_func_path")
    decomp_func_path = args.get("decomp_func_path")
    graph_edit_timeout = args.get("graph_edit_timeout")
    
    try:
        src_func_code = Path(src_func_path).read_text()
        decomp_func_code = Path(decomp_func_path).read_text()
        
        if not src_func_code or not decomp_func_code:
            return
            
        sm = SimilarityMatching(src_func_code, decomp_func_code)
        stats = sm.computeGraphEditDistance(graph_edit_timeout)
        del sm
        
        with open(res_path, "w") as f:
            json.dump(stats.to_dict(), f, indent=4)
            
    except Exception as e:
        print(f"[-] Failure processing {res_path}: {e}", file=sys.stderr)

def comp_res(worker_count: int, timeout: int):
    jobs = load_jobs()
    if not jobs:
        print("[-] jobs.json not found! Try running prepare_jobs.py", file=sys.stderr)
        return

    print(f"[*] Computing results for {len(jobs)} functions using {worker_count} workers...")
    
    with ProcessPool(max_workers=worker_count, initializer=init_worker) as pool:
        future = pool.map(_comp_res_for_job, jobs, timeout=timeout)
        iterator = future.result()
        
        for job in jobs:
            try:
                next(iterator)
            except StopIteration:
                break
            except TimeoutError:
                print(f"[-] Timeout reached for: {job.get('res_path')}", file=sys.stderr)
            except Exception as e:
                print(f"[-] Error during job execution: {e}", file=sys.stderr)

def init_worker():
    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()

def main():
    parser = argparse.ArgumentParser(description="Parallel Similarity Matching Stats")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help="Number of processes"
    )
    parser.add_argument(
        "-t", "--timeout", 
        type=int, 
        default=COMP_RES_TIMEOUT,
        help="Timeout of result computation of a function"
    )
    args = parser.parse_args()
    comp_res(args.processes, args.timeout)

if __name__ == "__main__":
    main()
