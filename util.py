# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 23:13:17 2020

@author: Gachon
"""
import simTimer
import pcnStat
import math
import operator

bLogging = True
SECOND = 1000;
MINUTE = SECOND * 60;
HOUR = MINUTE * 60;
DATE = HOUR * 24;

f = open("log", mode='wt')


def uDist(c1, c2):
    return math.sqrt(math.pow(c2[0]-c1[0], 2) + math.pow(c2[1]-c1[1], 2))
 
def getDate(tic):
    d=0; h=0; m=0; s=0;
    if tic >= DATE:
        d = int(tic / DATE);
        tic = tic - d*DATE;
    if tic >= HOUR:
        h = int(tic / HOUR);
        tic = tic - h*HOUR;
    if tic >= MINUTE:
        m = int(tic / MINUTE);
        tic = tic - m*MINUTE;
    if tic >= SECOND:
        s = int(tic / SECOND);
        tic = tic - s*SECOND;
    return d, h, m, s, tic;

def getCurTime():
    d, h, m, s, ms = getDate(simTimer.globalTic);
    curTime = "[ "+str(h)+":"+str(m)+":"+str(s)+":"+str(ms)+" ]";
    return curTime;

def getCurTick():
    return simTimer.globalTic;

LOG_TYPE_MANET = 1;
LOG_TYPE_NETWORK = 2;
LOG_MPC_PROTOCOL = 32
LOG_TYPE_PCN_ROUTING = 4;
LOG_TYPE_PCN_PROTOCOL = 8;
LOG_TYPE_PROCESS = 16;
LOG_TYPE_USER_SPEC = 1024

gLogType = LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS;
gLogType = LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_TYPE_MANET | LOG_TYPE_NETWORK | LOG_TYPE_PCN_ROUTING | LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_TYPE_NETWORK | LOG_TYPE_PCN_ROUTING | LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_MPC_PROTOCOL

gNodeFilter = 0;
noFilter = True
def MSG_LOG(logType, msg, nodeId=-1):
    global f
    global gLogType
    global gNodeFilter
    if logType & gLogType:
        if noFilter or gNodeFilter == nodeId:
            d, h, m, s, ms = getDate(simTimer.globalTic);
            curTime = "[ "+str(h)+":"+str(m)+":"+str(s)+":"+str(ms)+" ]";
            print(curTime, msg)
            if bLogging:
                f.write(curTime+msg+"\n")


    
class TransactionNotFound(Exception):
    def __str__(self):
        return "Transaction Not Found";



def getDegree(g):
    ngbMat = {}
    for a in g:
        ngbMat[a] = []
        for b in g:
            if a != b:
                if a[0] in b or a[1] in b:
                    ngbMat[a].append(b)
    degMat ={}
    for v in ngbMat:
        degMat[v] = len(ngbMat[v])
    return degMat

def getNextVpc(q):
    deg = getDegree(q)
    e = min(deg, key=lambda key: deg[key])  # get min degree vpc
    return e

def getSpcSchedule(lspc):
    step = 1
    timeSched = {}
    remainVpc = []
    Qvpc = [v for v in lspc]
    while True:
        timeSched[step] = []
        conflict = []
        e = getNextVpc(Qvpc)
        Qvpc.remove(e)
        while e:
            if e[0] not in conflict and e[1] not in conflict:
                timeSched[step].append(e)
                conflict += [e[0],e[1]]
                #print(timeSched)
            else:
                remainVpc.append(e)
            if Qvpc:
                e = getNextVpc(Qvpc)
                Qvpc.remove(e)
            else:
                break
        if remainVpc:
            Qvpc = [v for v in remainVpc]
            remainVpc = []
            step += 1
        else:
            break

    return timeSched

# n = 8
# edges = [(i,j) for i in range(1, n+1) for j in range(n, 0, -1) if i != j]
# #bi-directional edge
# biEdge = []
# adjMatrix = {}
# for (i, j) in edges:
#     if (i,j) not in biEdge and (j,i) not in biEdge:
#         biEdge.append((i,j))
#
# print(biEdge)
#
# for a in biEdge:
#     adjMatrix[a] = []
#     for b in biEdge:
#         if a != b:
#             if a[0] in b or a[1] in b:
#                 adjMatrix[a].append(b)
#
# print(adjMatrix)
# print(getSpcSchedule(biEdge))