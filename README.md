## Setup

### Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python <binaryninja_path>/scripts/install_api.py --install-on-pyenv
```

### Initialize Submodules

```bash
git submodule update --init
```

### Place Binaries

Place binary files in the `dataset/bins/` directory. 

## Usage

### `pipeline.py`

Main orchestration script. Runs the complete decompilation pipeline.

**Options**:
- `-f, --fresh`: Overwrite existing files
- `-p, --processes`: Number of parallel processes
- `-t, --decompile-timeout`: Timeout per job in seconds
- `-m, --mem-limit`: Memory limit per process in GB

### `prepare_jobs.py`

Discovers functions in binaries and prepares decompilation jobs.

**Options**:
- `-p, --processes`: Number of parallel processes
- `-m, --mem-limit`: Memory limit per process in GB

### `decomp_bins.py`

Parallel decompilation of functions using multiple SSA algorithms.

**Options**:
- `-f, --fresh`: Overwrite existing results
- `-p, --processes`: Number of parallel workers
- `-t, --decompile-timeout`: Timeout per decompilation in seconds
- `-m, --mem-limit`: Memory limit per worker in GB

You can run `./decomp_bins.py` without `-f` to continue an aborted decompilation run or re-decompile some functions with different limits.

### `cmp.py`

Compares decompiled functions across SSA algorithm pairs and identifies outliers.

### `plot.py`

Visualizes decompilation results and compares SSA algorithms.

## Dataset Structure

```
dataset/
├── bins/          # Place your binary files here
│   ├── res/           # Decompilation results (generated)
│   │   └── <algo>/
│   │       └── <binary>/
│   │           └── <function>.c
│   ├── cmp/           # Comparison outputs (generated)
│   │   └── <algo1>_<algo2>/
│   │       └── *_differences.txt
│   ├── plots/         # Visualization outputs (generated)
│   │   └── <algo>/
│   │       └── *.png
│   ├── log.txt        # Pipeline log
│   └── decomp_log.txt # Decompilation log
```

## Metrics

### Structural Metrics
- num_variables: Average number of variables per function
- num_copy_assignments: Number of copy assignment operations

### Halstead Metrics
- total_operators: Total number of operators
- distinct_operators: Number of unique operators
- total_operands: Total number of operands
- distinct_operands: Number of unique operands
- halstead_vocabulary: Total number of unique operators + operands
- halstead_length: Total number of operators + operands
- halstead_volume: Amount of information in the code
- halstead_difficulty: Difficulty to understand/write the code
- halstead_effort: Effort to implement the code
- halstead_bugs: Estimated number of bugs

### Variable Analysis Metrics (averaged across all variables)
- var_defs: Average number of variable definitions
- var_uses: Average number of variable usages
- var_scope: Average number of basic blocks (scopes) a variable occurs in
- var_distance: Average of all live_range averages across all variables
- var_max_live_distance: Average of all variables' maximum live distances
- var_disjoint_webs: Average number of disjoint variable webs
