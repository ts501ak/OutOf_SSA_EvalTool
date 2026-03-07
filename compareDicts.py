import json
import itertools 
from pathlib import Path
from collections import defaultdict

def are_the_same(dictPaths : list[Path], threshold: float = 1) -> bool:
    dicts : list[dict] = []
    for x in dictPaths: #recover Dicts
        with open(x) as f:
            dicts.append(json.load(f))

    hashes = []
    for c_dict in dicts:
        value_to_keys = defaultdict(list) #group values by key
        for key, value in c_dict.items():
            value_to_keys[value].append(key)
        
        hashes.append(
            { 
                tuple(sorted(keys))
                for keys in value_to_keys.values() 
            }
        )

    matches = 0
    non_matches = 0 
    for set_i, set_j in itertools.combinations(hashes, 2):
        matches += len(set_i & set_j)
        non_matches += len(set_i ^ set_j)

    total_comparisons = matches + non_matches
    if total_comparisons == 0:
        return True 

    return (non_matches / total_comparisons) <= threshold
