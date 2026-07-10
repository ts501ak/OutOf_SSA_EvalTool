#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, Any, Optional
import json
import sys


SSA_ALGOS = ["boissinot2008", "conditional", "sreedhar"]

METRICS = [
    "num_variables",
    "num_copy_assignments",
    "total_operators",
    "distinct_operators",
    "total_operands",
    "distinct_operands",
    "halstead_vocabulary",
    "halstead_length",
    "halstead_volume",
    "halstead_difficulty",
    "halstead_effort",
    "halstead_bugs",
    "var_defs",
    "var_uses",
    "var_scope",
    "var_distance",
    "var_max_live_distance",
    "var_disjoint_webs",
]

VAR_METRICS = {
    "var_defs": "definitions",
    "var_uses": "usages",
    "var_scope": "scopes",
    "var_distance": "distance",
    "var_max_live_distance": "max_live_distance",
    "var_disjoint_webs": "disjoint_webs",
}

VAR_DIST_METRICS = {"var_distance"}


def parse_args(description: str, default_res_dir: str, default_output_dir: str) -> dict:
    """Parse common CLI arguments for analysis scripts."""
    import argparse
    
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--res-dir",
        type=str,
        default=None,
        help=f"Path to results directory (default: {default_res_dir})"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Path to output directory (default: {default_output_dir})"
    )
    
    args = parser.parse_args()
    
    res_dir = args.res_dir if args.res_dir else default_res_dir
    output_dir = args.output_dir if args.output_dir else default_output_dir
    
    return {
        "res_dir": Path(res_dir),
        "output_dir": Path(output_dir),
    }


def load_json_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a JSON file."""
    try:
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return None


def get_binary_function_name(filepath: Path) -> str:
    """Extract binary/function identifier from path."""
    parts = str(filepath).split("/")
    return "/".join(parts[-2:]).split(".")[0]


def calculate_metric_value(data: Dict[str, Any], metric: str) -> Any:
    """Extract the value for a metric from data."""
    if metric in VAR_METRICS:
        var_metric = VAR_METRICS[metric]
        variables = data.get("variables", {}).values()
        values = [var.get(var_metric, 0) for var in variables]
        
        if metric in VAR_DIST_METRICS:
            distances = []
            for var in variables:
                for lr in var.get("live_ranges", []):
                    distances.append(lr.get("distance", 0))
            if not distances:
                return None
            return sum(distances) / len(distances)
        
        if not values:
            return None
        return sum(values) / len(values)

    return data.get(metric)


def collect_function_data(res_dir: Path) -> Dict[str, Dict[str, Dict]]:
    """Collect data from all JSON files in the results directory."""
    function_data = {}
    
    for algo in SSA_ALGOS:
        algo_path = res_dir / algo
        if not algo_path.exists():
            continue
            
        for json_path in algo_path.rglob("*.json"):
            func_key = get_binary_function_name(json_path)
            
            data = load_json_file(json_path)
            if data is None:
                continue
            
            if func_key not in function_data:
                function_data[func_key] = {}
            
            function_data[func_key][algo] = data
    
    return function_data


def compute_absolute_differences(function_data: Dict[str, Dict[str, Dict]]) -> Dict[tuple, Dict[str, float]]:
    """
    Compute absolute differences for each metric between algorithm pairs.
    Returns a dict mapping (algo_x, algo_y) -> {function_name: absolute_difference}
    """
    from itertools import combinations
    
    metric_differences = {}
    
    for func_name, algo_data in function_data.items():
        if len(algo_data) < 2:
            continue
        
        algo_pairs = list(combinations(algo_data.keys(), 2))
        for algo_x, algo_y in algo_pairs:
            if (algo_x, algo_y) not in metric_differences:
                metric_differences[(algo_x, algo_y)] = {metric: {} for metric in METRICS}
            
            data1 = algo_data[algo_x]
            data2 = algo_data[algo_y]
            
            for metric in METRICS:
                val1 = calculate_metric_value(data1, metric)
                val2 = calculate_metric_value(data2, metric)
                
                if val1 is not None and val2 is not None:
                    abs_diff = abs(val1 - val2)
                    metric_differences[(algo_x, algo_y)][metric][func_name] = abs_diff
    
    return metric_differences


def write_differences_file(
    output_dir: Path, 
    metric: str, 
    func_diffs: Dict[str, float]
) -> Path:
    """Write differences for a single metric to a file with outlier marks."""
    if not func_diffs:
        output_file = output_dir / f"{metric}_differences.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            pass
        return output_file
    
    import numpy as np
    
    diffs = list(func_diffs.values())
    q1 = np.percentile(diffs, 25)
    q3 = np.percentile(diffs, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    
    sorted_funcs = sorted(func_diffs.items(), key=lambda x: x[1], reverse=True)
    
    output_file = output_dir / f"{metric}_differences.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for func_name, diff in sorted_funcs:
            outlier = ""
            if diff < lower_bound:
                outlier = " (lower_outlier)"
            f.write(f"{func_name}: {diff}{outlier}\n")
    
    return output_file


def clear_none(data_list):
    """Remove None values from a list."""
    return [x for x in data_list if x is not None]


def mctfunction(x):
    """Compute mean (rounded to 3 decimals) of a list."""
    import numpy as np
    return np.round(np.average(x), 3)
