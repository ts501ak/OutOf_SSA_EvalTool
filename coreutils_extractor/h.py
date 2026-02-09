#!/usr/bin/env python3
"""
Preprocess only src/ C files from a Makefile build log.

Features:
- Filters only src/*.c files
- Ignores lib/ and automake dependency files
- Removes shell expansions (`...` and $())
- Uses object file name for .i output if available
- Adds -E -P -w and includes config.h
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
            line = raw.strip()
            if not line:
                continue
            # Remove trailing \ and &&
            line = re.sub(r'\\\s*$', '', line)
            line = re.sub(r'\s+&&\s*$', '', line)
            if re.search(r'\b(gcc|clang|cc)\b', line) and '-c' in line and '.c' in line:
                cmds.append(line)
    return cmds

def extract_c_and_obj(args):
    """Extract the src/*.c file and output object from gcc compile line."""
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

    # Only consider src/*.c files
    c_candidates = [t for t in args if t.startswith('src/') and t.endswith('.c')]
    if c_candidates:
        cfile = c_candidates[-1]
    return cfile, obj

def normalize_cfile(cfile):
    """Remove backticks, $(), quotes, etc."""
    cfile = re.sub(r'[`$()]+', '', cfile)
    cfile = cfile.strip("'\"")
    return cfile

def build_preprocess_cmd(args, cfile, outpath):
    """Build the preprocessing command for gcc."""
    skip_flags = {'-fPIC', '-MT', '-MD', '-MP', '-MF'}
    new_args = []

    for tok in args:
        # keep flags and the actual src file only
        if tok in skip_flags or tok.startswith('-M'):
            continue
        if tok == '-c' or tok == '-o':
            continue
        if tok.endswith('.o') or tok.endswith('.Tpo') or tok.endswith('.Po') or tok.endswith('.d'):
            continue
        if tok.startswith('lib/'):
            continue
        # skip tokens containing shell expansions
        if '`' in tok or '$(' in tok or ')' in tok:
            continue
        new_args.append(tok)

    # Add preprocessing flags
    if '-E' not in new_args:
        new_args.insert(1, '-E')
    if '-P' not in new_args:
        new_args.insert(2, '-P')
    if '-w' not in new_args:
        new_args.insert(3, '-w')

    # Ensure the correct source file is included
    if cfile not in new_args:
        new_args.append(cfile)

    # Include config.h if not already
    if not any(tok == '-include' for tok in new_args):
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
            continue

        cfile = normalize_cfile(cfile)

        # Only process src/ files
        if not cfile.startswith('src/'):
            continue

        if args.filter and args.filter not in cfile:
            continue

        # Use object file basename if available
        if obj:
            bn = Path(obj).stem
        else:
            bn = Path(cfile).stem
        outpath = Path(args.outdir) / f"{bn}.c"

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
