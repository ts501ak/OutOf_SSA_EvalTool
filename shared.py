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
SRC_DIR = DATASET_DIR / "src"
BINS_DIR = DATASET_DIR / "bins"
JOBS_FILE = DATASET_DIR / "jobs.json"

SSA_ALGOS = ["conditional", "sreedhar", "boissinot2008", "simple"]

NAMES_TO_IGNORE = { ".gitignore" }
DECOMP_COMP_TRESHOLD = 0
MEM_LIMIT_GB = 8 
DECOMP_MEM_LIMIT_GB = 12 
GRAPH_EDIT_DISTANCE_TIMEOUT = 7 * 60 + 30 
DECOMP_TIMEOUT_SECONDS = 10 * 60 

class InfoException(Exception):
    def __init__(self, message):
        super().__init__(message)

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

def get_src_file(bin_name: str) -> Path:
    return SRC_DIR / f"{bin_name}.c"

def get_base_dir(ssa_algo: str) -> Path:
    return DATASET_DIR / ssa_algo

def get_decomp_dir(ssa_algo: str) -> Path:
    return get_base_dir(ssa_algo) / "decomp"

def get_src_func_dir(ssa_algo: str) -> Path:
    return get_base_dir(ssa_algo) / "src_func"

def get_decomp_func_dir(ssa_algo: str) -> Path:
    return get_base_dir(ssa_algo) / "decomp_func"

def get_dict_dir(ssa_algo: str) -> Path: 
    return get_base_dir(ssa_algo) / "dict"

def get_res_dir(ssa_algo: str) -> Path:
    return get_base_dir(ssa_algo) / "res"

def get_plot_dir(ssa_algo: str) -> Path:
    return get_base_dir(ssa_algo) / "plots"

def get_decomp_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_decomp_dir(ssa_algo) / bin_name

def get_src_func_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_src_func_dir(ssa_algo) / bin_name

def get_decomp_func_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_decomp_func_dir(ssa_algo) / bin_name

def get_dict_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_dict_dir(ssa_algo) / bin_name 

def get_res_bin_dir(ssa_algo: str, bin_name: str) -> Path:
    return get_res_dir(ssa_algo) / bin_name

def get_decomp_file(ssa_algo: str, bin_name: str, func_name: str) -> Path:
    return get_decomp_bin_dir(ssa_algo, bin_name) / func_name

def get_src_func_file(ssa_algo: str, bin_name: str, func_name: str) -> Path:
    return get_src_func_bin_dir(ssa_algo, bin_name) / func_name

def get_decomp_func_file(ssa_algo: str, bin_name: str, func_name: str) -> Path:
    return get_decomp_func_bin_dir(ssa_algo, bin_name) / func_name

def get_dict_file(ssa_algo: str, bin_name: str, func_name: str) -> Path:
    return get_dict_bin_dir(ssa_algo, bin_name) / f"{func_name}.json"

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

def clear_log():
    try:
        os.remove(LOG_FILE)
    except Exception as e:
        print(f"Unable to remove log file {LOG_FILE}: {e}", file=sys.stderr)

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
