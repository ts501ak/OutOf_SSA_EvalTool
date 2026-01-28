import networkx as nx
from typing import DefaultDict, Dict, Set, Tuple
from dependencyGraphfromC import DependencyGraphfromCFunction, CompareGraphs

class SimilarityMatching:
    MATCH_THRESHOLD = 0.5          
    SIG_DIST_PENALTY = 0.5 
    WEIGHT_PROXIMITY_DECAY = 0.1
    WEIGHT_HINT_BOOST = 0.15 

    def __init__(self, src_graph: nx.DiGraph, src_Code : str, decomp_graph: nx.DiGraph, decomp_Code : str):
        self._src_graph = src_graph
        self._decomp_graph = decomp_graph
        self._src_Code = src_Code
        self._decomp_Code = decomp_Code

        self._init_mapping()
        self._match_iterative()

    def _calc_unknown_nodes(self, graph: nx.DiGraph) -> Set[str]:
        candidates = set()
        for u, v, data in graph.edges(data=True):
            edge_type = data.get("type")
                        
            if edge_type == 'var':
                candidates.add(u) 
            elif edge_type == 'assig':
                candidates.add(v) 

        return candidates

    def _init_mapping(self):
        self.mapping = {}
        self.hint_mapping = {} 
        self.src_unknowns =  self._calc_unknown_nodes(self._src_graph)
        self.decomp_unknowns = self._calc_unknown_nodes(self._decomp_graph)
        compObj = CompareGraphs(self._src_Code,self._decomp_Code)
        safe_matches, unsafe_matches = compObj.getSameVars()

        for src_var, d_var in safe_matches.items():
            self.mapping[src_var] = (d_var, 1.0)
            self.src_unknowns.discard(src_var)
            self.decomp_unknowns.discard(d_var)
            print(src_var, d_var)

        for src_var, d_var in unsafe_matches.items():
            self.hint_mapping[src_var] = d_var

    def _get_signature(self, node: str, use_src_graph: bool) -> Dict[str, int]:
        """
        BFS to find features (Anchors or Matched Vars) and their Distances.
        Returns: {FeatureKey: ShortestDistance}
        """
        signature = {}
        visited = set()
        queue = [(node, 0)] 
        graph = self._src_graph if use_src_graph else self._decomp_graph

        while queue:
            curr, dist = queue.pop(0)
            if curr in visited: continue
            visited.add(curr)

            #TODO: consider limiting depth for performance
            #if dist > 20: continue

            for pred in graph.predecessors(curr):

                # Check for Anchors
                feature_key = None
                feature_dist = dist + 1
                e_type = graph.get_edge_data(pred, curr).get("type")

                if e_type in {'const', 'strConst'}:
                    feature_key = f"ANC:{pred}"
                elif e_type in {'func', 'array'}:
                    clean_name = pred.split('$', 1)[0]
                    feature_key = f"ANC:{clean_name}"
                elif e_type in {'var'}:
                    if use_src_graph:
                        if pred not in self.src_unknowns:
                            feature_key = f"MATCH:{self.mapping[pred][0]}"
                    else:
                        if pred not in self.decomp_unknowns:
                            feature_key = f"MATCH:{pred}"

                if feature_key and feature_key not in signature:
                        signature[feature_key] = feature_dist

                if e_type not in {'const', 'strConst', 'func', 'array' }:
                    if pred not in visited:
                        queue.append((pred, feature_dist))
        
        return signature

    def _compute_score(self, src_node: str, src_sig: Dict[str, int], decomp_node: str, decomp_sig: Dict[str, int]) -> float:
        """
        Calculates weighted Jaccard index based on Distance Alignment and Proximity.
        """
        common_features = src_sig.keys() & decomp_sig.keys()
        if not common_features: return 0.0

        intersection_score = 0.0
        
        for feature in common_features:
            d_src = src_sig[feature]
            d_decomp = decomp_sig[feature]
            
            # Alignment: Are they the same distance away?
            dist_diff = abs(d_src - d_decomp)
            alignment_factor = 1.0 / (1.0 + self.SIG_DIST_PENALTY * dist_diff)
            
            # Proximity: (Closer = Higher Score)
            avg_dist = (d_src + d_decomp) / 2.0
            proximity_factor = 1.0 / (1.0 + self.WEIGHT_PROXIMITY_DECAY * avg_dist)
            
            intersection_score += (alignment_factor * proximity_factor)

        union_size = len(src_sig.keys() | decomp_sig.keys())
        if union_size == 0: return 0.0

            
        score = intersection_score / union_size
        if self.hint_mapping.get(src_node) == decomp_node: 
            score += self.WEIGHT_HINT_BOOST

        return min(1, score)

    def _match_iterative(self):
        while True:
            # Pre compute signatures with new mapping
            src_sigs = { n: self._get_signature(n, True) for n in self.src_unknowns }
            
            decomp_sigs = { n: self._get_signature(n, False) for n in self.decomp_unknowns }

            if not src_sigs or not decomp_sigs:
                break

            # Compare every source unknown to every decomp unknown
            candidates = []
            for s_node, s_sig in src_sigs.items():
                for d_node, d_sig in decomp_sigs.items():
                    score = self._compute_score(s_node, s_sig, d_node, d_sig)
                    if score >= self.MATCH_THRESHOLD: 
                        candidates.append(( s_node, d_node, score ))

            # Sort best matches first
            candidates.sort(key=lambda x: x[2], reverse=True)

            # Apply Matches (Greedy Strategy)
            new_mapping = False 
            for c in candidates:
                s_node = c[0]
                d_node = c[1]
                score  = c[2]
                if s_node in self.src_unknowns and d_node in self.decomp_unknowns: 
                    new_mapping = True
                    self.src_unknowns.remove(s_node)
                    self.decomp_unknowns.remove(d_node)
                    self.mapping[s_node] = (d_node, score)

            if not new_mapping:
                break

    def print_results(self):
        print("\n" + "="*60)
        print(f"{'SOURCE VAR':<20} | {'DECOMP VAR':<20} | {'SCORE':<5}")
        print("-" * 60)
        sorted_matches = sorted(self.mapping.items(), key=lambda item: item[1][1], reverse=True)
        
        for src, (decomp, score) in sorted_matches:
            print(f"{src:<20} -> {decomp:<20} ({score:.2f})")
        print("="*60 + "\n")

def main():     
    try:
        with open("/home/ak/Downloads/ex1 1.txt") as f:
            cCode = f.read()
        dgrc = DependencyGraphfromCFunction()
        dg = dgrc.getDependencyGraph(cCode)
        
        with open("/home/ak/Downloads/ex2 1.txt") as f:
            cCode2 = f.read()
        dgrc2 = DependencyGraphfromCFunction()
        dgg = dgrc2.getDependencyGraph(cCode2)
        
        sm = SimilarityMatching(dg, cCode, dgg, cCode2)
        sm.print_results()
    except FileNotFoundError:
        print("Error: Test files not found. Please check file paths in main().")
    except NameError:
        print("Error: DependencyGraphfromCFunction not imported/defined.")

if __name__ == "__main__":
    main()
