#!/usr/bin/env python3

import os
import sys
import gc
import argparse
import contextlib
from multiprocessing import cpu_count
from pebble import ProcessPool

from shared import (
    DEWOLF_DIR,
    DECOMP_TIMEOUT_SECONDS,
    load_jobs,
)

# Add the 'dewolf' directory to sys.path
sys.path.insert(0, str(DEWOLF_DIR))

# Import decompiler
try:
    from decompile import Decompiler #type: ignore
except ImportError:
    print("Error importing dewolf", file=sys.stderr)
    sys.exit(1)

def _decompile_func(args):
    bin_path = args.get("bin_path")
    func_name = args.get("func_name")
    ssa_method = args.get("ssa_method")
    decomp_out_path = args.get("decomp_out_path")

    success = False
    decompiler = None
    try:
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                options = Decompiler.create_options()
                options.update({"out-of-ssa-translation.mode": ssa_method})
                
                decompiler = Decompiler.from_path(bin_path)

                task, code = decompiler.decompile(func_name)
                success = not task.failed

        if success:
            with open(decomp_out_path, "w") as f:
                f.write(code)

    except Exception as e:
        print(f"[-] Error decompiling function {func_name} in {bin_path}: {e}", file=sys.stderr)
    finally:
        del decompiler
        gc.collect()


def decomp_bins(worker_count: int, decompile_timeout: int):
    jobs = load_jobs()
    if(not jobs):
        print("[-] jobs.json not found! Try running prepare_jobs.py", file=sys.stderr)
        return

    print(f"[*] Decompiling {len(jobs)} functions using {worker_count} workers...")
    with ProcessPool(max_workers=worker_count) as pool:
        future = pool.map(_decompile_func, jobs, timeout=decompile_timeout)
        try:
            for _ in future.result():
                pass
        except Exception as e:
            print(f"[-] Error during decompilation pool execution: {e}", file=sys.stderr)
            gc.collect()


def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes (default: {cpu_count()})"
    )
    parser.add_argument(
        "-t", "--decompile-timeout", 
        type=int, 
        default=DECOMP_TIMEOUT_SECONDS,
        help=f"Dewolf decompile timeout (default: {DECOMP_TIMEOUT_SECONDS})"
    )
    args = parser.parse_args()
    decomp_bins(args.processes, args.decompile_timeout)

if __name__ == "__main__":
    main()
