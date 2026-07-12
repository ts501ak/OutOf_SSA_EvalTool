#!/usr/bin/env python3

import argparse
from prepare_jobs import prepare_jobs 
from decomp_bins import decomp_bins 
from process_functions import process_functions
from comp_res import comp_res
from multiprocessing import cpu_count

from lib.shared import (
    MEM_LIMIT_GB,
    DECOMP_MEM_LIMIT_GB,
    DECOMP_TIMEOUT_SECONDS,
    GRAPH_EDIT_DISTANCE_TIMEOUT,
    DECOMP_COMP_TRESHOLD,
    log_and_print,
    clear_log,
) 

sep = '-' * 100

def start_stage(name: str):
    log_and_print(f"Starting ** {name} **")
    log_and_print(sep)

def end_stage():
    log_and_print(sep)
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
        help=f"Timeout for a decompilation job in seconds (default: {DECOMP_TIMEOUT_SECONDS}s)"
    )
    parser.add_argument("-m", "--mem-limit",
        type=int,
        default=MEM_LIMIT_GB,
        help=f"Memory limit in GB per process (default: {MEM_LIMIT_GB}GB)"
    )
    parser.add_argument("-z", "--decomp-mem-limit",
        type=int,
        default=DECOMP_MEM_LIMIT_GB,
        help=f"Memory limit in GB for a decompilation job (default: {DECOMP_MEM_LIMIT_GB}GB)"
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

    args=parser.parse_args()
    
    if (args.fresh):
        clear_log()
        start_stage("Process Preparation")
        prepare_jobs(args.processes, args.mem_limit)
        end_stage()

    start_stage("Binary Decompilation")
    decomp_bins(args.decomp_processes, args.decompile_timeout, args.decomp_mem_limit, args.fresh)
    end_stage()
    start_stage("Function Processing")
    process_functions(args.processes, args.mem_limit, args.fresh)
    end_stage()
    start_stage("Result Computation")
    comp_res(args.processes, args.mem_limit, args.graph_edit_timeout, 
             args.decomp_comp_threshold, args.fresh)
    end_stage()


if __name__ == "__main__":
    main()


