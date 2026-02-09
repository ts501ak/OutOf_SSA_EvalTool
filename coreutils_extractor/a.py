import os
import re
import subprocess
from pathlib import Path

MAKEFILE = "Makefile"
OUTDIR = Path("someoutdir")
OUTDIR.mkdir(parents=True, exist_ok=True)

# Regex:
#   src_unexpand_SOURCES = src/unexpand.c src/expand-common.c
pattern = re.compile(r'^(src_[a-zA-Z0-9]+)_SOURCES\s*=\s*(.*)$')

with open(MAKEFILE, "r") as f:
    for line in f:
        line = line.strip()

        m = pattern.match(line)
        if not m:
            continue

        varname = m.group(1)
        sources_raw = m.group(2)

        # Skip variable references like $(...)  
        if "$(" in sources_raw:
            print(f"[SKIP] contains variable reference: {line}")
            continue

        # Extract .c files
        sources = sources_raw.split()
        c_files = [s for s in sources if s.endswith(".c")]

        if not c_files:
            print(f"[SKIP] no .c files found in: {line}")
            continue

        # Output file path
        binary_name = varname.replace("src_", "")
        out_file = OUTDIR / f"{binary_name}.i"

        # GCC command
        cmd = [
            "gcc",
            "-E", "-P",
            "-I.", "-Ilib",
            "-std=gnu11"
        ] + c_files

        print(f"[RUN] {' '.join(cmd)} > {out_file}")

        # Attempt GCC call
        try:
            with open(out_file, "w") as outfile:
                subprocess.run(cmd, stdout=outfile, stderr=subprocess.PIPE, check=True)

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] GCC failed for {varname}: {e}")
            print(f"[ERROR] stderr:\n{e.stderr.decode(errors='ignore')}")
            continue
