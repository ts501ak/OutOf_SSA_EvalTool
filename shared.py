import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional


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

NAMES_TO_IGNORE = { ".gitignore" }
COMP_RES_TIMEOUT = 10 * 60 
GRAPH_EDIT_DISTANCE_TIMEOUT = 5 * 60 
DECOMP_TIMEOUT_SECONDS = 5 * 60 

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
