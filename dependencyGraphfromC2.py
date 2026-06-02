from copy import deepcopy
from typing import ByteString, DefaultDict
import networkx as nx
import re
import matplotlib.pyplot as plt
import processVariable
import tree_sitter as ts
import tree_sitter_c
import sys

class Result:
    def __init__(self):
        self.dependencyGraph = nx.DiGraph()
        self.arguments = []
        self.callDict = DefaultDict(lambda:[])

class DependencyGraphfromCFunction:
    def __init__(self):

        self._parser = ts.Parser(ts.Language(tree_sitter_c.language()))
        self.__Constant = re.compile(r"^( |\t)*(?P<num>((?P<Hex>(\+|-)?(0[x|X]([0-9]|[ABCDEF]|[abcdef])+(\.([0-9]|[ABCDEF]|[abcdef])*)?((P|p)(\+|-)?([0-9]|[ABCDEF]|[abcdef])+)?))|(?P<Dec>((-|\+)?[0-9_]*\.[0-9]+(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))|(?P<Dec2>((-|\+)?[0-9_]+\.[0-9]*(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))|(?P<Bin>(0[B|b][10]+))|(?P<NULLL>(NULL))|(?P<Oct>(0[0-7]*))|(?P<trueFalse>true|false|True|False|TRUE|FALSE)|(?P<Dec3>((-|\+)?[1-9][0-9_]*(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))))")

    def getResult(self,cFunc : str) -> Result:
        """takes the code of a single function as ascii and builds the dependency graph for it"""

        self.__func = cFunc.encode("utf-8")
        self.__counter = 0
        self.__result = Result()
        self.parseTree()
        self.__result.dependencyGraph.remove_edges_from(list(nx.selfloop_edges(self.__result.dependencyGraph)))
        return self.__result
    
    def getDependencyGraph(self,cFunc : str):
        return self.getResult(cFunc).dependencyGraph


    def get_node_text(self,node : ts.Node):
        return self.__func[node.start_byte:node.end_byte].decode("utf-8")
    
    def __getVarName(self):
        nodeName = f"$help${self.__counter}$"
        self.__counter += 1
        return nodeName

    def __extract_parameter_names(self, parameter_list_node: ts.Node) -> list:
        """Extract only the parameter names (declarators), not type identifiers.
        
        E.g. for 'stbi__uint16 *orig, int w, int h, int channels':
        Returns: ['orig', 'w', 'h', 'channels']
        (not including 'stbi__uint16' which is a type name)
        """
        param_names = []
        
        # Iterate through direct children to find parameter_declaration nodes
        for child in parameter_list_node.children:
            if child.type == "parameter_declaration":
                # Find the declarator field in this parameter
                declarator = child.child_by_field_name("declarator")
                if declarator:
                    # The declarator can be: simple identifier, pointer_declarator, array_declarator, etc.
                    # We need to find the identifier within it
                    identifiers = self.find_nodes_by_type(declarator, "identifier")
                    if identifiers:
                        # Take the last identifier (the actual parameter name, not part of the type)
                        param_names.append(self.get_node_text(identifiers[-1]))
        
        return param_names

    def parseTree(self):
        tree = self._parser.parse(self.__func)
        tree : ts.Tree
        curs = self.getFuncDef(tree)
        functionNode = curs.node
        #Step 1 - get function arguemtns
        params_list = self.find_nodes_by_type(curs.node,"parameter_list")
        if params_list:
            self.__result.arguments = self.__extract_parameter_names(params_list[0])
        else:
            self.__result.arguments = []
        #Step 2 - get all function Calls
        calls = self.find_nodes_by_type(functionNode,"call_expression")
        for call in calls:
            argList = ""
            call : ts.Node
            args = call.child_by_field_name("arguments").children
            funcName = self.get_node_text(call.child_by_field_name("function"))
            vars = []
            for child in args:
                res = self.find_nodes_by_types(child,["number_literal","identifier","string_content","character"])
                aList = ""
                for x in res:
                    x : ts.Node
                    match x.type:
                        case "number_literal":
                            aList = aList +  str(self.__constantToDec(self.get_node_text(x)))
                        case "identifier":
                            aList = aList + str("var")
                            vars.append(self.get_node_text(x))
                        case "string_content" | "character":
                            aList = aList + str(hash(self.get_node_text(x)))
                        case _ as weird:
                            raise Exception(f"Encountered unexpected type: {weird}")
                argList = argList + aList
                
            self.__result.callDict[funcName].append((argList,vars))
        #Step 3 - get Assignments
        assignmentsPt1 = self.find_nodes_by_type(functionNode,"assignment_expression")
        assignmentsPt1.extend(self.find_nodes_by_type(functionNode,"declaration"))
        for assi in assignmentsPt1:
            assi : ts.Node
            if assi.type == "assignment_expression":
                left = self.get_node_text(self.find_nodes_by_type(assi.child_by_field_name("left"),"identifier")[0])
                right = assi.child_by_field_name("right")
            else: #type = declaration
                if assi.child_by_field_name("declarator").type == "init_declarator":
                    right = assi.child_by_field_name("declarator").child_by_field_name("value")
                    left = assi.child_by_field_name("declarator").child_by_field_name("declarator")
                    left = self.find_nodes_by_type(left,"identifier")[0]
                    left = self.get_node_text(left)
                else:
                    right = None
            
            if right:
                self.__result.dependencyGraph.add_node(left,name=left)
                assignees = self.recursivelyGetInvolved(right)
                for x in assignees:
                    self.__result.dependencyGraph.add_node(helperName:= self.__getVarName(),name=helperName)
                    self.__result.dependencyGraph.add_edge(helperName,left,type="assig")
                    for y in x:
                        self.__result.dependencyGraph.add_node(y[0],name=y[0],type=y[1])
                        self.__result.dependencyGraph.add_edge(y[0],helperName,type=y[1])

        #Step 4 - return statements
        returns = self.find_nodes_by_type(functionNode,"return_statement")
        if len(returns) != 0:
            self.__result.dependencyGraph.add_node("return",name="return")
        for ret in returns:
            ret : ts.Node
            retVars = self.recursivelyGetInvolved(ret)
            for x in retVars:
                self.__result.dependencyGraph.add_node(helperName:= self.__getVarName(),name=helperName)
                self.__result.dependencyGraph.add_edge(helperName,"return",type="return")
                for y in x:
                    self.__result.dependencyGraph.add_node(y[0],name=y[0],type=y[1])
                    self.__result.dependencyGraph.add_edge(y[0],helperName,type=y[1])


    def recursivelyGetInvolved(self,inp: ts.Node):
        comp = [[]]
        for node in self.dfs(inp):
            match node.type:
                case "number_literal":
                    for x in comp:
                        x : list
                        x.append((self.__constantToDec(self.get_node_text(node)),"const"))
                case "identifier":
                    for x in comp:
                        x : list
                        x.append((self.get_node_text(node),"var"))
                case "string_content" | "character":
                    for x in comp:
                        x : list
                        x.append(("§§STR§§" + str(hash(self.get_node_text(node)))+ "§","const"))
                case "call_expression":
                    funcHandle = self.handleCalls(node)
                    for x in comp:
                        x : list
                        x.append((funcHandle,"func"))
                case "conditional_expression":
                    if len(comp) == 1: #We accept 1 ternary but no more
                        con = self.recursivelyGetInvolved(node.child_by_field_name("consequence"))
                        alt = self.recursivelyGetInvolved(node.child_by_field_name("alternative"))
                        if (len(con) != 1) or (len(alt) != 1):
                            raise Exception("We currently can't build a dependency tree for this Code, bc there are nested tenary statements!")
                        save = deepcopy(comp[0])
                        comp[0].extend(con[0])
                        save.extend(alt[0])
                        comp.append(save)
                case "subscript_expression":
                    subscriptHandle = self. handleSubscripts(node)
                    if subscriptHandle:
                        for x in comp:
                            x : list
                            x.append((subscriptHandle,"arr"))
                case "true" | "false":
                    for x in comp:
                        x : list
                        x.append((self.__constantToDec(self.get_node_text(node)),"const"))
        return comp


    def handleCalls(self,node : ts.Node):
        args = [] 
        for funcarg in node.children_by_field_name("arguments"):
            res = self.recursivelyGetInvolved(funcarg)
            if len(res) != 1:
                raise Exception("There's a tenary Expression inside a function call")
            args.extend(res)

        nname = self.get_node_text(node.child_by_field_name("function"))
        nname = f"{nname}${self.__counter}"
        self.__counter += 1
        self.__result.dependencyGraph.add_node(nname,name=nname)
        for x in range(len(args)):
            for y in args[x]:
                self.__result.dependencyGraph.add_node(y[0],name=y[0],type=y[1])
                self.__result.dependencyGraph.add_edge(y[0],nname,name=f"funcArg{x}",type=y[1])
        
        return nname
    
    def handleSubscripts(self,node : ts.Node):
        #Node: double subscripts are being ingnored
        index = node.child_by_field_name("index")
        index : ts.Node
        res = self.recursivelyGetInvolved(index)
        if len(res) != 1:
            raise Exception("There's a tenary Expression inside a subscript expression!")

        nname = node.child_by_field_name("argument")
        while nname.type == "subscript_expression":
            nname : ts.Node
            nname = nname.child_by_field_name("argument")
        if nname.type != "identifier":
            return None
        nname = f"{self.get_node_text(nname)}${self.__counter}"
        self.__counter += 1
        self.__result.dependencyGraph.add_node(nname,name=nname)
        for y in res[0]:
            self.__result.dependencyGraph.add_node(y[0],name=y[0],type=y[1])
            self.__result.dependencyGraph.add_edge(y[0],nname,name=f"subscript",type=y[1])
        
        return nname

    def dfs(self,root):

        stack = [root]

        while stack:
            node = stack.pop()
            node : ts.Node

            if node.type in ["subscript_expression","call_expression","conditional_expression","number_literal","identifier","string_content","character"]:
                yield node
            if not (node.type in ["conditional_expression","call_expression","subscript_expression","ERROR"]):
                stack.extend(reversed(node.children))

    def find_nodes_by_type(self,node, target_type):
        result = []

        if node: 
            if node.type == target_type:
                result.append(node)

            for child in node.children:
                result.extend(self.find_nodes_by_type(child, target_type))

        return result

    def find_nodes_by_types(self,node, target_types : list):
        result = []
        if node:
            if node.type in target_types:
                result.append(node)

            for child in node.children:
                result.extend(self.find_nodes_by_types(child, target_types))

        return result

    def getFuncDef(self,tree : ts.Tree):
        cursor = tree.root_node.walk()
        cursor.goto_first_child()
        if cursor.node.type == "function_definition":
            return cursor
        while cursor.node.type != "function_definition":
            if not cursor.goto_next_sibling():
                raise Exception("Found no function definition")
        return cursor
            
    def __constantToDec(self,inp : str):
        matO = self.__Constant.search(inp)
        if matO:
            if matO.group("Dec"):
                return str(float(matO.group("num")))
            elif matO.group("Dec2"):
                return str(float(matO.group("num")))
            elif matO.group("Dec3"):
                return str(float(matO.group("num")))
            elif hex := matO.group("Hex"):
                return str(float.fromhex(hex))
            elif bin := matO.group("Bin"):
                bin = bin[2:]
                return str(float(int(bin,base=2)))
            elif oct := matO.group("Oct"):
                if oct == "0":
                    return "0"
                oct = oct[1:]
                return str(float(int(oct,base=8)))
            elif nu := matO.group("NULLL"):
                return "0.0"
            elif tf:= matO.group("trueFalse"):
                return f"{tf.upper()}(const)"
            return str(float(matO.group("num")))
        
        raise Exception(f"Couldn't convert {inp} to Dec!")

def mergeDicts(d1 :dict, d2 : dict):
    res = {}
    for k in set(list(d1.keys()) + list(d2.keys())):
        values = []
        if k in d1.keys():
            values.append(d1[k])
        if k in d2.keys():
            values.append(d2[k])
        values = list(set(values))
        #if len(values) > 1:
        #    #raise InfoException("Found 2 contradicting certain matches! We're taking the first one!")
        #    pass
        res[k] = values[0]
    return res   


class CompareGraphs:
    def __init__(self,c1 : str,c2:str,depGraph1 : nx.DiGraph = None,depGraph2 : nx.DiGraph = None, buildInNames : list[tuple[2]] = []):
        self.c1 = c1
        self.c2 = c2
        self.c1Result = processVariable._DependencyGraphObj.getResult(c1)
        self.c2Result = processVariable._DependencyGraphObj.getResult(c2)
        self.c1Result : Result
        self.c2Result : Result
        self.equivDictSure = DefaultDict(lambda:set())
        self.equivDictUsure = DefaultDict(lambda:set())
            
    def getSameConstants(self,c1 : nx.DiGraph, c2 : nx.DiGraph): 
        equivDict = {}
        vars1 = [x for x,y in nx.get_node_attributes(c1,"type","None").items() if y == "const"]
        vars2 = [x for x,y in nx.get_node_attributes(c2,"type","None").items() if y == "const"]

        for var in vars1:
            if (vars1.count(var) == 1) and (var in vars2) and (vars2.count(var) == 1):
                equivDict[var] = var

        return equivDict

    def getSameVars(self):
        
        self.matchFunctionsArgs()
        e = self.getSameConstants(self.c1Result.dependencyGraph,self.c2Result.dependencyGraph)
        
        #Sets in Listen umwandeln

        return self.equivDictSure, self.equivDictUsure, e
       
    def matchFunctionsArgs(self):
        self.equivDictSure = DefaultDict(lambda:"")
        self.equivDictUsure = DefaultDict(lambda:"")

        if len(self.c1Result.arguments) == len(self.c2Result.arguments):
            for x in range(len(self.c1Result.arguments)):
                self.equivDictSure[self.c1Result.arguments[x]] = self.c2Result.arguments[x]
                self.equivDictSure[self.c2Result.arguments[x]] = self.c1Result.arguments[x]
        else:
            raise Exception(f"The two functions don't habe the same number of parameters.{self.c1Result.arguments}, {self.c2Result.arguments}")
        


        for i in range(2):
            rmKeysc1 = []
            rmKeysc2 = []
            for key in self.c1Result.callDict.keys():
                for c1Index in range(len(self.c1Result.callDict[key])):
                    c2Strs = [x[0] for x in self.c2Result.callDict[key]]
                    if (self.c1Result.callDict[key][c1Index][0] in c2Strs) and (c2Strs.count(self.c1Result.callDict[key][c1Index][0]) == 1):
                        for i in range(len(self.c2Result.callDict[key])):
                            if self.c2Result.callDict[key][i][0] == self.c1Result.callDict[key][c1Index][0]:
                                c2Index = i
                                if len(self.c1Result.callDict[key][c1Index][1]) == len(self.c2Result.callDict[key][c2Index][1]):
                                    for varI in range(len(self.c1Result.callDict[key][c1Index][1])):
                                        if self.equivDictSure[self.c1Result.callDict[key][c1Index][1][varI]] == "":
                                            self.equivDictSure[self.c1Result.callDict[key][c1Index][1][varI]] = self.c2Result.callDict[key][c2Index][1][varI]
                                            self.equivDictSure[self.c2Result.callDict[key][c2Index][1][varI]] = self.c1Result.callDict[key][c1Index][1][varI]
                                rmKeysc1.append((key,c1Index))
                                rmKeysc2.append((key,c2Index))
                            
                            elif (len(self.c1Result.callDict[key]) == 1) and (len(self.c2Result.callDict[key]) == 1):
                                if len(self.c1Result.callDict[key][0][1]) == len(self.c2Result.callDict[key][0][1]):
                                    for varI in range(len(self.c1Result.callDict[key])):
                                        self.equivDictUsure[self.c1Result.callDict[key][1][varI]] = self.c2Result.callDict[key][1][varI]
                                        self.equivDictUsure[self.c2Result.callDict[key][1][varI]] = self.c1Result.callDict[key][1][varI]

            for dictKey, Index in sorted(rmKeysc1,key=lambda x : x[1],reverse=True):
                self.c1Result.callDict[dictKey].pop(Index)

            for dictKey, Index in sorted(rmKeysc2,key= lambda x : x[1],reverse=True):
                self.c2Result.callDict[dictKey].pop(Index)


def main():
    processVariable._DependencyGraphObj = DependencyGraphfromCFunction()
    with open("/home/jannis/Desktop/ex1.txt") as f:
        c1 = f.read()
        #print(c1)
    #with open("/home/jannis/Desktop/ex2.txt") as f:
    #    c2 = f.read()
    #    print(c2)

    cc1 = DependencyGraphfromCFunction()
    dg = cc1.getDependencyGraph(c1)
    for edge in dg.edges():
        pass
        #print(edge)

    compObj = CompareGraphs(c1,c1)
    a,b,c = compObj.getSameVars()
    print(a.items())
    print(b.items())
    print(c.items())

if __name__ == "__main__":
    main()
