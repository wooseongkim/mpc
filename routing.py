# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 11:23:11 2020

@author: Gachon
"""


import networkx as nx
import matplotlib.pyplot as plt
import copy;
import simTimer

gTopo = 0;
ONDEMAND_ROUTING = 0
PROACTIVE_ROUTING = 1

#overlay pcn topology
class Topology():
    def __init__(self, numNodes, edge = [], gType=0):
        self.numNodes = numNodes
        self.edge = edge
        if gType == 0:
            self.graph = nx.Graph()
            self.graph.add_nodes_from(tuple(range(numNodes)))
            self.graph.add_edges_from(edge)
        elif gType == 1:
            self.graph = nx.powerlaw_cluster_graph(numNodes, 3, 0.7) #degree=3, triangle=10%
            self.edge = nx.edges(self.graph)

        nx.draw(self.graph)
        plt.show()
    def updateTopoWithEdge(self, e):
        if e not in self.edge and (e[1], e[0]) not in self.edge:
            self.edge.append(e)
            self.graph.add_edges_from(self.edge)
        
    def getConnectedPeers(self, n):
        peerIDs = []
        for e in self.edge:
            if n == e[0]: 
                peerIDs.append(e[1])
            elif n == e[1]:
                peerIDs.append(e[0])
        return peerIDs
        
        

class PCNRoutingEntry():
    def __init__(self, dest, nextNode, hops, capa, gTick):
        self.dest = dest
        self.next = nextNode
        self.hops = hops
        self.capa = capa
        self.time = gTick;
    def update(self, hops, capa, time):
        self.hops = hops;
        self.capa = capa;
        self.time = time;
        
class SourcePBTEntry():
    def __init__(self, dest, path, hops, capa, gTick):
        self.dest = dest
        self.path = copy.deepcopy(path)
        self.hops = hops
        self.capa = capa
        self.time = gTick;
        
class PCNRoutingTable():
    def __init__(self):
        self.pbtTable = {} #source routing table
        self.table = {} #per-ho table (dsdv)
        self.recvRreqFrom = {};
        self.mode = 0
        self.onDemandTimer = 0;        
        
    def obsoleteEntries(self):
        oldEntry =[];
        if self.pbtTable:
            for e in self.pbtTable:
                if self.pbtTable[e].time > simTimer.globalTic:
                    oldEntry.append(e)
            for e in oldEntry:
                del self.pbtTable[e];
        oldEntry =[];
        if self.table:
            for e in self.table:
                for n in self.table[e]:
                    if self.table[e][n].time > simTimer.globalTic:
                        oldEntry.append((e,n))
            for t in oldEntry:                
                del self.table[t[0]][t[1]];
                
    def getNextHops(self, dst):
        nextNodes = []
        if dst not in self.table:
            return nextNodes;
        
        for e in self.table[dst]:
            nextNodes.append(e)
        return nextNodes;
    def addNewEntry(self, dest, nextNode, hops, capa, time):
        self.table [dest] = {};
        self.table[dest][nextNode] = PCNRoutingEntry(dest, nextNode, hops, capa, time)
    def updateEntry(self, dest, nextNode, hops, capa, time):
        if dest not in self.table:
            self.addNewEntry(dest, nextNode, hops, capa, time)
        elif nextNode in self.table [dest]:
            self.table[dest][nextNode].update(hops, capa, time)
        else:
            self.table[dest][nextNode] = PCNRoutingEntry(dest, nextNode, hops, capa, time) 
    def updatePbtEntry(self, dest, path, capa, time):
            self.pbtTable[dest] = SourcePBTEntry(dest, path, len(path), capa, time);

class PCNNeighbor():
    def __init__(self, _id, _exp):
        self.id = _id;
        self.qTransLen = {}; #per flow
        self.qTransAmount = {};
        self.exp = _exp;
        
class PCNNeighborTable():            
        def __init__(self):
            self.table = {}            
        def updateEntry(self, nodeId, flowId =0, qLen = 0, qAmount =0, timer=60000): #1 min default
            if nodeId not in self.table:
                ngb = PCNNeighbor(nodeId, timer);
            else:
                ngb = self.table[nodeId]
            ngb.exp = timer;
            if flowId:
                ngb.qTransLen[flowId] = qLen;
                ngb.qTransAmount[flowId] = qAmount;
                self.table[nodeId] = ngb;
        def lookupPendTrans(self, nh, flowId):
            if nh in self.table and flowId in self.table[nh].qTransLen:
                return self.table[nh].qTransLen[flowId], self.table[nh].qTransAmount[flowId]
            return 0, 0
    
def getMultiPath(s, d, margin):
    global gTopo;
    paths = [];
    #nx.all_simple_paths(graph, source, target, cutoff=routeLen+ rMargin)
    routeLen = len(nx.shortest_path(gTopo.graph, s, d))
    for p in nx.all_simple_paths(gTopo.graph, s, d, cutoff=routeLen+ margin):
        #print(p)
        paths.append(p)
    return paths;

def getNextHops(s, d, margin):
    path = getMultiPath(s, d, margin)
    n = set();
    for p in path:
        n.add(p[1])
    return list(n);

def getNextHop(s, d):
    global gTopo;
    path = nx.shortest_path(gTopo.graph, s, d)
    if len(path) > 1:
        return path[1];
    else:
        return -1;

def setGlobalTopo(topo):
    global gTopo;
    gTopo = topo;
