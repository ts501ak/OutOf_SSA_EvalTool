import shared
import argparse
import json
from pathlib import Path

def load_json(file: Path):
    with open(str(file)) as f:
        content = f.read()
    stat = json.loads(content)
    return stat

parser = argparse.ArgumentParser()
parser.add_argument("--pathOverride","-p",dest="altPath",type=str,required=False,help="Path to the base direcetory")
parser.add_argument("--minThreshold","-i",dest="min",type=float,default=0.05,required=False)
parser.add_argument("--maxThreshold","-a",dest="max",type=float,default=0.75,required=False)
args = parser.parse_args()

if args.altPath:
    shared.changeBaseDir(Path(args.altPath))

jobs = load_json(shared.JOBS_FILE)
jobs = jobs["jobs"]
close = []
far = []
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

    minv = min(GEDValues)
    maxv = max(GEDValues)

    if (maxv - args.min * maxv) < minv:
        close.append((abs((maxv - maxv * args.min) - minv),f"{binary}::{func}"))
    if (maxv - maxv * args.max) > minv:
        far.append(((abs((maxv - maxv * args.max) - minv)),f"{binary}::{func}"))

far = sorted(far,key=lambda x : x[0],reverse=True)
#print(len(far))
close = sorted(close,key=lambda x : x[0],reverse=True)
#print(len(close))
print("Functions with close GED values from closets to least close:")
for x in range(min(10,len(close))):
    print("\t",close[x][1],sep="")

print("Functions with wide spread GED values from farest to nearest:")
for x in range(min(10,len(far))):
    print("\t",far[x][1],sep="")
#print(f"{excludedFuncs} were skipped!")
