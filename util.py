# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 23:13:17 2020

@author: Gachon
"""
import simTimer
import pcnStat
import math

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
LOG_TYPE_PCN_ROUTING = 4;
LOG_TYPE_PCN_PROTOCOL = 8;
LOG_TYPE_PROCESS = 16;
LOG_TYPE_USER_SPEC = 1024

gLogType = LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS;
gLogType = LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_TYPE_MANET | LOG_TYPE_NETWORK | LOG_TYPE_PCN_ROUTING | LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_TYPE_NETWORK | LOG_TYPE_PCN_ROUTING | LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS | LOG_TYPE_USER_SPEC;
gLogType = LOG_TYPE_PCN_PROTOCOL | LOG_TYPE_PROCESS

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
    