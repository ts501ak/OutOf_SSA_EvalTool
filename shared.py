import sys
import os
import json
import shutil
import resource
from pathlib import Path
from typing import Dict, List, Optional, TextIO

BASE_DIR = Path(__file__).resolve().parent

DEWOLF_DIR = BASE_DIR / "dewolf"
DATASET_DIR = BASE_DIR / "dataset"
LOG_FILE = DATASET_DIR / "log.txt"
DECOMP_LOG_FILE = DATASET_DIR / "decomp_log.txt"
BINS_DIR = DATASET_DIR / "bins"
RES_DIR = DATASET_DIR / "res"
JOBS_FILE = DATASET_DIR / "jobs.json"
NAMES_TO_IGNORE = { ".gitignore" }

SSA_ALGOS = ["conditional", "sreedhar", "boissinot2008" ]

MEM_LIMIT_GB = 10 
DECOMP_TIMEOUT_SECONDS = 10 * 60 

def init_worker(limit_gb: int):
    limit_bytes = limit_gb * 1024**3
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard))

def log_and_print(message, log_file_path: Path = LOG_FILE, print_file: TextIO = sys.stdout):
    print(message, file = print_file)
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(str(message) + "\n")
 
# helper functions; i know that the naming is bad
def get_bin_file(bin_name: str) -> Path:
    return BINS_DIR / bin_name

def get_res_dir(ssa_algo: str) -> Path:
    return RES_DIR / ssa_algo

#def get_plot_dir(ssa_algo: str) -> Path:
#    return get_base_dir(ssa_algo) / "plots"

def get_res_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_res_dir(ssa_algo) / bin_name

def get_res_file(ssa_algo: str, bin_name: str, func_name: str) -> Path:
    return get_res_bin_dir(ssa_algo, bin_name) / f"{func_name}.json"

def clear_and_create_dir(path: Path, log_file: Path = LOG_FILE):
    """
    Deletes a directory if it exists and recreates it empty.
    """
    try:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=False, exist_ok=True) #False is a sanity check
    except Exception as e:
        log_and_print(f"Unable to clear dir {path}: {e}", 
                      log_file_path=log_file, print_file=sys.stderr) 

def _clear_log_file(file: Path):
    try:
        if os.path.exists(file):
            os.remove(file)
    except Exception as e:
        print(f"Unable to remove log file {file}: {e}", file=sys.stderr)

def clear_log():
    _clear_log_file(LOG_FILE)
    _clear_log_file(DECOMP_LOG_FILE)

def save_jobs(jobs: List[Dict[str, str]]):
    """Saves Jobs to JSON"""
    try:
        with JOBS_FILE.open("w") as f:
            json.dump({"jobs": jobs}, f, indent=4)
    except Exception as e:
        print(f"Error saving jobs: {e}")

def load_jobs() -> Optional[List[Dict[str, str]]]:
    """Load Jobs from JSON"""
    try:
        with JOBS_FILE.open("r") as f:
            data = json.load(f)
        return data.get("jobs")
    except Exception as e:
        print(f"Error loading jobs {JOBS_FILE}: {e}")
    
    return None
