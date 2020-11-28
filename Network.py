import networkx as nx
import matplotlib.pyplot as plt
import copy

class Network:
    def __init__(self,sat):
        self.G = nx.DiGraph()
        self.sat = sat
        # 初めにコピーしておく，その後は更新されるたびに色を更新って感じかな
        self.COMnodes = copy.deepcopy(self.sat.target_composCOM)
        self.TELnodes = copy.deepcopy(self.sat.target_composTEL)


    def add_edges(self):
        nx.add_path(self.G, self.COMnodes)
        nx.add_path(self.G, self.TELnodes)
        print(list(self.G.nodes))
        print(list(self.G.edges))
        print(list(self.G.out_edges("GS")))
        self.set_attribute()

        self.A = nx.nx_agraph.to_agraph(self.G)
        self.A.draw("../targetCompos.png",prog='sfdp')
        print(nx.get_node_attributes(self.G, 'size'))
        
        #nx.nx_agraph.view_pygraphviz(self.G, prog='circo')  # pygraphvizが必要
        
        #nx.draw(self.G)
    
    def set_attribute(self):
        size = {}
        for node in self.G.nodes:
            link_num = len(self.sat.compos[node].COM_link + self.sat.compos[node].TEL_link)
            size[node] = link_num
            #self.A.get_node(node).attr['width'] = link_num
            #self.A.get_node(node).attr['height'] = link_num
            
        nx.set_node_attributes(self.G,name='size',values=size)
        nx.set_edge_attributes(self.G, name='width',values=10)
        
        

