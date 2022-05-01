# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 21:52:24 2020

@author: Gachon
"""

class PcnStat:
    def __init__(self):
        self.rejectPbt = 0;
        self.numTransaction = 0;
        self.numPayment = 0;
        self.outage = 0;
        self.rreq = 0;
        self.rrep = 0;
        self.hello = 0;
        self.recvhello = 0;
        self.hops = 0;
        self.nonePcnNodes = 0;
        self.incentive = {}
        self.queuedTrans = {}
        self.avgPayDelay = {}
        self.minPayDelay = {}
        self.maxPayDelay = {}
        self.manetFoward = {}
        self.pktDrop = 0
        self.cancel = set();
        self.succPbt = set()
        self.maxTxQLen = {}
    
    
gStat = 0;    
def initPcnStat(numNodes, edges, payFlows):
    global gStat;
    gStat = PcnStat();
    for n in range(numNodes):
        gStat.incentive[n] = 0
    for n in edges:
        gStat.queuedTrans[n] = 0
        gStat.maxTxQLen[n] = 0
    for n in payFlows:
        gStat.avgPayDelay[n] = 0
        gStat.minPayDelay[n] = 0
        gStat.maxPayDelay[n] = 0
    for n in range(numNodes):
        gStat.manetFoward[n] = 0
    

def saveStatResult():
    global gStat;
    f = open("stat", mode='a')
    f.write("-------------------------------------------------------------------\n");
    f.write("Number of successful transaction: "+ str(gStat.numTransaction) + "\n")
    f.write("Number of payment: "+ str(gStat.numPayment) + "\n")
    f.write("Number of success PBT: " + str(len(gStat.succPbt)) +',' + str(gStat.succPbt) + "\n")
    f.write("Number of cancel: " + str(len(gStat.cancel)) +',' + str(gStat.cancel) + "\n")
    f.write("Rejected PBTs: "+ str(gStat.rejectPbt) + "\n")
    f.write("On-chain access: "+ str(gStat.outage) + "\n")
    f.write("Number of RREQ: "+ str(gStat.rreq) + "\n")
    f.write("Number of RREP: "+ str(gStat.rrep) + "\n") 
    f.write("Number of sentHELLO: "+ str(gStat.hello) + "\n")
    f.write("Number of recvHELLO: "+ str(gStat.recvhello) + "\n")
    f.write("Number of hops: "+ str(gStat.hops) + "\n")
    f.write("Number of none PCN users: "+ str(gStat.nonePcnNodes) + "\n")
    f.write("Incentive: "+ str(gStat.incentive) + "\n")
    f.write("Number of Mean Queued transaction: "+ str(gStat.queuedTrans) + "\n")
    f.write("Number of Max Queue: "+ str(gStat.maxTxQLen) + "\n")
    f.write("Average PBT delay: "+ str(gStat.avgPayDelay) + "\n")
    f.write("Min PBT delay: "+ str(gStat.minPayDelay) + "\n")
    f.write("Max PBT delay: "+ str(gStat.maxPayDelay) + "\n")
    f.write("Manet forwarding: "+ str(gStat.manetFoward) + "\n")
    f.write("Manet packet drop: "+ str(gStat.pktDrop) + "\n")
    f.close();
    qList = [q for q in gStat.maxTxQLen.values() if q != 0]
    print(qList)
    #maxD = [min(d, 3) for d in gStat.maxPayDelay.values()]
    return 1- len(gStat.cancel)/gStat.numPayment, list(gStat.avgPayDelay.values())[0], min(list(gStat.maxPayDelay.values())[0], 3), sum(qList)/len(qList)