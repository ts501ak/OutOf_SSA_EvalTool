#!/usr/bin/env python3
"""
Preprocess only src/ C files from a Makefile build log.

Usage:
  1) From coreutils top-level:
       make -j1 V=1 2>&1 | tee make.log
  2) Then:
       python3 preprocess_src.py --log make.log --outdir someoutdir
"""

import argparse
import shlex
import subprocess
from pathlib import Path
import re
import sys

def find_compile_commands(logfile):
    """Extract lines that invoke gcc/clang/cc and compile a .c file."""
    cmds = []
    with open(logfile, 'r', errors='ignore') as fh:
        for raw in fh:
            line = raw.rstrip().rstrip('\\').rstrip()
            if not line:
                continue
            if re.search(r'\b(gcc|clang|cc)\b', line) and '-c' in line and '.c' in line:
                cmds.append(line)
    return cmds

def extract_c_and_obj(args):
    """
    Extract the source .c file and the output object from a gcc compile line.
    -c may or may not take an argument; -o <obj> is standard.
    Strategy:
      * find -o <obj> if exists
      * take the last token ending with .c as the source file
    """
    cfile = None
    obj = None
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == '-o' and i+1 < len(args):
            obj = args[i+1]
            i += 2
            continue
        i += 1
    # last .c file in the args is usually the source file
    c_candidates = [t for t in args if t.endswith('.c')]
    if c_candidates:
        cfile = c_candidates[-1]
    return cfile, obj

def build_preprocess_cmd(args, cfile, outpath):
    """Transform a compile command into a preprocessing command."""
    new_args = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == '-c':
            i += 1  # skip -c
            continue
        if tok == '-o':
            i += 2  # skip -o and its argument
            continue
        new_args.append(tok)
        i += 1

    # Insert -E -P if not already present
    if '-E' not in new_args:
        new_args.insert(1, '-E')
    if '-P' not in new_args:
        new_args.insert(2, '-P')

    # Ensure the .c file is included
    if cfile not in new_args:
        new_args.append(cfile)

    # Ensure config.h is included if HAVE_CONFIG_H not defined
    has_include = any(tok == '-include' for tok in new_args)
    has_define_have_config = any(tok.startswith('-DHAVE_CONFIG_H') or tok == '-DHAVE_CONFIG_H' for tok in new_args)
    if not has_include and not has_define_have_config:
        new_args.extend(['-include', 'config.h'])

    return new_args, str(outpath)

def run_preprocess(cmd_tokens, outpath):
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, 'w') as outf:
        try:
            proc = subprocess.run(cmd_tokens, stdout=outf, stderr=subprocess.PIPE, check=True)
            return True, proc.stderr.decode(errors='ignore')
        except subprocess.CalledProcessError as e:
            return False, (e.stderr.decode(errors='ignore') if e.stderr else str(e))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True, help='make V=1 log file containing compile commands')
    parser.add_argument('--outdir', default='someoutdir', help='directory for .i output files')
    parser.add_argument('--filter', help='optional substring filter to process only certain files')
    args = parser.parse_args()

    compile_cmds = find_compile_commands(args.log)
    if not compile_cmds:
        print('[ERROR] No compile commands found. Did you run: make -j1 V=1 2>&1 | tee make.log ?')
        sys.exit(1)

    processed = 0
    for line in compile_cmds:
        # Strip trailing && or \
        line = line.strip().rstrip('\\').rstrip()
        try:
            toks = shlex.split(line, posix=True)
        except Exception:
            toks = line.split()

        # Keep only tokens from compiler onward
        comp_idx = None
        for i, t in enumerate(toks):
            if re.match(r'^(gcc|clang|cc)(\b|$)', t):
                comp_idx = i
                break
        if comp_idx is None:
            continue
        toks = toks[comp_idx:]

        cfile, obj = extract_c_and_obj(toks)
        if not cfile:
            print(f'[SKIP] Could not find .c file in compile line: {line}')
            continue

        # Only handle src/ files
        if not str(cfile).startswith("src/"):
            print(f'[SKIP] not in src/: {cfile}')
            continue

        if args.filter and args.filter not in cfile:
            continue

        # Output file: someoutdir/<basename>.i
        bn = Path(cfile).stem
        outpath = Path(args.outdir) / f"{bn}.i"

        pre_cmd, outpath_str = build_preprocess_cmd(toks, cfile, outpath)
        print(f'[RUN] {" ".join(pre_cmd)} > {outpath_str}')

        ok, stderr = run_preprocess(pre_cmd, outpath_str)
        if not ok:
            print(f'[ERROR] GCC failed for {cfile}')
            if stderr:
                print('[ERROR] stderr:\n' + stderr.strip())
            continue

        processed += 1

    print(f'Processed {processed} files (outdir={args.outdir}).')

if __name__ == "__main__":
    main()
