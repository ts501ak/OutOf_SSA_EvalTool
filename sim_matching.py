from collections import defaultdict
import networkx as nx
from typing import Dict, Set
from dependencyGraphfromC import DependencyGraphfromCFunction, CompareGraphs, mergeDicts
import matplotlib.pyplot as plt
from time import time_ns
import processVariable

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
        """Merges another statistics object into this one."""
        self.runs += other.runs
        self.anzZhk1.extend(other.anzZhk1)
        self.anzZhk2.extend(other.anzZhk2)
        self.matchedZhk += other.matchedZhk
        self.halfmatchedZhk += other.halfmatchedZhk
        self.notmatchedZhk += other.notmatchedZhk
        self.totalGED += other.totalGED
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
        """Allows use of += operator: stats += new_stats"""
        return self.merge(other)

    def to_dict(self):
        def safe_avg(data): return sum(data) / len(data) if data else 0
        total_attempts = self.timeOuts + self.notimeOut
        
        return {
            "runs": self.runs,
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
        print('%-24s%-20i' % ("total GED", data["total_ged"]))
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
        
        self._src_graph = processVariable._DependencyGraphObj.getDependencyGraph(
                self._src_Code)
        self._decomp_graph = processVariable._DependencyGraphObj.getDependencyGraph(
                self._decomp_Code) 

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
        self.constants = constants

        for src_var, d_var in safe_matches.items():
            self.mapping[src_var] = (d_var, 1.0)
            self.src_unknowns.discard(src_var)
            self.decomp_unknowns.discard(d_var)

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

    def computeGraphEditDistance(self, timeout=20) -> StatisticsClass:
        stats = StatisticsClass()
        stats.runs += 1
        stats.lastGED = 0
        stats.totalNodes1.append(len(self._src_graph.nodes(data=False)))
        stats.totalNodes2.append(len(self._decomp_graph.nodes(data=False)))

        subgraphDict = defaultdict(lambda: [[], []])
        
        equivDict = {a: b for a, (b, _) in self.mapping.items()}
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

        undirSrcGraph = self._src_graph.to_undirected()
        undirdecompGraph = self._decomp_graph.to_undirected()

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

        for zz in subgraphDict.keys():
            if (len(subgraphDict[zz][0]) == 1) and (len(subgraphDict[zz][1]) == 1):
                stats.matchedZhk += 2
                srcGraph = subgraphDict[zz][0][0].union(gscrNodes)
                decompGraph = subgraphDict[zz][1][0].union(gdecompNodes)
                stats.sizeMatchedZHK.append(len(subgraphDict[zz][0][0]))
                stats.sizeMatchedZHK.append(len(subgraphDict[zz][1][0]))
                start = time_ns()
                ged = nx.graph_edit_distance(undirSrcGraph.subgraph(srcGraph), undirdecompGraph.subgraph(decompGraph), node_match=areSameNode, timeout=timeout)
                if ged is None:
                    raise Exception("nx.graph_edit_distance returned None! It's not clear how this result should be interpreted, therefore it's beeing discarded by this exception!")
                stats.lastGED += ged
                stats.matchedGED += ged
                end = time_ns()
                stats.timeNeeded.append((end-start)/1000000000)
                if (((end-start)/1000000000) + 1) > (timeout):
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
                start = time_ns()
                ged = nx.graph_edit_distance(undirSrcGraph.subgraph(srcSet), undirdecompGraph.subgraph(decompSet), node_match=areSameNode, timeout=timeout)
                if ged is None:
                    raise Exception("nx.graph_edit_distance returned None! It's not clear how this result should be interpreted, therefore it's beeing discarded by this exception!")
                stats.lastGED += ged
                stats.matchedGED += ged
                end = time_ns()
                stats.timeNeeded.append((end-start)/1000000000)
                if (((end-start)/1000000000) + 1) > (timeout):
                    stats.timeOuts += 1
                    stats.matchedTimeOuts += 1
                else:
                    stats.notimeOut += 1
            else:
                for bb in subgraphDict[zz][0]:
                    remainsrc.update(bb)
                    stats.sizeUnmatchedZHK.append(len(bb))
                    stats.notmatchedZhk += 1
                for cc in subgraphDict[zz][1]:
                    remaindecomp.update(cc)
                    stats.sizeUnmatchedZHK.append(len(cc))
                    stats.notmatchedZhk += 1
        
        remainsrc.update(gscrNodes)
        remaindecomp.update(gdecompNodes)

        start = time_ns()
        ged = nx.graph_edit_distance(undirSrcGraph.subgraph(remainsrc), undirdecompGraph.subgraph(remaindecomp), node_match=areSameNode, timeout=timeout)
        if ged is None:
            raise Exception("nx.graph_edit_distance returned None! It's not clear how this result should be interpreted, therefore it's beeing discarded by this exception!")
        stats.lastGED += ged
        stats.unmatchedGED += ged
        end = time_ns()
        stats.timeNeeded.append((end-start)/1000000000)
        if (((end-start)/1000000000) + 1) > (timeout):
            stats.timeOuts += 1
            stats.unmatchedTimeOuts += 1
        else:
            stats.notimeOut += 1

        stats.totalGED += stats.lastGED
        return stats

def showGraph(g : nx.DiGraph):
    pos = nx.kamada_kawai_layout(g)
    plt.figure()
    nx.draw(g,pos,with_labels=True,edge_color="black",node_color="orange",arrowstyle="->",node_size=2000,width=4,font_size=18)
    plt.show()

def main():     
    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()
    try:
        with open("/home/jannis/Desktop/ex1.txt") as f:
            cCode = f.read()
        
        with open("/home/jannis/Desktop/ex2.txt") as f:
            cCode2 = f.read()
        
        sm = SimilarityMatching(cCode, cCode2)
        sm.computeGraphEditDistance(20).printResults()
    except FileNotFoundError:
        print("Error: Test files not found. Please check file paths in main().")
    except NameError:
        print("Error: DependencyGraphfromCFunction not imported/defined.")

if __name__ == "__main__":
    main()
