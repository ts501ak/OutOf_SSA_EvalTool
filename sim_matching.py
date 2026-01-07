from typing import Dict, Set, Tuple
import networkx as nx 
from dependencyGraphfromC import DependencyGraphfromCFunction


class SimilarityMatching:
    WEIGHT_ANCHOR_OVERLAP = 1.0   # Importance of shared constants/funcs
    WEIGHT_DIST_PENALTY = 0.3     # Penalty for distance mismatch (higher = stricter)
    MATCH_THRESHOLD = 0.1         # Minimum score to accept a match (0.0 to 1.0)

    def __init__(self, src_graph: nx.DiGraph, decomp_graph: nx.DiGraph):
        self._src_graph = src_graph
        self._decomp_graph = decomp_graph
        
        self.shared_anchors, self.src_unknowns = self._calc_shared_nodes(self._src_graph)
        _, self.decomp_unknowns = self._calc_shared_nodes(self._decomp_graph)
        
        print(f"Anchors found: {len(self.shared_anchors)}")
        print(f"Source Candidates: {len(self.src_unknowns)}")
        print(f"Decomp Candidates: {len(self.decomp_unknowns)}")
        
        try:
            self.src_dists = nx.shortest_path_length(self._src_graph, target="return")
        except nx.NetworkXNoPath:
            self.src_dists = {} 
            
        try:
            self.decomp_dists = nx.shortest_path_length(self._decomp_graph, target="return")
        except nx.NetworkXNoPath:
            self.decomp_dists = {}

        self.matches = self._match()

    def _calc_shared_nodes(self, graph: nx.DiGraph) -> Tuple[Set[str], Set[str]]:
        """
        Extracts 'Anchors' (known constants/funcs) and 'Candidates' (vars to match).
        Returns: (Set of Anchor Strings, Set of Candidate Node Names)
        """
        anchors = set()
        candidates = set()
        
        for u, v, data in graph.edges(data=True):
            edge_type = data.get("type")
            
            if edge_type in {'const', 'strConst'}:
                anchors.add(u)
            elif edge_type == 'func':
                clean_name = u.split('$', 1)[0]
                anchors.add(clean_name)
            
            if edge_type == 'var':
                candidates.add(u) 
            elif edge_type == 'assig':
                candidates.add(v) 
                
        return anchors, candidates

    def _get_signature(self, graph: nx.DiGraph, node: str) -> Set[str]:
        """
        Walk backwards from a node to find all values 
        (Constants, Strings, Functions) that contribute to this node.
        """
        signature = set()
        visited = set()
        queue = [node]

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            for pred in graph.predecessors(curr):
                edge_data = graph.get_edge_data(pred, curr)
                e_type = edge_data.get("type")

                if e_type in {'const', 'strConst'}:
                    signature.add(pred) 
                elif e_type == 'func':
                    clean_name = pred.split('$', 1)[0]
                    signature.add(clean_name)
                elif e_type == 'array':
                     clean_name = pred.split('$', 1)[0]
                     signature.add(clean_name)
                else:
                    if pred not in visited:
                        queue.append(pred)
        
        return signature

    def _compute_score(self, src_sig: Set[str], decomp_sig: Set[str], 
                       src_dist: int, decomp_dist: int) -> float:
        """
        Calculates similarity based on:
        1. Jaccard Index of Ancestors 
        2. Distance to Sink Similarity
        """

        if len(src_sig & decomp_sig) == 0: return 0.0

        # Jaccard Similarity (Set Overlap)
        intersection = len(src_sig & decomp_sig)
        union = len(src_sig | decomp_sig)
        
        if union == 0:
            jaccard = 0.0
        else:
            jaccard = intersection / union

        # Distance Similarity
        dist_diff = abs(src_dist - decomp_dist)
        dist_sim = 1.0 / (1.0 + (self.WEIGHT_DIST_PENALTY * dist_diff))

        # Weighted Average
        score = ((jaccard * self.WEIGHT_ANCHOR_OVERLAP) + dist_sim) / (self.WEIGHT_ANCHOR_OVERLAP + 1.0)
        
        return score

    def _match(self) -> Dict[str, Tuple[str, float]]:
        final_mapping = {}
        
        print("Generating signatures...")
        src_sigs = {n: self._get_signature(self._src_graph, n) for n in self.src_unknowns}
        decomp_sigs = {n: self._get_signature(self._decomp_graph, n) for n in self.decomp_unknowns}

        print("Comparing nodes...")
        # Greedy Matching Strategy
        candidates = []

        for s_node in self.src_unknowns:
            s_dist = self.src_dists.get(s_node, 999) # Default high dist if dead code
            
            for d_node in self.decomp_unknowns:
                d_dist = self.decomp_dists.get(d_node, 999)
                
                score = self._compute_score(src_sigs[s_node], decomp_sigs[d_node], int(s_dist), int(d_dist))
                
                if score >= self.MATCH_THRESHOLD:
                    candidates.append({
                        'src': s_node, 
                        'decomp': d_node, 
                        'score': score,
                        'debug': (src_sigs[s_node], decomp_sigs[d_node])
                    })

        candidates.sort(key=lambda x: x['score'], reverse=True)

        used_src = set()
        used_decomp = set()

        for c in candidates:
            if c['src'] not in used_src and c['decomp'] not in used_decomp:
                final_mapping[c['src']] = (c['decomp'], c['score'])
                used_src.add(c['src'])
                used_decomp.add(c['decomp'])

        return final_mapping

    def print_results(self):
        print("\n" + "="*50)
        print(f"{'SOURCE VAR':<15} | {'DECOMP VAR':<15} | {'SCORE':<5}")
        print("-" * 50)
        for src, (decomp, score) in self.matches.items():
            print(f"{src:<15} -> {decomp:<15} ({score:.2f})")
        print("="*50 + "\n")


def main():    
    with open("./easy_mod.c") as f:
        cCode = f.read()
    dgrc = DependencyGraphfromCFunction()
    dg = dgrc.getDependencyGraph(cCode)
    with open("./easy_mod_cond_decompiled.c") as f:
        cCode = f.read()
    dgrc = DependencyGraphfromCFunction()
    dgg = dgrc.getDependencyGraph(cCode)
    sm = SimilarityMatching(dg, dgg)
    sm.print_results()

if __name__ == "__main__":
    main()
