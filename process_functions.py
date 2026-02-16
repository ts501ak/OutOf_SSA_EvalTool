#!/usr/bin/env python3

import re
import sys
import argparse
from pathlib import Path
from shared import load_jobs
from pebble import ProcessPool
from multiprocessing import cpu_count

def _find_matching_brace(content: str, start_index: int, open_char: str = '{', close_char: str = '}') -> int:
    """
    Finds the index of the closing brace matching the one at start_index.
    Handles nested braces.
    Returns the index of the closing brace, or -1 if not found.
    """
    if start_index >= len(content) or content[start_index] != open_char:
        return -1
    
    stack = 1
    i = start_index + 1
    while i < len(content):
        char = content[i]
        if char == open_char:
            stack += 1
        elif char == close_char:
            stack -= 1
            if stack == 0:
                return i
        i += 1
    return -1

def _skip_whitespace_and_attributes(content: str, start_index: int) -> tuple[int, bool]:
    """
    Skips whitespace and GCC-style attributes (e.g. __attribute__((...))) 
    starting from start_index.
    
    Returns:
        (next_index, is_declaration_stopper)
        next_index: The index of the first character that is NOT whitespace or an attribute.
        is_declaration_stopper: True if we hit a ';' (indicating this is just a declaration).
    """

    i = start_index
    length = len(content)
    
    while i < length:
        char = content[i]
        
        # 1. Skip whitespace
        if char.isspace():
            i += 1
            continue
            
        # 2. Check for declaration stopper
        if char == ';':
            return i, True
        
        # 3. Check for body start
        if char == '{':
            return i, False
            
        # 4. Handle Attributes / Macros / Keywords
        # Need to skip things like __attribute__ ((...)) or __asm__ (...)
        # Peek ahead to see if it looks like a word followed by parens
        if char.isalpha() or char == '_':
            # Identify the word
            while i < length and (content[i].isalnum() or content[i] == '_'):
                i += 1
            
            # Check what follows the word (ignoring space)
            j = i
            while j < length and content[j].isspace():
                j += 1
                
            if j < length and content[j] == '(':
                # It is likely an attribute with arguments: attribute (...)
                # Skip the balanced parens
                close_index = _find_matching_brace(content, j, '(', ')')
                if close_index != -1:
                    i = close_index + 1
                    continue
            
            # If no parens follow, it's just a keyword (like 'const') 
            # We consumed the word, so we just continue the loop
            continue
            
        # If we hit something else (like a comma), it might be a multi-variable declaration
        # treating it as a stopper is usually safe
        return i, True

    return i, True

def _extract_function_from_buf(buf: str, func_name: str) -> str:
    """
    Parses a C/Preprocessed C file to find and extract the full definition 
    of a specific function.
    
    Strategy:
    1. Find all occurrences of the function name.
    2. For each, verify it is a definition (followed by (...) then {).
    3. If verified, scan backwards to find the start of the signature (return type).
    4. Extract the body using brace counting.
    """
    # 1. Iterate over all occurrences of the function name
    # We use a regex to find the name ensuring it's a whole word boundary
    name_pattern = re.compile(rf'\b{re.escape(func_name)}\b')
    
    for match in name_pattern.finditer(buf):
        name_start = match.start()
        name_end = match.end()
        
        # Expectation: Name -> whitespace -> '('
        i = name_end
        while i < len(buf) and buf[i].isspace():
            i += 1
            
        if i >= len(buf) or buf[i] != '(':
            continue # Not a function call/def (maybe a variable use)
       
        # Skip arguments (...)
        args_close = _find_matching_brace(buf, i, '(', ')')
        if args_close == -1:
            continue
            
        # Check what comes after arguments
        # Could be: '{' (Definition), ';' (Declaration), or attributes and then '{'
        post_args_index, is_stopper = _skip_whitespace_and_attributes(buf, args_close + 1)
        
        if is_stopper:
            continue
            
        if post_args_index >= len(buf) or buf[post_args_index] != '{':
            continue

        body_start_brace = post_args_index

        # 2. Find the start of the signature (Backtracking)
        # We scan backwards from the name to capture "void", "static", "extern", etc.
        # We stop if we hit a semicolon ';', closing brace '}', or start of file.

        def_start_index = name_start
        scan_idx = name_start - 1
        
        while scan_idx >= 0:
            char = buf[scan_idx]
            if char == ';' or char == '}':
                def_start_index = scan_idx + 1
                break

            # Note: We intentionally don't break on '{' to be safe, 
            # though global functions shouldn't be inside braces.
            scan_idx -= 1
        
        if scan_idx < 0:
            def_start_index = 0

        # 3. Extract the Body ---
        body_end_brace = _find_matching_brace(buf, body_start_brace, '{', '}')
        
        if body_end_brace != -1:
            full_code = buf[def_start_index : body_end_brace + 1].strip()
            return full_code

    raise Exception(f"Function {func_name} not found!")

def _process_function_pair(args):
    func_name = args.get("func_name")
    src_path = args.get("src_path")
    decomp_out_path = args.get("decomp_out_path")
    src_func_path = args.get("src_func_path")
    decomp_func_path = args.get("decomp_func_path")

    try:
        src_input = Path(src_path).read_text()
        src_match = _extract_function_from_buf(src_input, func_name)
    except Exception as e:
        print(f"[-] Error extracting {func_name} from {src_path}: {e}", file=sys.stderr)
        src_match = ""

    try:
        decomp_input = Path(decomp_out_path).read_text()
        decomp_match = _extract_function_from_buf(decomp_input, func_name)
    except Exception as e:
        print(f"[-] Error extracting {func_name} from {decomp_out_path}: {e}", file=sys.stderr)
        decomp_match = ""
    try:
        Path(src_func_path).write_text(src_match)
    except Exception as e:
        print(f"[-] Error writing to {src_func_path}: {e}", file=sys.stderr)
        return
    try:
        Path(decomp_func_path).write_text(decomp_match)
    except Exception as e:
        print(f"[-] Error writing to {decomp_func_path}: {e}", file=sys.stderr)
        return

def process_functions(worker_count: int):
    jobs = load_jobs()
    if(not jobs):
        print("[-] jobs.json not found! Try running prepare_jobs.py", file=sys.stderr)
        return

    print(f"[*] Processing functions for {len(jobs)} using {worker_count} workers...")
    with ProcessPool(max_workers=worker_count) as pool:
        future = pool.map(_process_function_pair, jobs)
        try:
            for _ in future.result():
                pass
        except Exception as e:
            print(f"[-] Error during function extraction pool execution: {e}", file=sys.stderr)
    
def main():
    parser = argparse.ArgumentParser(description="Parallel Binary Decompiler")
    parser.add_argument(
        "-p", "--processes", 
        type=int, 
        default=cpu_count(),
        help=f"Number of processes (default: {cpu_count()})"
    )
    args = parser.parse_args()
    process_functions(args.processes)

if __name__ == "__main__":
    main()
