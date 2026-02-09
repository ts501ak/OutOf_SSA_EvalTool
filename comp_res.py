#!/usr/bin/env python3

import json
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial

from sim_matching import SimilarityMatching, StatisticsClass
from extract import extract_function
from shared import (
    DECOMP_DIR,
    FUNCS_DIR,
    SRC_DIR,
    GRAPH_EDIT_DISTANCE_TIMEOUT,
    RES_DIR,
    clear_and_create_dir,
    get_unique_path,
)

def write_statistics(statistics: StatisticsClass, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(statistics.to_dict(), f, indent=4)


def process_binary_task(funcs_file: Path, timeout: int):
    """
    Processes a single binary's functions and returns binary statistics.
    """
    bin_name = funcs_file.stem
    print(f"[+] Analyzing binary: {bin_name}")

    src_file = SRC_DIR / f"{bin_name}.c"
    decomp_file = DECOMP_DIR / f"{bin_name}.c"

    if not src_file.exists() or not decomp_file.exists():
        return None

    bin_avg = StatisticsClass()
    bin_res_dir = RES_DIR / f"{bin_name}"
    bin_res_dir.mkdir(parents=True, exist_ok=True)

    function_names = [
        line.strip() for line in funcs_file.read_text().splitlines() if line.strip()
    ]

    for func in function_names:
        src_code = extract_function(src_file, func)
        decomp_code = extract_function(decomp_file, func)

        if src_code and decomp_code:
            sm = SimilarityMatching(src_code, decomp_code)
            stats = sm.computeGraphEditDistance(timeout)

            func_res_file = get_unique_path(bin_res_dir / f"{func}.json")
            write_statistics(stats, func_res_file)

            bin_avg += stats

    bin_avg_file = get_unique_path(bin_res_dir / f"{bin_name}_avg.json")
    write_statistics(bin_avg, bin_avg_file)

    return bin_avg


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
        default=GRAPH_EDIT_DISTANCE_TIMEOUT,
        help="GED timeout in seconds"
    )
    args = parser.parse_args()

    clear_and_create_dir(RES_DIR)
    global_avg = StatisticsClass()
    
    tasks = [f for f in FUNCS_DIR.iterdir() if f.is_file()]
    
    if not tasks:
        print("No function files found.")
        return

    worker = partial(process_binary_task, timeout=args.timeout)

    with Pool(processes=args.processes) as pool:
        for result in pool.imap_unordered(worker, tasks):
            if result:
                global_avg += result

    global_avg_file = get_unique_path(RES_DIR / "global_avg.json")
    write_statistics(global_avg, global_avg_file)
    print("Done.")


if __name__ == "__main__":
    main()
