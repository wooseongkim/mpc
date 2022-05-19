# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 17:48:00 2020

@author: Gachon
"""

import matplotlib.pyplot as plt
from matplotlib import rc_file
from matplotlib import rcParams
from random import *
import numpy as np
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


SIMULATION_TIME = 0.1* MINUTE;
NUM_NODES = 20;
CONN_PROB = 0.1;


PAY_DEF_INTERVAL = SECOND; #1sec
ROUTING_INTERVAL = 60 *SECOND;

INIT_DEPOSIT = 1000
MAX_AMOUNT_PER_PAY = INIT_DEPOSIT
MIN_AMOUNT_PER_PAY = INIT_DEPOSIT * 0.5


nodes = {}
sockConns = [] #overlay directional UDP connections
mpc = []
#sock == bi-directional connections
#payGo F1 scenario
#sockConn = [(0,1),(0,2),(0,3),(1,4),(1,5),(1,6), (2,4),(2,5),(2,6), (3,4),(3,5),(3,6), (4,7), (5,7), (6,7) ];
linearNet = None


#application for PBT
INIT_SIM =True;
payers = [1, 5]
PBTs =[(1, 5), (5, 1)]

def genTopo(numNodes):
    topo = None
    sockConns = []
    partition = []
    if linearNet:
        # linear network 3 PCs
        sockConn = [(0, 1), (1, 2), (2, 3)]
        for e in sockConn:
            a, b = e;
            sockConns += [(a, b), (b, a)]
        topo = routing.Topology(numNodes, sockConn, 0);
    else:
        topo, partition, sockConns = test.genMPC(numNodes)
    return topo, partition, sockConns

def smartContractForDispute(n1, n2, transPbtId): #n1 has not received unlock from n2
    nodes[n1].channels[n2].reImburse(transPbtId)
    nodes[n2].channels[n1].unlock(transPbtId)

def searchMpc(i,j, mpc):
    for m in mpc:
        if i in m.spcState and j in m.spcState:
            return m
    return None

def genNodeLink(numNodes, sockConns, mpc):
    global nodes;
    pcnUser = None;
    for n in range(0, numNodes):
        pcnUser = Node(n) # PCN node
        pcnUser.setBlockchainAccess(smartContractForDispute)
        nodes[n] = pcnUser
    #open payment channel over socket connection
    for a, b in sockConns: #sockConns - undirected edge
        _mpc = searchMpc(a,b, mpc) #mpc object
        if _mpc:
            if a not in _mpc.psp:
                _mpc.psp[a] = nodes[a]
            if b not in _mpc.psp:
                _mpc.psp[b] = nodes[b]
        nodes[a].createSockPayCh(nodes[b], INIT_DEPOSIT, _mpc)
        nodes[b].createSockPayCh(nodes[a], INIT_DEPOSIT, _mpc)

def initializeSim(numNodes, topo, partition, sockConns, pbts):
    global INIT_SIM;
    INIT_SIM == True;
    global mpc;
    mpc.clear()
    routing.setGlobalTopo(topo);
    simTimer.globalTic = 0;
    simTimer.initTimeList();
    simEvent.initEventQ();
    for p in partition:
        if p:
            print(p)
        if len(p) > 2: #2 pcs is not for mpc
            _pspSet = set()
            for i, j in p:
                _pspSet.add(i)
            mpc.append(MPC(len(mpc)+1, list(_pspSet), INIT_DEPOSIT))
    print("number of MPCs: ", len(mpc), ' partition: ', len(partition))
    genNodeLink(numNodes, sockConns, mpc)
    pcnStat.initPcnStat(numNodes, sockConns, pbts, len(mpc))

def payApp(payer, payee, amount, routePeriod):    
    MSG_LOG(LOG_TYPE_PROCESS, "[app] send transaction from "+str(payer) + " to "+ str(payee))
    n = routing.getNextHop(payer, payee);
    nodes[payer].payTo(payer, payee, amount, n, simTimer.globalTic+ 3*SECOND, routePeriod)
      
def doSimulation(pays, simParam):  
    for p in PBTs:        
        if simTimer.globalTic % simParam == 0: # interval
            payApp(p[0], p[1], MIN_AMOUNT_PER_PAY, ROUTING_INTERVAL)
    for m in mpc:
        m.updateRounds()
    for n in nodes:
        nodes[n].doProcess(); #arg = hello period


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

## rcParams dict
rcParams['axes.labelsize'] = 10
rcParams['xtick.labelsize'] = 10
rcParams['ytick.labelsize'] = 10
rcParams['legend.fontsize'] = 9
rcParams['font.family'] = 'DeJavu Serif'
rcParams['font.serif'] = ['Computer Modern Roman']
rcParams['text.usetex'] = True
rcParams['figure.figsize'] = 2.5, 2.5

para = list(range(20, 21, 10)) #period of hellow, rreq, etc

x = []; y = []; y1 = [];
for p in para:
    topo, partition, sockConns = genTopo(p)
    initializeSim(p, topo, partition, sockConns, PBTs)
    succRatio, avgDelay, maxDelay, avgQ = ticStart(PBTs, p);
    x.append(p);
    y.append(succRatio);
    y1.append(avgQ)
    #y1.append(failures);
    #y1.append(pcnStat.gStat.avgPayDelay[(0, 4)])
    
labels = ['20','30','40']
x = np.arange(len(labels))
#resPlot.drawPlot(x, y);
#plt.plot(x,y, 'r--', label="Success")
#plt.plot(x,y, 'r--')
#plt.scatter(x,y1, label="Fail")
width = 0.34
fig, ax1 = plt.subplots()
#rects1 = ax1.bar(x - width/2, y['sym'], width, label='asymmetry')
rects2 = ax1.bar(x, y, width, label='asymmetry')
#rects3 = ax1.bar(x + width, y[0.1], width, label='0.01')

ax1.set_xticks(x, labels)
#ax1.legend(loc='lower right')
#ax1.legend(loc='upper center')

ax1.set_ylabel("Success ratio")
ax1.set_xlabel("User demands")
fig.tight_layout()

#ax1.bar_label(rects1, padding=3)
#ax1.bar_label(rects2, padding=3)

# fig, ax1 = plt.subplots()
# l1 = ax1.plot(x,y, 'r--', label="Success ratio")
# #l2 = ax1.scatter(x,y2, label="Fail")
# ax1.set_ylabel("Success ratio")
# ax1.set_xlabel("Payment interval (s)")



# ax2 = ax1.twinx()
# l3 = ax2.scatter(x,y1, label="Queued pays", marker='D', s=50)
# ax2.set_ylabel("Transactions")
# ax2.legend(loc="center right")

#plt.ylabel("Transactions")
#plt.xlabel("Payment interval")    
#plt.title("PCN throughput in imbalanced PBT flows")
#plt.legend()
plt.xticks(x, labels)
plt.show()
fig.savefig("foo.pdf", bbox_inches='tight')
