import shared
import argparse
import json
from pathlib import Path
import numpy as np

def load_json(file: Path):
    with open(str(file)) as f:
        content = f.read()
    stat = json.loads(content)
    return stat

parser = argparse.ArgumentParser()
parser.add_argument("--pathOverride","-p",dest="altPath",type=str,required=False,help="Path to the base direcetory")
args = parser.parse_args()

if args.altPath:
    shared.changeBaseDir(Path(args.altPath))

jobs = load_json(shared.JOBS_FILE)
jobs = jobs["jobs"]
distances = []
excludedFuncs = 0

for job in jobs:
    binary = job["bin"]
    func = job["func"]

    GEDValues = []
    try:
        for algo in shared.SSA_ALGOS:
            path = shared.get_res_dir(algo) / binary / f"{func}.json"
            funcRes = load_json(path)
            GEDValues.append(funcRes["total_ged"])
    except Exception as e:
        #print(f"Error while reading {binary}/{func}.json: {e}")
        excludedFuncs += 1
        continue

    distances.append((np.var(GEDValues),f"{binary}::{func}"))

distances = sorted(distances,key=lambda x : x[0],reverse=False)
print("Functions with close GED values from closets to least close:")
for x in range(min(10,len(distances))):
    print("\t",distances[x][1],sep="")
    #print("\t",int(distances[x][0]),": ",distances[x][1],sep="")
distances = sorted(distances,key=lambda x : x[0],reverse=True)
print("Functions with wide spread GED values from farest to nearest:")
for x in range(min(10,len(distances))):
    print("\t",distances[x][1],sep="")
    #print("\t",int(distances[x][0]),": ",distances[x][1],sep="")
#print(f"{excludedFuncs} were skipped!")
