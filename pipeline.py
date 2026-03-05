#!/usr/bin/env python3

import argparse
from prepare_jobs import prepare_jobs 
from decomp_bins import decomp_bins 
from process_functions import process_functions
from comp_res import comp_res
from multiprocessing import cpu_count

from shared import (
    MEM_LIMIT_GB,
    DECOMP_MEM_LIMIT_GB,
    DECOMP_TIMEOUT_SECONDS,
    GRAPH_EDIT_DISTANCE_TIMEOUT,
) 

sep = '-' * 100

def start_stage(name: str):
    print(f"Starting **{name}**")
    print(sep)

def end_stage():
    print(sep)
    print()

def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes to use (default: {cpu_count()})"
    )
    parser.add_argument(
        "-d", "--decomp-processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes to use for the decompilation (default: {cpu_count()})"
    )
    parser.add_argument(
        "-t", "--decompile-timeout", 
        type=int, 
        default=DECOMP_TIMEOUT_SECONDS,
        help=f"Timeout for a decompilation job (default: {DECOMP_TIMEOUT_SECONDS})"
    )
    parser.add_argument("-m", "--mem-limit",
        type=int,
        default=MEM_LIMIT_GB,
        help=f"Memory limit in GB per process (default: {MEM_LIMIT_GB})"
    )
    parser.add_argument("-z", "--decomp-mem-limit",
        type=int,
        default=DECOMP_MEM_LIMIT_GB,
        help=f"Memory limit in GB for a decompilation job (default: {DECOMP_MEM_LIMIT_GB})"
    )
    parser.add_argument(
        "-g", "--graph-edit-timeout", 
        type=int,
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help=f"Timeout for the graph edit distance approx. algorithm (default {GRAPH_EDIT_DISTANCE_TIMEOUT})"
    )
    args=parser.parse_args()
    
    start_stage("Preparing jobs")
    prepare_jobs(args.processes, args.mem_limit)
    end_stage()
    start_stage("Decompiling bins")
    decomp_bins(args.decomp_processes, args.decompile_timeout, args.decomp_mem_limit)
    end_stage()
    start_stage("Processing functions")
    process_functions(args.processes, args.mem_limit)
    end_stage()
    start_stage("Computing results")
    comp_res(args.processes, args.mem_limit, args.graph_edit_timeout)
    end_stage()


if __name__ == "__main__":
    main()


