import networkx as nx
import re
import iplotx as ix
import matplotlib.pyplot as pp


class DependencyGraphfromCFunction:
    def __init__(self):
        """As this class will compute a few thousand dependency graphs we precompile all our regexes in advance, so we don't have to do it every single run"""

        self.__regs = []
        self.__regs.append(re.compile(r'"(\\.|[^"\\])*"')) #No Strings
        self.__regs.append(re.compile(r"'(\\.|[^'\\])*'")) #No Strings
        self.__regs.append(re.compile(r"//.*")) #No Comments
        self.__regs.append(re.compile(r"/\*.*?\*/",re.DOTALL)) #No Multiline Comments
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
        self.__noConstant = re.compile(r"^ *0x.*")
        self.__pat = r"(\+|\-(?!>)|\*|/|%|==|!=|(?<!-)>|<|>=|<=|\&\&|\|\||\&|\||\^|<<|>>|\)|\(|,|\[|\])"
        self.__specialAccess = re.compile(r" *(?P<first>[A-Za-z_]\w*) *((\.|->) *[A-Za-z_]\w*)*")
        self.__numberbegin = re.compile(r"^ *[0-9]")
        self.__ternaryAssig = re.compile(r"\?(?P<ifTrue>[^:\n]*):(?P<ifFalse>[^;\n]*)")
        self.__dotVar = re.compile(r"(^ *\. *[A-Za-z_]\w*|^ *-> *[A-Za-z_]\w*)")


    def getDependencyGraph(self,cFunc : str) -> nx.Graph:
        """takes the code of a single function as ascii and builds the dependency graph for it"""


        self.__func = cFunc
        self.__prepareFunc()
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


    def __constructDepGraph(self) -> nx.Graph:
        """computes the dependency graph of a given preprocessed function
            Tenary assignments are ignored"""
        
        self.depGraph = nx.Graph()
        
        for line in self.__func.split("\n"):
            for instr in [x for x in line.split(";") if x != '']:
                if any(aop in instr for aop in self.__assignOperators) and (not "return" in instr) and (self.__oneequals.search(instr)): #No == as Assignmet Operator
                    if assi := self.__variableAssign.search(instr):
                        lhs = assi.group("first")
                        if (ind := assi.group(0).find("[")) != -1:
                            self.__getVariablesOfString2(instr[ind+1:len(assi.group(0))-1],lhs)
                        start = instr.find(assi.group(0))
                        instr = instr[start + len(assi.group(0)):]
                        if ta := self.__ternaryAssig.search(instr):
                            self.__getVariablesOfString(ta.group("ifTrue"),lhs,False)
                            self.__getVariablesOfString(ta.group("ifFalse"),lhs,False)
                        else:
                            self.__getVariablesOfString(instr,lhs,False)
                
                elif (ind := instr.find("return")) != -1:
                    if ta := self.__ternaryAssig.search(instr[ind + 6:]):
                            self.__getVariablesOfString(ta.group("ifTrue"),"return",True)
                            self.__getVariablesOfString(ta.group("ifFalse"),"return",True)
                    else:
                        self.__getVariablesOfString(instr[ind + 6:],"return",True)


        self.depGraph.remove_edges_from(list(nx.selfloop_edges(self.depGraph)))
        return self.depGraph
    
    def __getVariablesOfString(self,strIn : str,lhs,ret:bool = False):
        instr = re.split(self.__pat,strIn)
        instr = [i for i in instr if i != '']
        instr.append(";")
        for i in range(len(instr)-1):
            tok = instr[i]
            if self.__types.search(tok):
                continue
            elif (tok in self.__operators) or (tok == ","):
                continue
            elif self.__noConstant.search(tok) != None:
                continue
            elif (tok == "(") or (tok == ")"):
                continue
            elif (f := self.__funcEnd.search(tok)) and (instr[i+1] == "("):
                if not ret:
                    self.depGraph.add_edge(f.group(0),lhs,type="func")
                else:
                    self.depGraph.add_edge(f.group(0),lhs,type="return")
            elif (v := self.__specialAccess.search(tok)) and (not self.__numberbegin.search(tok)) and (not self.__noConstant.search(tok)):
                if not ret:
                    self.depGraph.add_edge(v.group("first"),lhs,type="var")
                else:
                    self.depGraph.add_edge(v.group("first"),lhs,type="return")
            else:
                continue
        return
    
    def __getVariablesOfString2(self,strIn : str,lhs,rek = 0): #special Case for [...]
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


    def areSimilar(self,g1 :nx.Graph, g2 : nx.Graph):
        pass

def main():
    with open("/home/jannis/Desktop/c-Code.txt") as f:
        cCode = f.read()
    dgrc = DependencyGraphfromCFunction()
    dg = dgrc.getDependencyGraph(cCode)
    for x in dg.edges():
        print(x)
    ix.network(dg,layout=nx.arf_layout(dg),node_labels=True)
    ax = pp.gca()
    ax.set_facecolor("#bfbfbf")
    pp.show()


if __name__ == "__main__":
    main()
