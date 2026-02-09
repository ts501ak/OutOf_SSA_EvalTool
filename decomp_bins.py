#!/usr/bin/env python3

import os
import sys
import argparse
import contextlib
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial

from shared import (
    BASE_DIR,
    BINS_DIR,
    DECOMP_DIR,
    FUNCS_DIR,
    clear_and_create_dir,
)

# Add the 'dewolf' directory to sys.path
dewolf_dir = BASE_DIR / "dewolf"
sys.path.insert(0, str(dewolf_dir))

# Import decompiler
try:
    from decompile import Decompiler
except ImportError:
    print("Error importing dewolf")
    sys.exit(1)

def decompile_binary(binary_path: Path, ssa_method: str):
    """
    Decompiles all functions in a binary.
    Returns (decompiled_code, function_names).
    """
    code = ""
    all_functions = []

    try:
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                options = Decompiler.create_options()
                options.update({"out-of-ssa-translation.mode": ssa_method})

                decomp = Decompiler.from_path(str(binary_path), options)
                all_functions = decomp._frontend.get_all_function_names()
                code = decomp.decompile_all(all_functions, options).code
    except Exception:
        pass

    return code, all_functions


def worker_task(bin_path: Path, ssa_method: str):
    """
    Worker function to process a single binary and write results to unique paths.
    """
    bin_name = bin_path.name
    print(f"[+] Processing {bin_name}")

    code, functions = decompile_binary(bin_path, ssa_method)

    if not code:
        return

    decomp_out = DECOMP_DIR / f"{bin_name}.c"
    decomp_out.write_text(code)

    funcs_out = FUNCS_DIR / f"{bin_name}.func"
    funcs_out.write_text("\n".join(functions))


def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes (default: {cpu_count()})"
    )
    parser.add_argument(
        "-m", "--ssa-method", 
        type=str, 
        default="conditional",
        help="SSA translation mode (default: 'conditional')"
    )
    args = parser.parse_args()

    clear_and_create_dir(DECOMP_DIR)
    clear_and_create_dir(FUNCS_DIR)

    tasks = [p for p in BINS_DIR.iterdir() if p.is_file()]
    
    if not tasks:
        print("No binaries found.")
        return

    print(f"Decompiling {len(tasks)} binaries with {args.processes} workers...")
    
    worker = partial(worker_task, ssa_method=args.ssa_method)

    with Pool(processes=args.processes) as pool:
        pool.map(worker, tasks)
    
    print("Done.")


if __name__ == "__main__":
    main()
