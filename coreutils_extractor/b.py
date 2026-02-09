import os
import re
import subprocess
from pathlib import Path

MAKEFILE = "Makefile"
OUTDIR = Path("someoutdir")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Add known variable expansions here:
KNOWN_VARS = {
    "copy_sources": [
        "src/copy.c",
        "src/copy-file-data.c",
        "src/cp-hash.c",
        "src/force-link.c",
        "src/force-link.h",
    ],
    "selinux_sources": [
        "src/selinux.c",
        "src/selinux.h",
    ],
    "src_b2sum_SOURCES": [
        "src/cksum.c",
        "src/blake2/blake2.h",
        "src/blake2/blake2-impl.h",
        "src/blake2/blake2b-ref.c",
        "src/blake2/b2sum.c",
        "src/blake2/b2sum.h",
    ],
}

# Regex to match "src_*_SOURCES = ..."
assign_re = re.compile(r'^(src_[A-Za-z0-9]+)_SOURCES\s*=\s*(.*)$')

# First, we read the Makefile into logical lines (merge continuations)
logical_lines = []
current = ""

with open(MAKEFILE, "r") as f:
    for raw in f:
        line = raw.rstrip()

        if line.endswith("\\"):
            current += line[:-1] + " "
            continue
        else:
            current += line
            logical_lines.append(current.strip())
            current = ""

if current:
    logical_lines.append(current.strip())

# Process each collected logical line
for line in logical_lines:

    m = assign_re.match(line)
    if not m:
        continue

    varname = m.group(1)
    sources_raw = m.group(2)

    # Replace known variables: $(var)
    def replace_var(match):
        name = match.group(1)
        if name in KNOWN_VARS:
            return " ".join(KNOWN_VARS[name])
        else:
            print(f"[SKIP] unresolved variable $({name}) in line: {line}")
            return None   # signal unresolved

    # Replace all occurrences of $(var)
    unresolved = False
    while "$(" in sources_raw:
        sources_raw_new = re.sub(r'\$\(([^)]+)\)', replace_var, sources_raw)
        if sources_raw_new is None or sources_raw_new == sources_raw:
            unresolved = True
            break
        sources_raw = sources_raw_new

    if unresolved:
        continue

    # Split into tokens
    tokens = sources_raw.split()
    c_files = [t for t in tokens if t.endswith(".c")]

    if not c_files:
        print(f"[SKIP] no .c files in: {line}")
        continue

    # Determine output file
    binary_name = varname.replace("src_", "")
    out_file = OUTDIR / f"{binary_name}.i"

    # Build GCC command
    cmd = ["gcc", "-E", "-P", "-I.", "-Ilib", "-std=gnu11"] + c_files

    print(f"[RUN] {' '.join(cmd)} > {out_file}")

    # Run GCC with error handling
    try:
        with open(out_file, "w") as outfile:
            subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, check=True)

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] GCC failed for {varname}: {e}")
        if e.stderr:
            print(f"[ERROR] stderr:\n{e.stderr.decode(errors='ignore')}")
        continue
