#!/usr/bin/env python3

import argparse
from prepare_jobs import prepare_jobs 
from decomp_bins import decomp_bins 
from multiprocessing import cpu_count

from shared import (
    MEM_LIMIT_GB,
    DECOMP_TIMEOUT_SECONDS,
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

    args=parser.parse_args()
    
    if (args.fresh):
        clear_log()
        start_stage("Process Preparation")
        prepare_jobs(args.processes, args.mem_limit)
        end_stage()

    start_stage("Computing Results")
    decomp_bins(args.decomp_processes, args.decompile_timeout, args.mem_limit, args.fresh)
    end_stage()

if __name__ == "__main__":
    main()


