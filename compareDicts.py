from pathlib import Path
import json
from collections import defaultdict

def are_the_same(dictPaths : list[Path],threshold = 0) -> True|False:
    dicts : list[dict] = []
    for x in dictPaths: #recover Dicts
        with open(x) as f:
            dicts.append(json.loads(f.read()))


    dictValues = [defaultdict(lambda : []) for _ in dicts]
    for i in range(len(dicts)): #group values by key
        aktDict = dicts[i]
        for key, value in aktDict.items():
            dictValues[value].append(key)


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

    if matches == 0: matches += 1

    if (sum(nonMatches)/matches) <= threshold:
        return True
    else:
        return False
