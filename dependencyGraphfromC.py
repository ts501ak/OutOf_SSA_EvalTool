from typing import DefaultDict
import networkx as nx
import re
import matplotlib.pyplot as pp

def fnv1a_64(s):
    h = 0xcbf29ce484222325  # 64-bit offset basis
    fnv_prime = 0x100000001b3
    for c in s:
        h ^= ord(c)
        h = (h * fnv_prime) & 0xFFFFFFFFFFFFFFFF  # modulo 2^64
    return f"{h:016x}"  # 16-character hex string

class DependencyGraphfromCFunction:
    def __init__(self):
        """As this class will compute a few thousand dependency graphs we precompile all our regexes in advance, so we don't have to do it every single run
        We ingore nested tenary-Assignments"""

        self.__regs = []
        self.__regs.append(re.compile(r"//.*")) #No Comments
        self.__regs.append(re.compile(r"/\*.*?\*/",re.DOTALL)) #No Multiline Comments
        #self.__regs.append(re.compile(r'"(\\.|[^"\\])*"')) #No Strings --> Strings are hashed by now and seen as a normal constant
        #self.__regs.append(re.compile(r"'(\\.|[^'\\])*'")) #No Strings 
        self.__stringIdent = re.compile(r"§§STR§§[a-fA-F0-9]{16}§")
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
        self.__newLineNoSC = re.compile(r"(?<!;)[ \t]*\n")
        self.__wsEquals = re.compile(r" *= *")
        self.__assignOperators = ["=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="]
        self.__operators = ["+","-", "*", "/", "%", "==", "!=", "[^-]>", "<", ">=", "<=", "&&", "||", "&", "|", "^", "<<", ">>"]
        #self.__delims = ["+","-", "*", "/", "%", "==", "!=", ">", "<", ">=", "<=", "&&", "||", "&", "|", "^", "<<", ">>",")","(",",","[","]"]
        self.__types = re.compile(r"\b(char|int|float|double|signed|short|long|bool|_Bool|void|uint[0-9]*_t|int[0-9]*_t|size_t|double_t|float_t|daddr_t|caddr_t|clock_t|ino_t|cnt_t|dev_t|chan_t|off_t|offset_t|off64_t|soff_t|paddr_t|key_t|time_t|nlink_t|mode_t|uid_t|gid_t|mid_t|pid_t|slab_t|mtyp_t|ssize_t|size_t|uchar_t|ushort_t|uint_t|ulong_t|trace_attr_t|trace_id_t|trace_event_id_t|trace_event_set_t)\b")
        self.__variable = re.compile(r"[A-Za-z_]\w*")
        self.__variableAssign = re.compile(r"(?P<first>[A-Za-z_]\w*)((\.|->|\[[^\]]+\]\.|\[[^\]]+\]->|\[.*\])*[A-Za-z_]\w*)*(\[[^\]]+\])* *((?<!=)=(?!=)|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)")
        self.__funcEnd = re.compile(r"[A-Za-z_]\w*$")
        self.__funcNorm = re.compile(r"[A-Za-z_]\w*\(")
        self.__oneequals = re.compile("[^=]=[^=]")
        self.__Constant = re.compile(r"^( |\t)*(?P<num>((?P<Hex>(0[x|X]([0-9]|[ABCDEF]|[abcdef])+(\.([0-9]|[ABCDEF]|[abcdef])*)?((P|p)(\+|-)?([0-9]|[ABCDEF]|[abcdef])+)?))|(?P<Dec>([0-9_]*\.[0-9]+(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))|(?P<Dec2>([0-9_]+\.[0-9]*(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))|(?P<Bin>(0[B|b][10]+))|(?P<NULLL>(NULL))|(?P<Oct>(0[0-7]*))|(?P<Dec3>([1-9][0-9_]*(((E|e)(\+|-)?[0-9]+)|( *i| *I| *j| *J))?))))")
        self.__pat = r"((?<!(E|e))\+(?!(>|\+|-))|(?<!(E|e))\-(?!(>|\+|-))|\*|/|%|==|!=|>=|<=|(?<!-)>|<|\&\&|\|\||\&|\||\^|<<|>>|\)|\(|,|\[|\])"
        self.__specialAccess = re.compile(r" *(?P<first>[A-Za-z_]\w*) *((\.|->) *[A-Za-z_]\w*)*")
        self.__numberbegin = re.compile(r"^ *[0-9]")
        self.__ternaryAssig = re.compile(r"\?(?P<ifTrue>[^:\n]*):(?P<ifFalse>[^;\n]*)")
        self.__dotVar = re.compile(r"(^ *\. *[A-Za-z_]\w*|^ *-> *[A-Za-z_]\w*)")
        self.__counter = 0
        self.__dels = re.compile(r"([ \.Pp\+\-])")
        self.__newLine = re.compile(" *\n *")
        self.__Union = re.compile(r"(union.*?)(\} *;\n)",re.DOTALL)
        self.__funcCall = re.compile(r"[A-Za-z_]\w* *\(")
        self.__keyWords = re.compile(r"^ *(auto|char|double|enum|float|int|long|short|signed|struct|union|unsigned|void|break|case|continue|default|do|else|for|goto|if|return|switch|while|const|extern|register|static|typedef|volatile|_Bool|_Complex|_Imaginary|inline|restrict|_Noreturn|_Alignas|_Alignof|_Atomic|_Generic|_Static_assert|_Thread_local) *$")
        


    def getDependencyGraph(self,cFunc : str) -> nx.DiGraph:
        """takes the code of a single function as ascii and builds the dependency graph for it"""

        self.__func = cFunc
        self.__prepareFunc()
        self.__counter = 0
        return self.__constructDepGraph()
    
    def getFuncGraph(self,cFunc : str) -> nx.DiGraph:
        """takes the code of a single function as ascii and builds the dependency graph for it"""

        self.__func = cFunc
        self.__prepareFunc()
        self.__counter = 0
        return self.__constructFuncGraph()

    def _fnv1a_64(self, s):
        """
        Computes the FNV-1a 64-bit hash of a string.
        """
        h = 0xcbf29ce484222325
        fnv_prime = 0x100000001b3
        
        # Use a mask to enforce 64-bit behavior for compatibility 
        MASK_64 = 0xFFFFFFFFFFFFFFFF 
        
        for c in s:
            h ^= ord(c)
            h = (h * fnv_prime) & MASK_64
            
        return f"{h:016x}"

    def _process_strings_to_hashes(self):
        """
        Processes code stored in self.__func to replace concatenated 
        string literals with their FNV-1a 64-bit hash.
        """
        code = self.__func
        result = []
        i = 0
        n = len(code)

        while i < n:
            c = code[i]
            prefix = ''
            start_q = -1 
            
            # Identify Prefix and First Quote
            if c == '"':
                # String literal (e.g. "Hello")
                prefix = ''
                start_q = i
            elif c == 'L' and i + 1 < n and code[i+1] == '"':
                # Wide string literal (e.g. L"Hello")
                prefix = 'L'
                start_q = i + 1
            
            # Process Concatenated String Group
            if start_q != -1:
                i = start_q + 1 
                combined = ''
                
                # This loop handles adjacent literals of the same type
                while start_q < n and code[start_q] == '"':
                    
                    # Read string content
                    s = ''
                    while i < n:
                        if code[i] == '"':
                            i += 1
                            break

                        elif code[i] == '\\' and i+1 < n:
                            # Skip spaces after a \ for a line break
                            if code[i+1].isspace():
                                i += 1
                                while i < n and code[i].isspace():
                                    i += 1

                            # Handle escaped chars like \, \n
                            else:
                                s += code[i:i+2]
                                i += 2
                        else:
                            s += code[i]
                            i += 1

                    combined += s.encode('utf-8').decode('unicode_escape')
                    
                    # Skip whitespace/newlines between adjacent literals
                    while i < n and code[i].isspace():
                            i += 1

                    next_start_q = -1
                    
                    # Check for new string 
                    if prefix == '' and i < n and code[i] == '"':
                        next_start_q = i
                        i += 1 
                        
                    # Check for new wide string 
                    elif prefix == 'L' and i + 1 < n and code[i] == 'L' and code[i+1] == '"':
                        next_start_q = i + 1
                        i += 2 
                        
                    if next_start_q == -1:
                        break
                    else:
                        start_q = next_start_q 
                        
                # Comment out and prefix with 'L' if desired
                combined += prefix 
                hashed = fnv1a_64(combined)
                result.append(f'§§STR§§{hashed}§')
            else:    
                result.append(c)
                i += 1
                
        self.__func = ''.join(result)

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
                return str(float(bin,2))
            elif oct := matO.group("Oct"):
                if oct == "0":
                    return "0"
                oct = oct[1:]
                return str(float(oct,8))
            elif nu := matO.group("NULLL"):
                return "0"
            return str(float(matO.group("num")))
        
        raise Exception(f"Couldn't convert {inp} to Dec!")

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
        self.__func = self.__newLineNoSC.sub(r" ",self.__func)
        self._process_strings_to_hashes()
        self.__func = self.__wsBeginning.sub(r"\n",self.__func)
        self.__func = self.__wsEquals.sub(r"=",self.__func)
        self.__func = self.__Union.sub(r"",self.__func)
        self.__func = self.__newLine.sub(r" ",self.__func)
        

    def __constructDepGraph(self) -> nx.DiGraph:
        """computes the dependency graph of a given preprocessed function
            Tenary assignments are ignored"""
        
        self.depGraph = nx.DiGraph()
        
        #for line in self.__func.split("\n"):
        for instr in [x for x in self.__func.split(";") if x != '']:
            if any(aop in instr for aop in self.__assignOperators) and (not "return" in instr) and (not "union" in instr) and (self.__oneequals.search(instr)): #No == as Assignmet Operator
                if assi := self.__variableAssign.search(instr):
                    lhs = assi.group("first")
                    #if (ind := assi.group(0).find("[")) != -1: #No more detection of Array access, bc this may get lost after OoSSA or is added afterwards
                    #    self.__getVariablesOfString2(instr[ind+1:len(assi.group(0))-1],lhs)
                    start = instr.find(assi.group(0))
                    instr = instr[start + len(assi.group(0)):]
                    if ta := self.__ternaryAssig.search(instr):
                        nodeName = self.__getVarName()
                        self.depGraph.add_node(nodeName,type=lhs)
                        self.depGraph.add_edge(nodeName,lhs,type="assig")
                        self.__getVariablesOfString(self.__getBracketGroup(ta.group("ifTrue")),nodeName)
                        nodeName = self.__getVarName()
                        self.depGraph.add_node(nodeName,type=lhs)
                        self.depGraph.add_edge(nodeName,lhs,type="assig")
                        self.__getVariablesOfString(self.__getBracketGroup(ta.group("ifFalse")),nodeName)
                    else:
                        nodeName = self.__getVarName()
                        self.depGraph.add_node(nodeName,type=lhs)
                        self.depGraph.add_edge(nodeName,lhs,type="assig")
                        self.__getVariablesOfString(instr,nodeName)
            
            elif (ind := instr.find("return")) != -1:
                if ta := self.__ternaryAssig.search(instr[ind + 6:]):
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return",type="return")
                    self.__getVariablesOfString(self.__getBracketGroup(ta.group("ifTrue")),nodeName)
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return",type="return")
                    self.__getVariablesOfString(self.__getBracketGroup(ta.group("ifFalse")),nodeName)
                else:
                    nodeName = self.__getVarName()
                    self.depGraph.add_edge(nodeName,"return",type="return")
                    self.__getVariablesOfString(instr[ind + 6:],nodeName)


        self.depGraph.remove_edges_from(list(nx.selfloop_edges(self.depGraph)))
        return self.depGraph
    
    def __constructFuncGraph(self) -> nx.DiGraph:
        """computes the dependency graph of a given preprocessed function
            Tenary assignments are ignored"""
        
        self.depGraph = nx.DiGraph()
        
        #for line in self.__func.split("\n"):
        for instr in [x for x in self.__func.split(";") if x != ''][1:]:
            if (mat := self.__funcCall.search(instr)):
                self.__getVariablesOfString2(instr[mat.start():],"dummy")

        self.depGraph.remove_edges_from(list(nx.selfloop_edges(self.depGraph)))
        return self.depGraph
    
    def __getVariablesOfString2(self,strIn : str,lhs:str,isFunc = False):
        funcArgCount = 0
        instr = re.split(self.__pat,strIn)
        instr = [i for i in instr if (i != '') and (i != None)]
        instr.append(";")
        count = -1
        while (count) < (len(instr) - 1):
            tok = instr[count]
            if self.__types.search(tok):
                pass
            elif (tok in self.__operators) or (tok == ","):
                pass
            elif ((const := self.__Constant.search(tok)) != None) and (lhs != "dummy"):
                #print(strIn,"-->",const.group(0),flush=True)
                const = self.__constantToDec(const.group("num"))
                if not isFunc:
                    self.depGraph.add_edge(const,lhs,type="const")
                else:
                    self.depGraph.add_edge(const,lhs,type="const",nr = funcArgCount)
                    funcArgCount += 1
                
            elif (tok == "(") or (tok == ")"):
                pass
            elif (string := self.__stringIdent.search(tok)) and (lhs != "dummy"):
                if not isFunc:
                    self.depGraph.add_edge(string.group(0),lhs,type="strConst")
                else:
                    self.depGraph.add_edge(string.group(0),lhs,type="strConst",nr = funcArgCount)
                    funcArgCount += 1
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "("):
                if self.__keyWords.search(tok) == None:
                    funcName = f"{f.group(0)}${self.__counter}"
                    self.__counter += 1
                    if not isFunc:
                        self.depGraph.add_edge(funcName,lhs,type="func")
                    else:
                        self.depGraph.add_edge(funcName,lhs,type="func", nr = funcArgCount)
                        funcArgCount += 1
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
                    self.__getVariablesOfString(rest,funcName,True)
                    count = brcount + 1    #This is why we use while(index < int) instead of for i in range(int)
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "["): #Array (but with Function Variables :) Sorry)
                funcName = f"{f.group(0)}${self.__counter}"
                self.__counter += 1
                if lhs != "dummy":
                    self.depGraph.add_edge(funcName,lhs,type="array",nr = funcArgCount)
                    funcArgCount += 1
                brcount = 0
                for i in range(count+1,len(instr)-1):
                    if instr[i] == "[":
                        brcount += 1
                    elif instr[i] == "]":
                        brcount -= 1
                    if brcount == 0:
                        brcount = i
                        break
                count = brcount + 1    #This is why we use while(index < int) instead of for i in range(int)
                
            elif (v := self.__specialAccess.search(tok)) and (not self.__numberbegin.search(tok)) and (not self.__Constant.search(tok)) and (lhs != "dummy"):
                if lhs is not None:
                    self.depGraph.add_edge(v.group("first"),lhs,type="var",nr = funcArgCount)
                    funcArgCount += 1
            else:
                pass
            count += 1
        return
    
    def __getBracketGroup(self,case:str):
        brcount = 0
        for i in range(len(case)):
            if case[i] in ["(","["]:
                brcount += 1
            elif case[i] in [")","]"]:
                brcount -= 1
            if brcount < 0:
                return case[:i]
        return case
    
    def __getVarName(self):
        nodeName = f"$help{self.__counter}$"
        self.__counter += 1
        return nodeName

    def __getVariablesOfString(self,strIn : str,lhs:str,isFunc = False):
        funcArgCount = 0
        instr = re.split(self.__pat,strIn)
        instr = [i for i in instr if (i != '') and (i != None)]
        instr.append(";")
        count = -1
        while (count) < (len(instr) - 1):
            tok = instr[count]
            if self.__types.search(tok):
                pass
            elif (tok in self.__operators) or (tok == ","):
                pass
            elif (const := self.__Constant.search(tok)) != None:
                #print(strIn,"-->",const.group(0),flush=True)
                const = self.__constantToDec(const.group("num"))
                if not isFunc:
                    self.depGraph.add_edge(const,lhs,type="const")
                else:
                    self.depGraph.add_edge(const,lhs,type="const",nr = funcArgCount)
                    funcArgCount += 1
                
            elif (tok == "(") or (tok == ")"):
                pass
            elif string := self.__stringIdent.search(tok):
                if not isFunc:
                    self.depGraph.add_edge(string.group(0),lhs,type="strConst")
                else:
                    self.depGraph.add_edge(string.group(0),lhs,type="strConst",nr = funcArgCount)
                    funcArgCount += 1
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "("):
                funcName = f"{f.group(0)}${self.__counter}"
                self.__counter += 1
                if not isFunc:
                    self.depGraph.add_edge(funcName,lhs,type="func")
                else:
                    self.depGraph.add_edge(funcName,lhs,type="func", nr = funcArgCount)
                    funcArgCount += 1
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
                self.__getVariablesOfString(rest,funcName,True)
                count = brcount + 1    #This is why we use while(index < int) instead of for i in range(int)
            elif (f := self.__funcEnd.search(tok)) and (instr[count+1] == "["): #Array (but with Function Variables :) Sorry)
                funcName = f"{f.group(0)}${self.__counter}"
                self.depGraph.add_edge(funcName,f.group(0),type="ReferenceArray")
                self.__counter += 1
                if not isFunc:
                    self.depGraph.add_edge(funcName,lhs,type="array")
                else:
                    self.depGraph.add_edge(funcName,lhs,type="array",nr = funcArgCount)
                    funcArgCount += 1
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
                if not isFunc:
                    self.depGraph.add_edge(v.group("first"),lhs,type="var")
                else:
                    self.depGraph.add_edge(v.group("first"),lhs,type="var",nr = funcArgCount)
                    funcArgCount += 1
            else:
                pass
            count += 1
        return
    

class CompareGraphs:
    def __init__(self,c1 : str,c2:str):
        self.c1 = c1
        self.c2 = c2

    def getSameVars(self):
        dgfc = DependencyGraphfromCFunction()
        dg1 = dgfc.getDependencyGraph(self.c1)
        dg2 = dgfc.getDependencyGraph(self.c2)
        df1 = dgfc.getFuncGraph(self.c1)
        df2 = dgfc.getFuncGraph(self.c2)
        a,b = self.getSameVarsfromFunctionCalls(dg1,dg2)
        c,d = self.getSameVarsfromFunctionCalls(df1,df2)
        return self.__mergeDicts(a,c), b

    def __mergeDicts(self,d1 :dict, d2 : dict):
        res = {}
        for k in set(list(d1.keys()) + list(d2.keys())):
            values = []
            if k in d1.keys():
                values.extend(d1[k])
            if k in d2.keys():
                values.extend(d2[k])
            res[k] = list(set(values))
        return res
            

    def areSimilar(self,g1 :nx.DiGraph, g2 : nx.DiGraph):
        a,b = self.getSameVarsfromFunctionCalls(g1,g2)
        for x in a.keys():
            print(x,a[x])
        for y in b.keys():
            print(y,b[y])
        pass

    def __getFuncArgumentsFromGraph(self,g : nx.DiGraph,node : str):
        funcSig = []
        varList = []
        for argument in sorted(list(g.in_edges(node,data=True)),key=lambda x : x[2]["nr"]):
            match argument[2]["type"]:
                case "const" | "strConst":
                    funcSig.append(argument[0])
                case "func":
                    fs, vl = self.__getFuncArgumentsFromGraph(g,argument[0])
                    funcSig.append("(")
                    funcSig.extend(fs)
                    funcSig.append(")")
                    varList.extend(vl)  
                case "array":
                    funcSig.append("a")
                    varList.append(argument[0].split("$")[0])
                case "var":
                    funcSig.append("v")
                    varList.append(argument[0])
        return funcSig, varList

    def getSameVarsfromFunctionCalls(self, g1 : nx.DiGraph, g2 : nx.DiGraph):
        equivalenceDictSure = DefaultDict(lambda : [])
        equivalenceDictUnsure = DefaultDict(lambda : [])
        g1Dict = DefaultDict(list)
        g2Dict = DefaultDict(list)
        assignmentDict = DefaultDict(list)
        typeDict = nx.get_node_attributes(g1,"type","None")
        for funcCall in g1.edges(data="type",default=""):
            if funcCall[2] == "func":
                fs, vl = self.__getFuncArgumentsFromGraph(g1,funcCall[0])
                h = hash(tuple(fs))
                #print("Function",funcCall[0],fs,vl, h)
                if (lhs := typeDict[funcCall[1]]) != "None":
                    assignmentDict[h].append(lhs)
                g1Dict[h].append(vl)
        typeDict = nx.get_node_attributes(g2,"type","None")
        for funcCall in g2.edges(data="type",default=""):
            if funcCall[2] == "func":
                fs, vl = self.__getFuncArgumentsFromGraph(g2,funcCall[0])
                h = hash(tuple(fs))
                #print("Function",funcCall[0],fs,vl, h)

                if (lhs := typeDict[funcCall[1]]) != "None":
                    assignmentDict[h].append(lhs)
                g2Dict[h].append(vl)
        for x in g1Dict.keys():
            if (len(g1Dict[x]) == 1) and (x in g2Dict.keys()) and (len(g2Dict[x]) == 1):
                for y in range(len(g1Dict[x][0])):
                        #if g1Dict[x][0][y] not in equivalenceDictSure[g2Dict[x][0][y]]:
                        #    equivalenceDictSure[g2Dict[x][0][y]].append(g1Dict[x][0][y]) 
                        if g2Dict[x][0][y] not in equivalenceDictSure[g1Dict[x][0][y]]:
                            equivalenceDictSure[g1Dict[x][0][y]].append(g2Dict[x][0][y]) 
                if len(assignmentDict[x]) == 2:
                    equivalenceDictUnsure[assignmentDict[x][0]].append(assignmentDict[x][1])
                    #equivalenceDictUnsure[assignmentDict[x][1]].append(assignmentDict[x][0])

        return equivalenceDictSure, equivalenceDictUnsure


def main():
    with open("/home/jannis/Desktop/ex1.txt") as f:
        c1 = f.read()
        print(c1)
    with open("/home/jannis/Desktop/ex2.txt") as f:
        c2 = f.read()
        print(c2)

    dgrc = DependencyGraphfromCFunction()
    cc1 = dgrc.getFuncGraph(c1)
    c1 = dgrc.getDependencyGraph(c1)
    
    print(cc1.edges(data=True))
    c2 = dgrc.getDependencyGraph(c2)
    dgrc.areSimilar(c1,c2)
    pass


if __name__ == "__main__":
    main()
