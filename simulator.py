# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 17:48:00 2020

@author: Gachon
"""

import matplotlib.pyplot as plt
from random import *
import sys

import simEvent;
import simTimer;
import routing;
import pcnStat;
import resPlot;
import random;
import test

import simMsg;
from node import *;
from util import *;
from transport import *;


# demand = {(1,2):50, (2,1):100, (1,4):50, (4,1):50, (2,4):50, (4,2):100, (1,3):100, (3,1):50,  (2,3):50, (3,2):50, (3,4):100, (4,3):50}


SIMULATION_TIME = 0.2* MINUTE;
NUM_NODES = 20;
CONN_PROB = 0.1;


PAY_DEF_INTERVAL = SECOND; #1sec
ROUTING_INTERVAL = 60 *SECOND;

INIT_DEPOSIT = 1000
MAX_AMOUNT_PER_PAY = INIT_DEPOSIT
MIN_AMOUNT_PER_PAY = INIT_DEPOSIT * 0.7


nodes =[]

#sock == bi-directional connections
#payGo F1 scenario
#sockConn = [(0,1),(0,2),(0,3),(1,4),(1,5),(1,6), (2,4),(2,5),(2,6), (3,4),(3,5),(3,6), (4,7), (5,7), (6,7) ];
linearNet = None
if linearNet:
    #linear network 3 PCs
    sockConn = [(0,1),(1,2),(2,3)] 
    sockConns = [] #overlay directional UDP connections
    for e in sockConn:
        a, b = e;
        sockConns += [(a,b), (b,a)]
    
    #gType =0 (manual graph), 1: powerlaw graph, 2:...
    topo = routing.Topology(NUM_NODES, sockConn, 0);
else:
    topo, partition = test.genMPC(NUM_NODES)

#application for PBT
INIT_SIM =True;
payers = [0, 3]
PBTs =[(0, 3), (3, 0)]


def smartContractForDispute(n1, n2, transPbtId): #n1 has not received unlock from n2
    nodes[n1].channels[n2].reImburse(transPbtId)
    nodes[n2].channels[n1].unlock(transPbtId)
    
def genNodeLink(numNodes, sockConns):
    global nodes;
    nodes = [];
    pcnUser = None;
    for n in range(numNodes):
        pcnUser = Node(n) # PCN node
        pcnUser.setBlockchainAccess(smartContractForDispute)
        nodes.append(pcnUser)        
    #open payment channel over socket connection
    for e in sockConns:
        a, b = e;
        nodes[a].createSockPayCh(nodes[b], INIT_DEPOSIT)



def initializeSim(numNodes, sockConns, topo, pbts):      
    global INIT_SIM;
    INIT_SIM == True;    
    routing.setGlobalTopo(topo);
    simTimer.globalTic = 0;
    simTimer.initTimeList();
    simEvent.initEventQ();
    genNodeLink(numNodes, sockConns);
    pcnStat.initPcnStat(numNodes, sockConns, pbts)

def payApp(payer, payee, amount, routePeriod):    
    MSG_LOG(LOG_TYPE_PROCESS, "[app] send transaction from "+str(payer) + " to "+ str(payee))
    n = routing.getNextHop(payer, payee);
    nodes[payer].payTo(payer, payee, amount, n, simTimer.globalTic+ 3*SECOND, routePeriod)
      
def doSimulation(pays, simParam):  
    for p in PBTs:        
        if simTimer.globalTic % simParam == 0: # interval
            payApp(p[0], p[1], MIN_AMOUNT_PER_PAY, ROUTING_INTERVAL)
    for n in nodes:
        n.doProcess(); #arg = hello period

def finishSim():
    return pcnStat.saveStatResult();

def ticStart(pays, simParam):
    while simTimer.globalTic < SIMULATION_TIME:
        simTimer.globalTic += 1;
        #print("tic ", simTimer.globalTic );
        simTimer.timeList.updateClock();
        doSimulation(pays, simParam);
        
    return finishSim();
    
################################
# main loop
#################################
para = list(range(10, 100, 10)) #period of hellow, rreq, etc

x = []; y = []; y1 = [];
for p in para:
    initializeSim(NUM_NODES, sockConns, topo, PBTs)
    succRatio, avgDelay, maxDelay, avgQ = ticStart(PBTs, p);
    x.append(p/1000);
    y.append(succRatio);
    y1.append(avgQ)
    #y1.append(failures);
    #y1.append(pcnStat.gStat.avgPayDelay[(0, 4)])
    

#resPlot.drawPlot(x, y);
#plt.plot(x,y, 'r--', label="Success")
#plt.plot(x,y, 'r--')
#plt.scatter(x,y1, label="Fail")

fig, ax1 = plt.subplots()
l1 = ax1.plot(x,y, 'r--', label="Success ratio")
#l2 = ax1.scatter(x,y2, label="Fail")
ax1.set_ylabel("Success ratio")
ax1.set_xlabel("Payment interval (s)") 



ax2 = ax1.twinx()
l3 = ax2.scatter(x,y1, label="Queued pays", marker='D', s=50)
ax2.set_ylabel("Transactions")
ax2.legend(loc="center right")

#plt.ylabel("Transactions")
#plt.xlabel("Payment interval")    
#plt.title("PCN throughput in imbalanced PBT flows")
#plt.legend()
plt.show()
fig.savefig("foo.pdf", bbox_inches='tight')
