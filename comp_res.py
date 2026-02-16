#!/usr/bin/env python3

import sys
import json
import argparse
from pathlib import Path
from shared import load_jobs
from pebble import ProcessPool
from multiprocessing import cpu_count
from sim_matching import SimilarityMatching

def _comp_res_for_job(args):
    res_path = args.get("res_path")
    src_func_path = args.get("src_func_path")
    decomp_func_path = args.get("decomp_func_path")
    graph_edit_timeout = args.get("graph_edit_timeout")
    
    try:
        src_func_code = Path(src_func_path).read_text()
    except Exception as e:
        print(f"[-] Error reading {src_func_path}: {e}", file=sys.stderr)
        return

    try:
        decomp_func_code = Path(decomp_func_path).read_text()
    except Exception as e:
        print(f"[-] Error reading {decomp_func_path}: {e}", file=sys.stderr)
        return

    if src_func_code == "":
        print(f"[-] Skipping {res_path} since src_func_code is empty", file=sys.stderr)
        return

    if decomp_func_code == "":
        print(f"[-] Skipping {res_path} since decomp_func_code is empty", file=sys.stderr)
        return

    try:
        sm = SimilarityMatching(src_func_code, decomp_func_code)
        stats = sm.computeGraphEditDistance(graph_edit_timeout)
        with open(res_path, "w") as f:
            json.dump(stats.to_dict(),f, indent=4)
    except Exception as e:
        print(f"[-] Failed to write results to {res_path}: {e}")
    

def comp_res(worker_count: int):
    jobs = load_jobs()
    if(not jobs):
        print("[-] jobs.json not found! Try running prepare_jobs.py", file=sys.stderr)
        return

    print(f"[*] Computing results for {len(jobs)} functions using {worker_count} workers...")
    with ProcessPool(max_workers=worker_count) as pool:
        future = pool.map(_comp_res_for_job, jobs)
        try:
            for _ in future.result():
                pass
        except Exception as e:
            print(f"[-] Error during function extraction pool execution: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Parallel Similarity Matching Stats")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help="Number of processes"
    )
    args = parser.parse_args()
    comp_res(args.processes)

if __name__ == "__main__":
    main()
