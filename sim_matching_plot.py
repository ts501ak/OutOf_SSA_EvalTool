import argparse
import os
from collections import defaultdict
import networkx as nx
from typing import Dict, Set
from dependencyGraphfromC import DependencyGraphfromCFunction, CompareGraphs, mergeDicts
import matplotlib.pyplot as plt
from time import time_ns
import processVariable

def save_zhk_plot(graph: nx.Graph, filename: str, title: str):
    """Saves a well-spaced layout of a ZHK subgraph."""
    if not graph.nodes():
        return
        
    num_nodes = len(graph.nodes())
    figsize = max(8, int((num_nodes ** 0.5) * 1.5))
    plt.figure(figsize=(figsize, figsize))
    
    # Spring layout for good spacing
    pos = nx.spring_layout(graph, k=2.5 / (num_nodes ** 0.5) if num_nodes > 0 else 1, iterations=50)

    # Note: These are undirected subgraphs, so no arrows
    nx.draw_networkx_nodes(graph, pos, node_color="#3498db", node_size=1200, alpha=0.9, edgecolors="white")
    nx.draw_networkx_edges(graph, pos, width=1.5, edge_color="#7f8c8d", alpha=0.6)
    nx.draw_networkx_labels(graph, pos, font_size=9, font_family="sans-serif", font_weight="bold")

    plt.title(title, fontsize=16, pad=20)
    plt.axis('off')
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

class StatisticsClass:
    def __init__(self):
        self.runs = 0
        self.anzZhk1 = []
        self.anzZhk2 = []
        self.matchedZhk = 0
        self.halfmatchedZhk = 0
        self.notmatchedZhk = 0
        self.totalGED = 0
        self.matchedGED = 0
        self.unmatchedGED = 0
        
        # --- Baseline metrics ---
        self.baselineGED = 0
        self.baselineTime = 0
        self.baselineTimeout = False

        self.savePoints = []
        self.totalNodes1 = []
        self.totalNodes2 = []
        self.sizeZhk = []
        self.timeOuts = 0
        self.matchedTimeOuts = 0
        self.unmatchedTimeOuts = 0
        self.notimeOut = 0
        self.timeNeeded = []
        self.lastGED = 0
        self.sizeUnmatchedZHK = []
        self.sizeMatchedZHK = []

    def merge(self, other: 'StatisticsClass'):
        self.runs += other.runs
        self.anzZhk1.extend(other.anzZhk1)
        self.anzZhk2.extend(other.anzZhk2)
        self.matchedZhk += other.matchedZhk
        self.halfmatchedZhk += other.halfmatchedZhk
        self.notmatchedZhk += other.notmatchedZhk
        self.totalGED += other.totalGED
        self.baselineGED += other.baselineGED
        self.baselineTime += other.baselineTime
        self.savePoints.extend(other.savePoints)
        self.totalNodes1.extend(other.totalNodes1)
        self.totalNodes2.extend(other.totalNodes2)
        self.sizeZhk.extend(other.sizeZhk)
        self.timeOuts += other.timeOuts
        self.notimeOut += other.notimeOut
        self.timeNeeded.extend(other.timeNeeded)
        self.sizeUnmatchedZHK.extend(other.sizeUnmatchedZHK)
        self.sizeMatchedZHK.extend(other.sizeMatchedZHK)
        self.unmatchedGED += other.unmatchedGED
        self.matchedGED += other.matchedGED
        self.matchedTimeOuts += other.matchedTimeOuts
        self.unmatchedTimeOuts += other.unmatchedTimeOuts
        return self

    def __iadd__(self, other):
        return self.merge(other)

    def to_dict(self):
        def safe_avg(data): return sum(data) / len(data) if data else 0
        total_attempts = self.timeOuts + self.notimeOut
        
        return {
            "runs": self.runs,
            "baseline_ged": self.baselineGED,
            "baseline_time": self.baselineTime,
            "baseline_timeout": self.baselineTimeout,
            "total_ged": self.totalGED,
            "avg_source_zhk": safe_avg(self.anzZhk1),
            "avg_decomp_zhk": safe_avg(self.anzZhk2),
            "matched_zhk": self.matchedZhk + self.halfmatchedZhk,
            "not_matched_zhk": self.notmatchedZhk,
            "avg_save_points": safe_avg(self.savePoints),
            "avg_zhk_size": safe_avg(self.sizeZhk),
            "ged_no_timeout": self.notimeOut,
            "ged_timeouts": self.timeOuts,
            "avg_ged_time": round(sum(self.timeNeeded) / total_attempts, 2) if total_attempts > 0 else 0,
            "ged_times" : self.timeNeeded,
            "unmatched_ZHK_size": self.sizeUnmatchedZHK,
            "matched_ZHK_size" : self.sizeMatchedZHK,
            "matched_ged" : self.matchedGED,
            "unmatched_ged" : self.unmatchedGED,
            "matchedTimeouts" : self.matchedTimeOuts,
            "unmatchedTimeouts" : self.unmatchedTimeOuts
        }

    def printResults(self):
        data = self.to_dict()
        print('%-24s%-20i' % ("#compared code samples", data["runs"]))
        print('-' * 44)
        print('%-24s%-20s' % ("BASELINE GED", str(data["baseline_ged"]) + (" (Timeout)" if data["baseline_timeout"] else "")))
        print('%-24s%-20s' % ("BASELINE TIME", f"{data['baseline_time']:.4f}s"))
        print('-' * 44)
        print('%-24s%-20i' % ("ZHK TOTAL GED", data["total_ged"]))
        print('%-24s%-20f' % ("average source zhk", data["avg_source_zhk"]))
        print('%-24s%-20f' % ("average decomp zhk", data["avg_decomp_zhk"]))
        print('%-24s%-20i' % ("#matched zhk", data["matched_zhk"]))
        print('%-24s%-20i' % ("#not matched zhk", data["not_matched_zhk"]))
        print('%-24s%-20f' % ("average save Points", data["avg_save_points"]))
        print('%-24s%-20f' % ("average zhk size", data["avg_zhk_size"]))
        print('%-24s%-20i' % ("GED no Timeout", data["ged_no_timeout"]))
        print('%-24s%-20i' % ("GED Timeouts", data["ged_timeouts"]))
        print('%-24s%-20s' % ("average GED Time", str(data["avg_ged_time"]) + "s"))

class SimilarityMatching:
    MATCH_THRESHOLD = 0.5          
    SIG_DIST_PENALTY = 0.5 
    WEIGHT_PROXIMITY_DECAY = 0.1
    WEIGHT_HINT_BOOST = 0.15 

    def __init__(self,  src_Code : str, decomp_Code : str):
        self._src_Code = src_Code
        self._decomp_Code = decomp_Code
        
        self._src_graph = processVariable._DependencyGraphObj.getDependencyGraph(self._src_Code)
        self._decomp_graph = processVariable._DependencyGraphObj.getDependencyGraph(self._decomp_Code) 

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

        compObj = CompareGraphs(self._src_Code,self._decomp_Code,self._src_graph,self._decomp_graph)
        safe_matches, unsafe_matches, constants = compObj.getSameVars()
        del compObj
        __import__('pprint').pprint(constants)
        exit(0)
        self.constants = constants

        for src_var, d_var in safe_matches.items():
            # Add Match Type Metadata to safe matches
            self.mapping[src_var] = (d_var, 1.0, "Exact (Name/Type)")
            self.src_unknowns.discard(src_var)
            self.decomp_unknowns.discard(d_var)

        for src_var, d_var in unsafe_matches.items():
            self.hint_mapping[src_var] = d_var

    def _get_signature(self, node: str, use_src_graph: bool) -> Dict[str, int]:
        signature = {}
        visited = set()
        queue = [(node, 0)] 
        graph = self._src_graph if use_src_graph else self._decomp_graph

        while queue:
            curr, dist = queue.pop(0)
            if curr in visited: continue
            visited.add(curr)

            for pred in graph.predecessors(curr):
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
        common_features = src_sig.keys() & decomp_sig.keys()
        if not common_features: return 0.0

        intersection_score = 0.0
        
        for feature in common_features:
            d_src = src_sig[feature]
            d_decomp = decomp_sig[feature]
            
            dist_diff = abs(d_src - d_decomp)
            alignment_factor = 1.0 / (1.0 + self.SIG_DIST_PENALTY * dist_diff)
            
            avg_dist = ((d_src + d_decomp) / 2.0 - 1)
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
            src_sigs = { n: self._get_signature(n, True) for n in self.src_unknowns }
            decomp_sigs = { n: self._get_signature(n, False) for n in self.decomp_unknowns }

            if not src_sigs or not decomp_sigs:
                break

            candidates = []
            for s_node, s_sig in src_sigs.items():
                for d_node, d_sig in decomp_sigs.items():
                    score = self._compute_score(s_node, s_sig, d_node, d_sig)
                    if score >= self.MATCH_THRESHOLD: 
                        candidates.append(( s_node, d_node, score ))

            candidates.sort(key=lambda x: x[2], reverse=True)

            new_mapping = False 
            for c in candidates:
                s_node = c[0]
                d_node = c[1]
                score  = c[2]
                if s_node in self.src_unknowns and d_node in self.decomp_unknowns: 
                    new_mapping = True
                    self.src_unknowns.remove(s_node)
                    self.decomp_unknowns.remove(d_node)
                    # Add Match Type Metadata to Iterative/Topology matches
                    self.mapping[s_node] = (d_node, score, "Iterative (Topology)")

            if not new_mapping:
                break

    def print_results(self):
        print("\n" + "="*80)
        print(f"{'SOURCE VAR':<20} | {'DECOMP VAR':<20} | {'SCORE':<6} | {'MATCH TYPE'}")
        print("-" * 80)
        sorted_matches = sorted(self.mapping.items(), key=lambda item: item[1][1], reverse=True)
        
        for src, val in sorted_matches:
            print(f"{src:<20} -> {val[0]:<20} ({val[1]:.2f})   [{val[2]}]")
        print("="*80 + "\n")

    def computeGraphEditDistance(self, timeout=20, out_dir=None) -> StatisticsClass:
        stats = StatisticsClass()
        stats.runs += 1
        stats.lastGED = 0
        stats.totalNodes1.append(len(self._src_graph.nodes(data=False)))
        stats.totalNodes2.append(len(self._decomp_graph.nodes(data=False)))

        subgraphDict = defaultdict(lambda: [[], []])
        ged_log = [] 
        
        # =================================================================
        # EXPORT ANCHORS & DIRECTORY SETUP (WITH METADATA)
        # =================================================================
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            print(f"Exporting ZHK plots, GED logs, and Anchor Mappings to {out_dir}/")
            
            anchor_file = os.path.join(out_dir, "matched_anchors.txt")
            with open(anchor_file, "w") as f:
                f.write("=== MATCHED VARIABLES (ANCHORS) ===\n")
                f.write(f"{'SOURCE NODE':<25} | {'DECOMP NODE':<25} | {'SCORE':<6} | {'MATCH TYPE'}\n")
                f.write("-" * 85 + "\n")
                
                # Sort the matched variables by score (highest first)
                sorted_vars = sorted(self.mapping.items(), key=lambda item: item[1][1], reverse=True)
                for src, val in sorted_vars:
                    # val is (decomp_node, score, match_type)
                    f.write(f"{src:<25} | {val[0]:<25} | {val[1]:<6.2f} | {val[2]}\n")
                
                f.write("\n=== MATCHED CONSTANTS (ANCHORS) ===\n")
                f.write(f"{'SOURCE CONSTANT':<25} | {'DECOMP CONSTANT':<25} | {'SCORE':<6} | {'MATCH TYPE'}\n")
                f.write("-" * 85 + "\n")
                for src_const, decomp_const in sorted(self.constants.items(), key=lambda x: str(x[0])):
                    f.write(f"{str(src_const):<25} | {str(decomp_const):<25} | 1.00   | Exact (Value)\n")
                
                if self.hint_mapping:
                    f.write("\n=== HEURISTIC HINTS (NOT STRICTLY ANCHORED) ===\n")
                    f.write(f"{'SOURCE NODE':<25} | {'DECOMP NODE':<25} | {'MATCH TYPE'}\n")
                    f.write("-" * 85 + "\n")
                    for h_src, h_decomp in self.hint_mapping.items():
                        f.write(f"{h_src:<25} | {h_decomp:<25} | Unsafe/Hint Match\n")
        
        # =================================================================
        # BASELINE FULL-GRAPH GED COMPUTATION
        # =================================================================
        undirSrcGraph = self._src_graph.to_undirected()
        undirdecompGraph = self._decomp_graph.to_undirected()

        def baseline_node_match(n1, n2):
            return n1.get("name") == n2.get("name")

        start = time_ns()
        baseline_ged = nx.graph_edit_distance(
            undirSrcGraph, 
            undirdecompGraph, 
            node_match=baseline_node_match, 
            timeout=timeout
        )
        end = time_ns()
        baseline_time = (end - start) / 1000000000
        baseline_timeout = (baseline_time + 1) > timeout

        stats.baselineGED = baseline_ged if baseline_ged is not None else -1
        stats.baselineTime = baseline_time
        stats.baselineTimeout = baseline_timeout
        
        ged_log.append(f"BASELINE FULL-GRAPH GED: {stats.baselineGED}")
        ged_log.append(f"BASELINE TIME: {baseline_time:.4f}s (Timeout = {baseline_timeout})")
        ged_log.append("-" * 40)

        # Unpack val[0] because mapping now stores (decomp_node, score, match_type)
        equivDict = {a: val[0] for a, val in self.mapping.items()}
        equivDict = mergeDicts(equivDict, self.constants)
        equivDict = defaultdict(lambda: None, equivDict)
        equivDict["return"] = "return"

        def areSameNode(n1, n2):
            if (equivDict[n1["name"]] == n2["name"]) or (equivDict[n2["name"]] == n1["name"]):
                return True
            else:
                return False

        gscrNodes = equivDict.keys()
        gdecompNodes = equivDict.values()

        stats.savePoints.append(len(equivDict))

        g1zhks = undirSrcGraph.subgraph([x for x in self._src_graph.nodes(data=False) if x not in gscrNodes])
        g2zhks = undirdecompGraph.subgraph([x for x in self._decomp_graph.nodes(data=False) if x not in gdecompNodes])

        stats.anzZhk1.append(len(list(nx.connected_components(g1zhks))))
        stats.anzZhk2.append(len(list(nx.connected_components(g2zhks))))

        sizeConComp = []

        for x in nx.connected_components(g1zhks):
            sizeConComp.append(len(x))
            connectedSepeartors = []
            y = set(gscrNodes).union(x)
            y = undirSrcGraph.subgraph(y)
            for z in y.edges(data=False):
                if (z[0] in gscrNodes) and (z[1] in x):
                    connectedSepeartors.append(equivDict[z[0]])
                elif (z[1] in gscrNodes) and (z[0] in x):
                    connectedSepeartors.append(equivDict[z[1]])
            
            connectedSepeartors = tuple(sorted(list(set(connectedSepeartors))))
            subgraphDict[connectedSepeartors][0].append(x)
        

        for x in nx.connected_components(g2zhks):
            sizeConComp.append(len(x))
            connectedSepeartors = []
            y = set(gdecompNodes).union(x)
            y = undirdecompGraph.subgraph(y)
            for z in y.edges(data=False):
                if (z[0] in gdecompNodes) and (z[1] in x):
                    connectedSepeartors.append(z[0])
                elif (z[1] in gdecompNodes) and (z[0] in x):
                    connectedSepeartors.append(z[1])
            
            connectedSepeartors = tuple(sorted(list(set(connectedSepeartors))))
            subgraphDict[connectedSepeartors][1].append(x)
        
        if len(sizeConComp) > 0:
            stats.sizeZhk.append(sum(sizeConComp)/len(sizeConComp))
        else:
            stats.sizeZhk.append(0)

        remainsrc = set()
        remaindecomp = set()

        match_index = 0
        unmatched_src_index = 0
        unmatched_decomp_index = 0

        for zz in subgraphDict.keys():
            if (len(subgraphDict[zz][0]) == 1) and (len(subgraphDict[zz][1]) == 1):
                stats.matchedZhk += 2
                srcGraph = subgraphDict[zz][0][0].union(gscrNodes)
                decompGraph = subgraphDict[zz][1][0].union(gdecompNodes)
                
                current_idx = match_index
                if out_dir:
                    save_zhk_plot(undirSrcGraph.subgraph(srcGraph), os.path.join(out_dir, f"match_{current_idx}_exact_src.png"), f"Exact Match {current_idx} (Source)")
                    save_zhk_plot(undirdecompGraph.subgraph(decompGraph), os.path.join(out_dir, f"match_{current_idx}_exact_decomp.png"), f"Exact Match {current_idx} (Decomp)")
                match_index += 1

                stats.sizeMatchedZHK.append(len(subgraphDict[zz][0][0]))
                stats.sizeMatchedZHK.append(len(subgraphDict[zz][1][0]))
                start = time_ns()
                ged = nx.graph_edit_distance(undirSrcGraph.subgraph(srcGraph), undirdecompGraph.subgraph(decompGraph), node_match=areSameNode, timeout=timeout)
                if ged is None:
                    ged = -1 
                
                stats.lastGED += ged
                stats.matchedGED += ged
                end = time_ns()
                time_taken = (end-start)/1000000000
                stats.timeNeeded.append(time_taken)
                
                is_timeout = (time_taken + 1) > timeout
                ged_log.append(f"Exact Match {current_idx}: GED = {ged}, Time = {time_taken:.4f}s, Timeout = {is_timeout}")
                
                if is_timeout:
                    stats.timeOuts += 1
                    stats.matchedTimeOuts += 1
                else:
                    stats.notimeOut += 1
            elif ((len(subgraphDict[zz][0])) != 0) and ((len(subgraphDict[zz][1])) != 0):
                srcSet = set()
                decompSet = set()
                for aa in subgraphDict[zz][0]:
                    srcSet.update(aa)
                    stats.sizeMatchedZHK.append(len(aa))
                    stats.halfmatchedZhk += 1
                srcSet.update(gscrNodes)
                for bb in subgraphDict[zz][1]:
                    decompSet.update(bb)
                    stats.sizeMatchedZHK.append(len(bb))
                    stats.halfmatchedZhk += 1
                decompSet.update(gdecompNodes)

                # --- EXPORT PARTIAL ZHK ---
                current_idx = match_index
                if out_dir:
                    save_zhk_plot(undirSrcGraph.subgraph(srcSet), os.path.join(out_dir, f"match_{current_idx}_partial_src.png"), f"Partial Match {current_idx} (Source)")
                    save_zhk_plot(undirdecompGraph.subgraph(decompSet), os.path.join(out_dir, f"match_{current_idx}_partial_decomp.png"), f"Partial Match {current_idx} (Decomp)")
                match_index += 1

                start = time_ns()
                ged = nx.graph_edit_distance(undirSrcGraph.subgraph(srcSet), undirdecompGraph.subgraph(decompSet), node_match=areSameNode, timeout=timeout)
                if ged is None:
                    ged = -1
                stats.lastGED += ged
                stats.matchedGED += ged
                end = time_ns()
                time_taken = (end-start)/1000000000
                stats.timeNeeded.append(time_taken)
                
                is_timeout = (time_taken + 1) > timeout
                ged_log.append(f"Partial Match {current_idx}: GED = {ged}, Time = {time_taken:.4f}s, Timeout = {is_timeout}")
                
                if is_timeout:
                    stats.timeOuts += 1
                    stats.matchedTimeOuts += 1
                else:
                    stats.notimeOut += 1
            else:
                for bb in subgraphDict[zz][0]:
                    # --- EXPORT INDIVIDUAL UNMATCHED ZHK (SOURCE) ---
                    if out_dir:
                        unmatched_sub = bb.union(gscrNodes)
                        save_zhk_plot(undirSrcGraph.subgraph(unmatched_sub), os.path.join(out_dir, f"unmatched_{unmatched_src_index}_src.png"), f"Unmatched ZHK {unmatched_src_index} (Source)")
                        unmatched_src_index += 1

                    remainsrc.update(bb)
                    stats.sizeUnmatchedZHK.append(len(bb))
                    stats.notmatchedZhk += 1
                for cc in subgraphDict[zz][1]:
                    # --- EXPORT INDIVIDUAL UNMATCHED ZHK (DECOMP) ---
                    if out_dir:
                        unmatched_sub = cc.union(gdecompNodes)
                        save_zhk_plot(undirdecompGraph.subgraph(unmatched_sub), os.path.join(out_dir, f"unmatched_{unmatched_decomp_index}_decomp.png"), f"Unmatched ZHK {unmatched_decomp_index} (Decomp)")
                        unmatched_decomp_index += 1

                    remaindecomp.update(cc)
                    stats.sizeUnmatchedZHK.append(len(cc))
                    stats.notmatchedZhk += 1
        
        remainsrc.update(gscrNodes)
        remaindecomp.update(gdecompNodes)

        # --- EXPORT COMBINED UNMATCHED REST ZHK ---
        if out_dir:
            if remainsrc:
                save_zhk_plot(undirSrcGraph.subgraph(remainsrc), os.path.join(out_dir, "unmatched_rest_combined_src.png"), "Combined Unmatched Rest (Source)")
            if remaindecomp:
                save_zhk_plot(undirdecompGraph.subgraph(remaindecomp), os.path.join(out_dir, "unmatched_rest_combined_decomp.png"), "Combined Unmatched Rest (Decomp)")

        start = time_ns()
        ged = nx.graph_edit_distance(undirSrcGraph.subgraph(remainsrc), undirdecompGraph.subgraph(remaindecomp), node_match=areSameNode, timeout=timeout)
        if ged is None:
            ged = -1
            
        stats.lastGED += ged
        stats.unmatchedGED += ged
        end = time_ns()
        time_taken = (end-start)/1000000000
        stats.timeNeeded.append(time_taken)
        
        is_timeout = (time_taken + 1) > timeout
        ged_log.append(f"Combined Unmatched Rest: GED = {ged}, Time = {time_taken:.4f}s, Timeout = {is_timeout}")

        if is_timeout:
            stats.timeOuts += 1
            stats.unmatchedTimeOuts += 1
        else:
            stats.notimeOut += 1

        stats.totalGED += stats.lastGED
        
        if out_dir:
            log_path = os.path.join(out_dir, "ged_results.txt")
            with open(log_path, "w") as f:
                for line in ged_log:
                    f.write(line + "\n")
                f.write("-" * 40 + "\n")
                f.write(f"TOTAL ZHK-COMBINED GED: {stats.totalGED}\n")

        return stats

def main():     
    parser = argparse.ArgumentParser(description="Match C AST/Dependency graphs and compute GED.")
    parser.add_argument("src", help="Path to the source C file (e.g., ex1.txt)")
    parser.add_argument("decomp", help="Path to the decompiled C file (e.g., ex2.txt)")
    parser.add_argument("-o", "--out-dir", dest="out_dir", default=None, 
                        help="Output directory to save the plotted ZHK subgraphs and GED results log.")
    args = parser.parse_args()

    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()
    
    try:
        with open(args.src) as f:
            cCode = f.read()
        
        with open(args.decomp) as f:
            cCode2 = f.read()
        
        sm = SimilarityMatching(cCode, cCode2)
        __import__('pprint').pprint(
            sm.computeGraphEditDistance(timeout=450, out_dir=args.out_dir).to_dict()
        )
        
    except FileNotFoundError as e:
        print(f"Error: Could not find file. {e}")
    except NameError:
        print("Error: DependencyGraphfromCFunction not imported/defined.")

if __name__ == "__main__":
    main()
