import json
import shutil
import resource
from pathlib import Path
from typing import Dict, List, Optional
from resource import setrlimit, RLIMIT_AS


BASE_DIR = Path(__file__).resolve().parent

DATASET_DIR = BASE_DIR / "dataset"
DEWOLF_DIR = BASE_DIR / "dewolf"

SRC_DIR = DATASET_DIR / "src"
BINS_DIR = DATASET_DIR / "bins"
DECOMP_DIR = DATASET_DIR / "decomp"
SRC_FUNC_DIR = DATASET_DIR / "src_func"
DECOMP_FUNC_DIR = DATASET_DIR / "decomp_func"
RES_DIR = DATASET_DIR / "res"
JOBS_FILES = DATASET_DIR / "jobs.json"
PLOTS_DIR = DATASET_DIR / "plots"

NAMES_TO_IGNORE = { ".gitignore" }
DECOMP_MEM_LIMIT_GB = 12 
COMP_RES_TIMEOUT = 10 * 60 
GRAPH_EDIT_DISTANCE_TIMEOUT = 5 * 60
DECOMP_TIMEOUT_SECONDS = 10 * 60 

#import os
#import time
#import psutil
#import threading
#def memory_monitor(interval=10):
#    process = psutil.Process(os.getpid())
#    while True:
#        mem_info = process.memory_info()
#        vms_gb = mem_info.vms / 1024**3
#        rss_gb = mem_info.rss / 1024**3
#        
#        print(f"[Worker {os.getpid()}] "
#              f"Virtual (AS): {vms_gb:.2f} GB | "
#              f"Physical (RSS): {rss_gb:.2f} GB")
#        
#        time.sleep(interval)

def init_worker(limit_gb: int):
    limit_bytes = limit_gb * 1024**3
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard))

    #monitor_thread = threading.Thread(target=memory_monitor, args=(10,), daemon=True)
    #monitor_thread.start()

def create_dir(path: Path):
    """Creates a dir"""
    path.mkdir(parents=False, exist_ok=True) #False is a sanity check

def clear_and_create_dir(path: Path):
    """
    Deletes a directory if it exists and recreates it empty.
    """
    if path.exists():
        shutil.rmtree(path)
    create_dir(path)

def save_jobs(jobs: List[Dict[str, str]]):
    """Saves Jobs to JSON"""
    try:
        with JOBS_FILES.open("w") as f:
            json.dump({"jobs": jobs}, f, indent=4)
    except Exception as e:
        print(f"Error saving jobs: {e}")

def load_jobs() -> Optional[List[Dict[str, str]]]:
    """Load Jobs from JSON"""
    try:
        with JOBS_FILES.open("r") as f:
            data = json.load(f)
        return data.get("jobs")
    except Exception as e:
        print(f"Error loading jobs {JOBS_FILES}: {e}")
    
    return None
