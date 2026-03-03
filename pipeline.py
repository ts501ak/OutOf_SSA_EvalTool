#!/usr/bin/env python3

import argparse
from prepare_jobs import prepare_jobs 
from decomp_bins import decomp_bins 
from process_functions import process_functions
from comp_res import comp_res
from multiprocessing import cpu_count

from shared import (
    DECOMP_TIMEOUT_SECONDS,
    GRAPH_EDIT_DISTANCE_TIMEOUT,
    DECOMP_MEM_LIMIT_GB,
    COMP_RES_TIMEOUT
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
        help=f"Number of processes (default: {cpu_count()})"
    )
    parser.add_argument(
        "-s", "--ssa-method", 
        type=str, 
        default="conditional",
        help="SSA translation mode (default: 'conditional')"
    )
    parser.add_argument(
        "-d", "--decompile-timeout", 
        type=int, 
        default=DECOMP_TIMEOUT_SECONDS,
        help=f"Dewolf decompile timeout (default: {DECOMP_TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        "-c", "--compres-timeout", 
        type=int, 
        default=COMP_RES_TIMEOUT,
        help=f"Timeout for the compres worker (default: {COMP_RES_TIMEOUT})"
    )
    parser.add_argument(
        "-g", "--graph-edit-timeout", 
        type=int,
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help=f"Timeout for the networkx graph edit distance approx. algorithm (default {GRAPH_EDIT_DISTANCE_TIMEOUT})"
    )
    parser.add_argument("-m", "--mem-limit",
        type=int,
        default=DECOMP_MEM_LIMIT_GB,
        help=f"Memory limit for worker processes (default: {DECOMP_MEM_LIMIT_GB})"
    )
    args=parser.parse_args()
    
    start_stage("Preparing jobs")
    prepare_jobs(args.processes, args.ssa_method, args.graph_edit_timeout, args.mem_limit)
    end_stage()
    start_stage("Decompiling bins")
    decomp_bins(args.processes, args.decompile_timeout, args.mem_limit)
    end_stage()
    start_stage("Processing functions")
    process_functions(args.processes, args.mem_limit)
    end_stage()
    start_stage("Processing functions")
    comp_res(args.processes, args.compres_timeout, args.mem_limit)
    end_stage()


if __name__ == "__main__":
    main()


