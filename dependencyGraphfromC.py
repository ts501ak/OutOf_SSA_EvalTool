import networkx as nx
import re
import iplotx as ix
import matplotlib.pyplot as pp


class DependencyGraphfromCFunction:
    def __init__(self):
        """As this class will compute a few thousand dependency graphs we precompile all our regexes in advance, so we don't have to do it every single run"""

        self.__regs = []
        self.__regs.append(re.compile(r"//.*")) #No Comments
        self.__regs.append(re.compile(r"/\*.*?\*/",re.DOTALL)) #No Multiline Comments
        self.__regs.append(re.compile(r'"(\\.|[^"\\])*"')) #No Strings --> To be removed
        self.__regs.append(re.compile(r"'(\\.|[^'\\])*'")) #No Strings --> To be removed
        self.__stringIdent = re.compile(r"\$[a-fA-F0-9]{64}\$")
        self.__doubleNL = re.compile(r"\n\n+")
        self.__doubleWS = re.compile(r"  +")
        self.__col = re.compile(r" *, *")
        self.__nbo = re.compile(r" *\( *")
        self.__nbc = re.compile(r" *\) *")
        self.__sbo = re.compile(r" *\[ *")
        self.__sbc = re.compile(r" *\] *")
        self.__cbo = re.compile(r" *\{ *")
        self.__cbc = re.compile(r" *\} *")
        self.__sc = re.compile(r" *; *")
        self.__tab = re.compile(r"\t+")
        self.__wsBeginning = re.compile(r"\n +")
        self.__wsEquals = re.compile(r" *= *")
        self.__assignOperators = ["=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="]
        self.__operators = ["+","-", "*", "/", "%", "==", "!=", "[^-]>", "<", ">=", "<=", "&&", "||", "&", "|", "^", "<<", ">>"]
        #self.__delims = ["+","-", "*", "/", "%", "==", "!=", ">", "<", ">=", "<=", "&&", "||", "&", "|", "^", "<<", ">>",")","(",",","[","]"]
        self.__types = re.compile(r"\b(char|int|float|double|signed|short|long|bool|_Bool|void|uint[0-9]*_t|int[0-9]*_t|size_t)\b")
        self.__variable = re.compile(r"[A-Za-z_]\w*")
        self.__variableAssign = re.compile(r"(?P<first>[A-Za-z_]\w*)((\.|->|\[[^\]]+\]\.|\[[^\]]+\]->|\[.*\])*[A-Za-z_]\w*)*(\[[^\]]+\])* *(=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)")
        self.__funcEnd = re.compile(r"[A-Za-z_]\w*$")
        self.__funcNorm = re.compile(r"[A-Za-z_]\w*\(")
        self.__oneequals = re.compile("[^=]=[^=]")
        self.__Constant = re.compile(r"^ *(?P<num>(0x([0-9]|[ABCDEF]|[abcdef])+|(\+|-)?[0-9]+\.[0-9]+((E|e)?(\+|-)?[0-9]+)?|0b[10]+|(\+|-)?[0-9]+))")
        self.__pat = r"((?<!(E|e))\+(?!(>|\+|-))|(?<!(E|e))\-(?!(>|\+|-))|\*|/|%|==|!=|>=|<=|(?<!-)>|<|\&\&|\|\||\&|\||\^|<<|>>|\)|\(|,|\[|\])"
        self.__specialAccess = re.compile(r" *(?P<first>[A-Za-z_]\w*) *((\.|->) *[A-Za-z_]\w*)*")
        self.__numberbegin = re.compile(r"^ *[0-9]")
        self.__ternaryAssig = re.compile(r"\?(?P<ifTrue>[^:\n]*):(?P<ifFalse>[^;\n]*)")
        self.__dotVar = re.compile(r"(^ *\. *[A-Za-z_]\w*|^ *-> *[A-Za-z_]\w*)")
        self.__counter = 0
        self.__newLine = re.compile(" *\n *")
        


    def getDependencyGraph(self,cFunc : str) -> nx.DiGraph:
        """takes the code of a single function as ascii and builds the dependency graph for it"""


        self.__func = cFunc
        self.__prepareFunc()
        self.__counter = 0
        return self.__constructDepGraph()

    def __prepareFunc(self):
        """prepares the code for processing the dependency graph e.g. deletes comments, removes unnecessary stylistic nuances etc., so that we don't have to take
            it into consideration in every single regex in the main construction method"""
        
        for reg in self.__regs:
            self.__func = reg.sub("",self.__func)
        self.__func = self.__doubleNL.sub("\n",self.__func)
        self.__func = self.__tab.sub(r" ",self.__func)
        self.__func = self.__doubleWS.sub(" ",self.__func)
        self.__func = self.__col.sub(",",self.__func)
        self.__func = self.__nbo.sub(r"(",self.__func)
        self.__func = self.__nbc.sub(r")",self.__func)
        self.__func = self.__sbo.sub(r"[",self.__func)
        self.__func = self.__sbc.sub(r"]",self.__func)
        self.__func = self.__cbo.sub(r"{",self.__func)
        self.__func = self.__cbc.sub(r"}",self.__func)
        self.__func = self.__sc.sub(r";",self.__func)
        self.__func = self.__wsBeginning.sub(r"\n",self.__func)
        self.__func = self.__wsEquals.sub(r"=",self.__func)
        self.__func = self.__newLine.sub(r" ",self.__func)


    def __constructDepGraph(self) -> nx.DiGraph:
        """computes the dependency graph of a given preprocessed function
            Tenary assignments are ignored"""
        
        self.depGraph = nx.DiGraph()
        
        #for line in self.__func.split("\n"):
        for instr in [x for x in self.__func.split(";") if x != '']:
            if any(aop in instr for aop in self.__assignOperators) and (not "return" in instr) and (self.__oneequals.search(instr)): #No == as Assignmet Operator
                if assi := self.__variableAssign.search(instr):
                    lhs = assi.group("first")
                    #if (ind := assi.group(0).find("[")) != -1: #No more detection of Array access, bc this may get lost after OoSSA or is added afterwards
                    #    self.__getVariablesOfString2(instr[ind+1:len(assi.group(0))-1],lhs)
                    start = instr.find(assi.group(0))
                    instr = instr[start + len(assi.group(0)):]
                    if ta := self.__ternaryAssig.search(instr):
                        nodeName = self.__getVarName()
                        self.depGraph.add_edge(nodeName,lhs)
                        self.__getVariablesOfString(ta.group("ifTrue"),nodeName)
                        nodeName = self.__getVarName()
                        self.depGraph.add_edge(nodeName,lhs)
                        self.__getVariablesOfString(ta.group("ifFalse"),nodeName)
                    else:
                        nodeName = self.__getVarName()
                        self.depGraph.add_edge(nodeName,lhs)
                        self.__getVariablesOfString(instr,nodeName)
            
            elif (ind := instr.find("return")) != -1:
                if ta := self.__ternaryAssig.search(instr[ind + 6:]):
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return")
                    self.__getVariablesOfString(ta.group("ifTrue"),nodeName)
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return")
                    self.__getVariablesOfString(ta.group("ifFalse"),nodeName)
                else:
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return")
                    self.__getVariablesOfString(instr[ind + 6:],nodeName)


        self.depGraph.remove_edges_from(list(nx.selfloop_edges(self.depGraph)))
        return self.depGraph
    
    def __getVarName(self):
        nodeName = f"$help{self.__counter}$"
        self.__counter += 1
        return nodeName

    def __getVariablesOfString(self,strIn : str,lhs:str):
        instr = re.split(self.__pat,strIn)
        instr = [i for i in instr if (i != '') and (i != None)]
        instr.append(";")
        count = -1
        print(instr)
        while (count) < (len(instr) - 1):
            tok = instr[count]
            if self.__types.search(tok):
                pass
            elif (tok in self.__operators) or (tok == ","):
                pass
            elif (const := self.__Constant.search(tok)) != None:
                self.depGraph.add_edge(const.group("num"),lhs,type="const")
                
            elif (tok == "(") or (tok == ")"):
                pass
            elif string := self.__stringIdent.search(tok):
                self.depGraph.add_edge(string.group(0),lhs)
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "("):
                funcName = f"{f.group(0)}${self.__counter}"
                self.__counter += 1
                self.depGraph.add_edge(funcName,lhs,type="func")
                brcount = 0
                for i in range(count+1,len(instr)-1):
                    if instr[i] == "(":
                        brcount += 1
                    elif instr[i] == ")":
                        brcount -= 1
                    if brcount == 0:
                        brcount = i
                        break
                rest = "".join(instr[count+1:brcount+1])
                self.__getVariablesOfString(rest,funcName)
                count = brcount + 1    #This is why we use while(index < int) instead of for i in range(int)
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "["): #Array (but with Function Variables :) Sorry)
                funcName = f"{f.group(0)}${self.__counter}"
                self.__counter += 1
                self.depGraph.add_edge(funcName,lhs,type="array")
                brcount = 0
                for i in range(count+1,len(instr)-1):
                    if instr[i] == "[":
                        brcount += 1
                    elif instr[i] == "]":
                        brcount -= 1
                    if brcount == 0:
                        brcount = i
                        break
                rest = "".join(instr[count+1:brcount+1])
                self.__getVariablesOfString(rest,funcName)
                count = brcount + 1    #This is why we use while(index < int) instead of for i in range(int)
                
            elif (v := self.__specialAccess.search(tok)) and (not self.__numberbegin.search(tok)) and (not self.__Constant.search(tok)):
                self.depGraph.add_edge(v.group("first"),lhs,type="var")
            else:
                pass
            count += 1
        return
    
    """ def __getVariablesOfString2(self,strIn : str,lhs,rek = 0): #This Function got NO update
        bet = []
        instr = re.split(self.__pat,strIn)
        instr = [i for i in instr if i != '']
        instr.append(";")
        #bracketCount = 0
        for i in range(len(instr)-1):
            tok = instr[i]
            if self.__types.search(tok):
                continue
            elif (tok in self.__operators) or (tok == ","):
                continue
            elif self.__noConstant.search(tok) != None:
                continue
            elif (tok == "[") or (tok == "]"):
                continue
            elif (f := self.__funcEnd.search(tok)) and (instr[i+1] == "("):
                self.depGraph.add_edge(f.group(0),lhs,type="func") 
            elif (v := self.__specialAccess.search(tok)) and (not self.__dotVar.search(tok)) and (not self.__numberbegin.search(tok)) and (not self.__noConstant.search(tok)):
                self.depGraph.add_edge(v.group("first"),lhs,type="var")
            else:
                continue

        return
    """


    def areSimilar(self,g1 :nx.DiGraph, g2 : nx.DiGraph):
        pass

def main():
    with open("/home/jannis/Desktop/c-Code.txt") as f:
        cCode = f.read()
    dgrc = DependencyGraphfromCFunction()
    dg = dgrc.getDependencyGraph(cCode)
    for x in dg.edges():
        print(x)
    pso = nx.spring_layout(dg)
    nx.draw_networkx_nodes(dg,pso,dg.nodes())
    nx.draw_networkx_edges(dg,pso,dg.edges(),arrows=True,arrowstyle="->")
    nx.draw_networkx_labels(dg,pso)
    pp.show()


if __name__ == "__main__":
    main()
