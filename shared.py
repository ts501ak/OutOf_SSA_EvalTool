from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent

DATASET_DIR = BASE_DIR / "dataset"
SRC_DIR = DATASET_DIR / "src"
BINS_DIR = DATASET_DIR / "bins"
DECOMP_DIR = DATASET_DIR / "bins_decomp"
FUNCS_DIR = DATASET_DIR / "bins_funcs"
RES_DIR = DATASET_DIR / "res"
GRAPH_EDIT_DISTANCE_TIMEOUT = 20

def get_unique_path(target_path: Path) -> Path:
    """Appends an underscore to the filename if the path already exists."""
    counter = 1
    new_path = target_path
    while new_path.exists():
        new_path = target_path.parent / f"{target_path.stem}{'_' * counter}{target_path.suffix}"
        counter += 1
    return new_path

def clear_and_create_dir(path: Path):
    """
    Deletes a directory if it exists and recreates it empty.
    """
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

