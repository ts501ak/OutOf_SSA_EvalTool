import re
from pathlib import Path
from typing import Optional, Union

def find_matching_brace(content: str, start_index: int, open_char: str = '{', close_char: str = '}') -> int:
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

def skip_whitespace_and_attributes(content: str, start_index: int) -> tuple[int, bool]:
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
                close_index = find_matching_brace(content, j, '(', ')')
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

def extract_function(file_path: Union[str, Path], func_name: str) -> Optional[str]:
    """
    Parses a C/Preprocessed C file to find and extract the full definition 
    of a specific function.
    
    Strategy:
    1. Find all occurrences of the function name.
    2. For each, verify it is a definition (followed by (...) then {).
    3. If verified, scan backwards to find the start of the signature (return type).
    4. Extract the body using brace counting.
    """
    target_path = Path(file_path)
    
    if not target_path.exists():
        return None

    try:
        content = target_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Error reading {target_path}: {e}")
        return None

    # 1. Iterate over all occurrences of the function name
    # We use a regex to find the name ensuring it's a whole word boundary
    name_pattern = re.compile(rf'\b{re.escape(func_name)}\b')
    
    for match in name_pattern.finditer(content):
        name_start = match.start()
        name_end = match.end()
        
        # Expectation: Name -> whitespace -> '('
        i = name_end
        while i < len(content) and content[i].isspace():
            i += 1
            
        if i >= len(content) or content[i] != '(':
            continue # Not a function call/def (maybe a variable use)
       
        # Skip arguments (...)
        args_close = find_matching_brace(content, i, '(', ')')
        if args_close == -1:
            continue
            
        # Check what comes after arguments
        # Could be: '{' (Definition), ';' (Declaration), or attributes and then '{'
        post_args_index, is_stopper = skip_whitespace_and_attributes(content, args_close + 1)
        
        if is_stopper:
            continue
            
        if post_args_index >= len(content) or content[post_args_index] != '{':
            continue

        body_start_brace = post_args_index

        # 2. Find the start of the signature (Backtracking)
        # We scan backwards from the name to capture "void", "static", "extern", etc.
        # We stop if we hit a semicolon ';', closing brace '}', or start of file.

        def_start_index = name_start
        scan_idx = name_start - 1
        
        while scan_idx >= 0:
            char = content[scan_idx]
            if char == ';' or char == '}':
                def_start_index = scan_idx + 1
                break

            # Note: We intentionally don't break on '{' to be safe, 
            # though global functions shouldn't be inside braces.
            scan_idx -= 1
        
        if scan_idx < 0:
            def_start_index = 0

        # 3. Extract the Body ---
        body_end_brace = find_matching_brace(content, body_start_brace, '{', '}')
        
        if body_end_brace != -1:
            full_code = content[def_start_index : body_end_brace + 1].strip()
            return full_code

    return None
