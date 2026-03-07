import json
import itertools 
from pathlib import Path
from collections import defaultdict

def are_the_same(dictPaths : list[Path], threshold: float = 1) -> bool:
    dicts : list[dict] = []
    for x in dictPaths: #recover Dicts
        with open(x) as f:
            dicts.append(json.load(f))

    dictValues = [defaultdict(lambda : []) for _ in dicts]
    for i in range(len(dicts)): #group values by key
        aktDict = dicts[i]
        for key, value in aktDict.items():
            dictValues[i][value].append(key)


    hashes = [[] for _ in dicts]
    for i in range(len(dictValues)): #all SSA-Variables are named the same
        aktDict = dictValues[i]
        for val in aktDict.values():
            h = hash(tuple(sorted(val)))
            hashes[i].append(h)
    
    nonMatches = [0 for _ in range(len(hashes))]
    matches = 0
    non_matches = 0 
    for set_i, set_j in itertools.combinations(hashes, 2):
        matches += len(set_i & set_j)
        non_matches += len(set_i ^ set_j)

    total_comparisons = matches + non_matches
    if total_comparisons == 0:
        return True 

    return (non_matches / total_comparisons) <= threshold
