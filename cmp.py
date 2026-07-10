#!/usr/bin/env python3

"""
Rank decompiled functions by their absolute differences for each metric.
"""

from pathlib import Path
from analyzer import analysis_common as common
from analyzer.shared import CMP_DIR, RES_DIR


def rank_functions_by_metric() -> None:
    """
    Rank all decompiled functions by their absolute differences for each metric.
    """
    if not RES_DIR.exists():
        print(f"Error: Results directory '{RES_DIR}' does not exist", flush=True)
        return
    
    CMP_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading data from: {RES_DIR}", flush=True)
    function_data = common.collect_function_data(RES_DIR)
    print(f"Found {len(function_data)} functions", flush=True)
    
    print("Computing absolute differences...", flush=True)
    metric_differences = common.compute_absolute_differences(function_data)
    
    print("Writing difference files...", flush=True)
    total_functions_written = 0
    for (algo_x, algo_y), metric_diffs in metric_differences.items():
        pair_dir = CMP_DIR / f"{algo_x}_{algo_y}"
        pair_dir.mkdir(parents=True, exist_ok=True)
        
        for metric in common.METRICS:
            func_diffs = metric_diffs[metric]
            if not func_diffs:
                continue
            
            output_file = common.write_differences_file(pair_dir, metric, func_diffs)
            total_functions_written += len(func_diffs)
            print(f"  {algo_x}_{algo_y}/: {output_file.name} ({len(func_diffs)} functions)", flush=True)
    
    print(f"\nTotal: {len(metric_differences)} algorithm pairs with differences computed", flush=True)
    print(f"Total functions across all metrics: {total_functions_written}", flush=True)
    print(f"Output directory: {CMP_DIR}", flush=True)


def main() -> None:
    rank_functions_by_metric()


if __name__ == "__main__":
    main()
