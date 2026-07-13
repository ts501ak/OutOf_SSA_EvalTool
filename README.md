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

Place binary files in the `dataset/bins/` directory and corresponding C source files in `dataset/src/`.

---

## Usage

### Pipeline

```bash
python pipeline.py
```

**Options:**
- `-f, --fresh` - Overwrite existing files
- `-p, --processes` - Number of parallel processes (default: CPU count)
- `-d, --decomp-processes` - Workers for decompilation
- `-t, --decompile-timeout` - Timeout per job in seconds (default: 600s)
- `-m, --mem-limit` - Memory limit per worker in GB (default: 10GB)
- `-z, --decomp-mem-limit` - Memory limit for decompilation in GB (default: 14GB)
- `-g, --graph-edit-timeout` - GED timeout in seconds (default: 870s)
- `-s, --decomp-comp-threshold` - Threshold for algorithm comparison

### Individual Stages

You can run individual stages to continue an aborted run or with new limits:

**Prepare Jobs:**
```bash
python prepare_jobs.py
```
Options: `-p` (processes), `-m` (mem-limit)

**Decompile:**
```bash
python decomp_bins.py -f
```
Options: `-f` (fresh), `-p` (processes), `-t` (decompile-timeout), `-m` (mem-limit)

**Process Functions:**
```bash
python process_functions.py -f
```
Options: `-f` (fresh), `-p` (processes), `-m` (mem-limit)

**Compute Results:**
```bash
python comp_res.py -f
```
Options: `-f` (fresh), `-p` (processes), `-m` (mem-limit), `-g` (graph-edit-timeout), `-s` (decomp-comp-threshold)

**Generate Plots:**
```bash
python makePlots.py
```
Options: `-r` (ged-reconstruct-timeouts), `-p` (pathOverride)

**Filter Interesting Functions:**
```bash
python filterInterestingFunctions.py
```
Options: `-p` (pathOverride)

---

## Dataset Structure

```
dataset/
├── bins/          # Place your binary files here
├── src/           # Place corresponding C source files here (.c)
├── jobs.json      # Function job queue (generated)
├── log.txt        # Pipeline log
├── decomp_log.txt # Decompilation log
├── conditional/   # Algorithm outputs
│   ├── decomp/           # Full decompiled functions
│   ├── decomp_func/      # Extracted decompiled functions
│   ├── src_func/         # Extracted source functions
│   ├── dict/             # SSA variable dictionaries (JSON)
│   ├── res/              # Comparison results
│   ├── plots/            # Visualizations
│   └── heinz_peter/      # Conditional-specific outputs
├── sreedhar/      # Algorithm outputs (same structure)
└── boissinot2008/ # Algorithm outputs (same structure)
```

---

## Metrics

### Graph Edit Distance (GED)
- `total_ged` - Total graph edit distance
- `matched_ged` - GED for matched components
- `unmatched_ged` - GED for unmatched components

### Structural Metrics
- `total_nodes1`, `total_nodes2` - Node counts
- `anz_zhk1`, `anz_zhk2` - Number of ZHKs
- `matched_zhk`, `halfmatched_zhk` - Matching counts

### Performance
- `time_needed` - Processing time
- `runs` - Successful runs
