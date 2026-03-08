import json
import itertools 
from pathlib import Path
from collections import defaultdict

def are_the_same(dictPaths : list[Path], threshold: float = 0) -> bool:
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
    for i in range(len(hashes)):
        for h in hashes[i]:
            for j in range(len(hashes)):
                if h not in hashes[j]:
                    nonMatches[j] += 1
                else:
                    matches += 1

    if (matches == 0) and (sum(nonMatches) == 0): matches += 1 #prevent divideByZeorError

    if (sum(nonMatches)/(matches + sum(nonMatches))) <= threshold:
        return True
    else:
        return False 
