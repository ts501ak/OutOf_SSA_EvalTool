import networkx as nx
from typing import DefaultDict, Dict, Set, Tuple, Self
from dependencyGraphfromC import DependencyGraphfromCFunction, CompareGraphs, mergeDicts
from collections import defaultdict
import matplotlib.pyplot as plt
from time import time_ns

class StatisticsClass:
    def __init__(self):
        self.runs = 0
        self.anzZhk1 = []
        self.anzZhk2 = []
        self.matchedZhk = 0
        self.halfmatchedZhk = 0
        self.notmatchedZhk = 0
        self.totalGED = 0
        self.savePoints = []
        self.totalNodes1 = []
        self.totalNodes2 = []
        self.sizeZhk = []
        self.timeOuts = 0
        self.notimeOut = 0
        self.timeNeeded = []
        self.lastGED = 0

    def fuseStatObj(self,statobj :Self):
        self.runs += statobj.runs
        self.anzZhk1.extend(statobj.anzZhk1)
        self.anzZhk1.extend(statobj.anzZhk2)
        self.matchedZhk += statobj.matchedZhk
        self.halfmatchedZhk += statobj.halfmatchedZhk
        self.notmatchedZhk += statobj.notmatchedZhk
        self.totalGED += statobj.totalGED
        self.savePoints.extend(statobj.savePoints)
        self.totalNodes1.extend(statobj.totalNodes1)
        self.totalNodes2.extend(statobj.totalNodes2)
        self.sizeZhk.extend(statobj.sizeZhk)
        self.timeOuts += statobj.timeOuts
        self.notimeOut += statobj.notimeOut
        self.timeNeeded.extend(statobj.timeNeeded)

    def getGED(self):
        return self.lastGED

    def printResults(self):
        print('%-24s%-20i' % ("#compared code samples",self.runs))
        print('%-24s%-20i' % ("total GED",self.totalGED))
        print('%-24s%-20f' % ("average source zhk",sum(self.anzZhk1)/len(self.anzZhk1)))
        print('%-24s%-20f' % ("average decomp zhk",sum(self.anzZhk2)/len(self.anzZhk2)))
        print('%-24s%-20i' % ("#matched zhk",self.matchedZhk + self.halfmatchedZhk))
        print('%-24s%-20i' % ("#not matched zhk",self.notmatchedZhk))
        print('%-24s%-20f' % ("average save Points",sum(self.savePoints)/len(self.savePoints)))
        print('%-24s%-20f' % ("average zhk size",sum(self.sizeZhk)/len(self.sizeZhk)))
        print('%-24s%-20i' % ("GED no Timeout",self.notimeOut))
        print('%-24s%-20i' % ("GED Timeouts",self.timeOuts))
        print('%-24s%-20s' % ("average GED Time",str(round((sum(self.timeNeeded)/(self.timeOuts + self.notimeOut)),2))+"s"))


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
        safe_matches, unsafe_matches, constants = compObj.getSameVars()
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

    def computeGraphEditDistance(self,timeout = 20,stats : StatisticsClass = StatisticsClass()):
        stats.runs += 1
        stats.lastGED = 0
        stats.totalNodes1.append(len(self._src_graph.nodes(data=False)))
        stats.totalNodes2.append(len(self._decomp_graph.nodes(data=False)))

        subgraphDict = DefaultDict(lambda : [[],[]])
        
        equivDict = {a : b for a,(b,c) in self.mapping.items()}
        equivDict = mergeDicts(equivDict,self.constants)
        equivDict = DefaultDict(lambda : None,equivDict)
        equivDict["return"] = "return"

        def areSameNode(n1 : str, n2 : str):
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

        #showGraph(undirSrcGraph)
        #showGraph(g1zhks)
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
        

        #showGraph(undirdecompGraph)
        #showGraph(g2zhks)
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
        
        stats.sizeZhk.append(sum(sizeConComp)/len(sizeConComp))

        remainsrc = set()
        remaindecomp = set()

        for zz in subgraphDict.keys():
            if (len(subgraphDict[zz][0]) == 1) and (len(subgraphDict[zz][1]) == 1):
                stats.matchedZhk += 2
                srcGraph = subgraphDict[zz][0][0].union(gscrNodes)
                decompGraph = subgraphDict[zz][1][0].union(gdecompNodes)
                start = time_ns()
                stats.lastGED += nx.graph_edit_distance(undirSrcGraph.subgraph(srcGraph),undirdecompGraph.subgraph(decompGraph),node_match=areSameNode,timeout=timeout)
                end = time_ns()
                stats.timeNeeded.append((end-start)/1000000000)
                if int((end-start)/1000000000) > (timeout):
                    stats.timeOuts += 1
                else:
                    stats.notimeOut += 1
            elif (len(subgraphDict[zz][0])) == (len(subgraphDict[zz][1])):
                srcSet = set()
                decompSet = set()
                for aa in subgraphDict[zz][0]:
                    srcSet.update(aa)
                    stats.halfmatchedZhk += 1
                srcSet.update(gscrNodes)
                for bb in subgraphDict[zz][1]:
                    decompSet.update(bb)
                    stats.halfmatchedZhk += 1
                decompSet.update(gdecompNodes)
                start = time_ns()
                stats.lastGED += nx.graph_edit_distance(undirSrcGraph.subgraph(srcSet),undirdecompGraph.subgraph(decompSet),node_match=areSameNode,timeout=timeout)
                end = time_ns()
                stats.timeNeeded.append((end-start)/1000000000)
                if int((end-start)/1000000000) > (timeout):
                    stats.timeOuts += 1
                else:
                    stats.notimeOut += 1
            else:
                for bb in subgraphDict[zz][0]:
                    remainsrc.update(bb)
                    stats.notmatchedZhk += 1
                for cc in subgraphDict[zz][1]:
                    remaindecomp.update(cc)
                    stats.notmatchedZhk += 1
        
        remainsrc.update(gscrNodes)
        remaindecomp.update(gdecompNodes)

        start = time_ns()
        stats.lastGED += nx.graph_edit_distance(undirSrcGraph.subgraph(remainsrc),undirdecompGraph.subgraph(remaindecomp),node_match=areSameNode,timeout=timeout)
        end = time_ns()
        stats.timeNeeded.append((end-start)/1000000000)
        if int((end-start)/1000000000) > (timeout):
            stats.timeOuts += 1
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
    try:
        with open("/home/jannis/Desktop/ex1.txt") as f:
            cCode = f.read()
        dgrc = DependencyGraphfromCFunction()
        dg = dgrc.getDependencyGraph(cCode)
        
        with open("/home/jannis/Desktop/ex2.txt") as f:
            cCode2 = f.read()
        dgrc2 = DependencyGraphfromCFunction()
        dgg = dgrc2.getDependencyGraph(cCode2)
        
        sm = SimilarityMatching(dg, cCode, dgg, cCode2)
        #sm.print_results()
        sm.computeGraphEditDistance(20).printResults()
    except FileNotFoundError:
        print("Error: Test files not found. Please check file paths in main().")
    except NameError:
        print("Error: DependencyGraphfromCFunction not imported/defined.")

if __name__ == "__main__":
    main()
