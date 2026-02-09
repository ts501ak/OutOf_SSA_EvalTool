#!/usr/bin/env python3
"""
make_to_preprocess.py

Usage:
  1) From coreutils top:
     make -j1 V=1 2>&1 | tee make.log

  2) Then:
     python3 make_to_preprocess.py --log make.log --outdir someoutdir

This script will create preprocessed .i files with the same -I/-D/-include flags
the real build used for each translation unit.
"""
import argparse
import shlex
import subprocess
from pathlib import Path
import sys
import re

def find_compile_commands(logfile):
    cmds = []
    with open(logfile, 'r', errors='ignore') as fh:
        for raw in fh:
            line = raw.rstrip()
            # crude filter: lines that invoke gcc/cc/clang and have -c and a .c file
            if re.search(r'\b(gcc|clang|cc)\b', line) and '-c ' in line and '.c' in line:
                # remove any leading echo/printf wrapper (some Makefiles echo the command)
                # best effort: if line starts with a tab and command, keep it
                cmds.append(line)
    return cmds

def extract_c_and_obj(args):
    # args: list of tokens (shlex.split)
    # find -c and the following token (c-file) and -o <obj> if any
    cfile = None
    obj = None
    for i, tok in enumerate(args):
        if tok == '-c' and i+1 < len(args):
            cfile = args[i+1]
        if tok == '-o' and i+1 < len(args):
            obj = args[i+1]
    return cfile, obj

def build_preprocess_cmd(args, cfile, outpath):
    # make a copy of args but replace '-c <cfile>' and any '-o <obj>' with '-E -P <cfile>'
    new_args = []
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == '-c':
            # skip '-c' and the cfile
            i += 2
            continue
        if tok == '-o':
            # skip -o and its arg
            i += 2
            continue
        new_args.append(tok)
        i += 1

    # ensure we keep the compiler name (first token)
    # append -E -P and the cfile at the end (or replace -c usage)
    new_args = [new_args[0]] + new_args[1:]  # safe copy
    # Add preprocessing flags
    # avoid duplicating -E/-P if accidentally present
    if '-E' not in new_args:
        new_args.insert(1, '-E')
    if '-P' not in new_args:
        new_args.insert(2, '-P')

    # ensure the cfile token is present (some compiles pass it before flags)
    if cfile not in new_args:
        new_args.append(cfile)

    # make sure config.h is included (if HAVE_CONFIG_H not defined and -include missing)
    has_include = any(tok == '-include' for tok in new_args)
    has_define_have_config = any(tok.startswith('-DHAVE_CONFIG_H') or tok == '-DHAVE_CONFIG_H' for tok in new_args)
    if not has_include and not has_define_have_config:
        # safe to add -include config.h (assuming you're in project top dir where config.h exists)
        new_args.extend(['-include', 'config.h'])

    # final redirect target
    return new_args, str(outpath)

def run_preprocess(cmd_tokens, outpath):
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, 'w') as outf:
        try:
            # Use stderr PIPE so we can print useful messages
            proc = subprocess.run(cmd_tokens, stdout=outf, stderr=subprocess.PIPE, check=True)
            return True, proc.stderr.decode(errors='ignore')
        except subprocess.CalledProcessError as e:
            return False, (e.stderr.decode(errors='ignore') if e.stderr else str(e))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True, help='make V=1 log file (stdout/stderr) containing compile commands')
    ap.add_argument('--outdir', default='someoutdir', help='directory for .i outputs')
    ap.add_argument('--filter', help='optional substring filter e.g. src/basenc.c to only process certain files')
    args = ap.parse_args()

    cmds = find_compile_commands(args.log)
    if not cmds:
        print('[ERROR] No compile commands found in log. Did you run: make -j1 V=1 2>&1 | tee make.log ?')
        sys.exit(1)

    processed = 0
    for line in cmds:
        # tidy: if the line starts with something like "gcc ..." or "  gcc ..." extract command part
        # remove any leading "echo" or "@" used by make; take first word starting with gcc/clang/cc
        # Use shlex to split robustly
        try:
            toks = shlex.split(line, posix=True)
        except Exception:
            # fallback: simple split
            toks = line.split()

        # find index of compiler token
        comp_idx = None
        for i, t in enumerate(toks):
            if re.match(r'^(gcc|clang|cc)(\b|$)', t):
                comp_idx = i
                break
        if comp_idx is None:
            # no compiler token found in this line
            continue

        toks = toks[comp_idx:]  # keep only from compiler onward

        cfile, obj = extract_c_and_obj(toks)
        if not cfile:
            # maybe compile via '$(CC) -o foo.o foo.c' style - try to heuristically find a .c file
            for t in toks:
                if t.endswith('.c'):
                    cfile = t
                    break
        if not cfile:
            print(f'[SKIP] Could not find .c file in compile line: {line}')
            continue

        if args.filter and args.filter not in cfile:
            continue

        # compute basename for output
        bn = Path(cfile).stem
        outpath = Path(args.outdir) / f'{bn}.i'

        pre_cmd, outpath_str = build_preprocess_cmd(toks, cfile, outpath)
        # join pre_cmd into list of tokens (already)
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
