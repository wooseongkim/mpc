# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 14:06:57 2020

@author: Gachon
"""
from util import *;
import simMsg;
import routing;
import simEvent;
import pcnStat;
import sys;
import copy;
import transport;


keepAliveBoot = False
class MPC:
    def __init__(self, _id, pspList, maxDepo):
        self.mpcId = _id
        self.spcState = {}
        self.locked = {}
        for i in pspList:
            self.spcState[i] = maxDepo 
            self.locked[i] = 0
            
        self.round = 0
        self.lockedTrans = [];
        
    def lock(self, i, trans):
        self.lockedTrans.append(trans)
        self.spcState[i] -= trans.amount;
        self.locked[i] += trans.amount;

        
class PayChannel:
    def __init__(self, cp, depo, onchain):
        self.id = cp;
        self.initBal = depo;
        self.curBal = depo;
        self.locked = 0;
        self.capa = depo;
        self.pendTrans = [];
        self.lockedTrans = [];
        self.rcvLockedTrans = [];
        self.sentSecret = {}
        self.lastSeenTransTS = 0;
        self.incomingTransRate = 1;
        self.onChain = onchain;
        self.bCheckDeadline = False;
        self.bMPC = False
    def isPayable(self, amount):
        #pbt join decision here
        return amount <= self.curBal;
    def pendTrans(self, trans):
        self.pendTrans.append(trans); 
    
    def checkExpiredTrans(self):
        #rollback
        for t in self.lockedTrans:
            if t.exp - getCurTick() < 0:
                self.locked -= t.amount;
                self.curBal += t.amount;                
                MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[channel "+str(self.id)+"] rollback +/-$" + str(t.amount) + " cancel PBT " + str(t.pbtId))
                pcnStat.gStat.cancel.add(t.pbtId)
                self.lockedTrans.remove(t)                 

        #on-chain access
        for t in self.rcvLockedTrans:
            if t.exp - getCurTick() < 0 and self.sentSecret[t] == True:
                pcnStat.gStat.outage +=1
                self.onChain(self.id[0], self.id[1], t.pbtId)
                
    def addRcvLockTrans(self, trans):
        self.rcvLockedTrans.append(trans);
        MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[channel "+str(self.id)+"] recvLock -$" + str(trans.amount) +" PBT "+str(trans.pbtId))
        self.sentSecret[trans] = False
        
    def lock(self, trans):
        self.lockedTrans.append(trans)
        self.curBal -= trans.amount;
        self.locked += trans.amount;
    def unlock(self, pbtId):
        try:
            for t in self.lockedTrans:
                if t.pbtId == pbtId:
                    self.locked -= t.amount;
                    MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[channel "+str(self.id)+"] unlock -$" + str(t.amount) +" PBT "+str(pbtId))
                    self.lockedTrans.remove(t)                    
        except TransactionNotFound as e:
            print(e," :unlock")
                #users are honest to forward Secret
        for t in self.rcvLockedTrans:
                if t.pbtId == pbtId:
                    self.sentSecret[t] = True
                    
    def reImburse(self, pbtId):
        try:
            for t in self.rcvLockedTrans:
                if t.pbtId == pbtId:
                    self.curBal += t.amount;
                    MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[channel "+str(self.id)+"] reimburse +$" + str(t.amount)+" PBT "+str(pbtId))
                    self.rcvLockedTrans.remove(t)
                    print("[reimburse "+str(self.id)+"]", t.pbtId)
                    return t.amount;
            raise TransactionNotFound;
        except TransactionNotFound as e:
            print(e," :reimburse ", pbtId)
            sys.exit()
     
    def getExDelay(self, amount):        
        return amount/self.capa;
    def getRcvTransByPbtId(self, pbtId):
        try:
            for t in self.rcvLockedTrans:
                if t.pbtId == pbtId:
                    return t;
            raise TransactionNotFound;
        except TransactionNotFound as e:
            print(e)

NODE_STATUS_INIT = 0
NODE_STATUS_RUNNING = 1 
NODE_STATUS_SLEEP = 2       

class Node:
    def __init__(self, id):
        self.id = id
        self.pcnLinks ={}
        self.pbtInfo = {} # (pre, next) of pbt
        self.channels = {}
        self.pf = []
        self.rcvMsgBuffer = [] #recvMsgQueue
        self.msgSeq = 0;
        self.myPay = []; #as a payer queue
        self.myUnpaid = []; #unpaid pbt list of mine
        self.rt = routing.PCNRoutingTable();
        self.ngbs = routing.PCNNeighborTable();
        self.rt.mode = routing.PROACTIVE_ROUTING; #routing mode setting
        self.proRtActivated = False
        self.pbtFlow = []
        self.recvTransBuffer = []; #transactions queue for QLB 
        self.state = NODE_STATUS_INIT 
        self.seenRREQ = []
        self.seenRREP = []

    def setBlockchainAccess(self, onChain):
        self.blockchain = onChain
        
    def createSockPayCh(self, peer, iDepo): #create bi-directional pc
        MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[node "+str(self.id)+"] open PC b/w [" + str(self.id) +","+str(peer.id)+"]"  )
        routing.gTopo.updateTopoWithEdge((self.id, peer.id))
        self.pcnLinks[peer.id] = transport.SocketConnect(self, peer);
        self.openChannel(peer.id, iDepo) #1000 usd
        
        peer.pcnLinks[self.id] = transport.SocketConnect(peer, self);
        peer.openChannel(self.id, iDepo) #1000 usd            
    
    def setLowerProto(self, l4):
        self.L4proto = l4
    def openChannel(self, peer, depo):
        self.channels[peer] = PayChannel((self.id, peer), depo, self.blockchain);
        
    def getAllPendTrans(self):
        numTrans = 0;
        for c in self.channels.values():
            numTrans += len(c.pendTrans)
        return numTrans;

    def getPendTransAmountAllFlow(self):
        flowTrans = {};
        flowAmount = {};        
        for c in self.channels.values():
            for t in c.pendTrans:
                if t.flowId not in flowTrans:
                    flowTrans[t.flowId] = 0
                    flowAmount[t.flowId] = 0                   
                flowTrans[t.flowId] += 1;
                flowAmount[t.flowId] += t.amount;
        return flowTrans, flowAmount;
    
    def getPendTransAmountPerFlow(self, flowId):
        flowTrans = 0;
        flowAmount = 0;        
        for c in self.channels.values():
            for t in c.pendTrans:
                if t.flowId == flowId:
                    flowTrans += 1;
                    flowAmount += t.amount;
        return flowTrans, flowAmount;
    
    def getPendTransAmountPerNgb(self, ngb, flowId):
        flowTrans = 0;
        flowAmount = 0;
        for t in self.channels[ngb].pendTrans:
            if t.flowId == flowId:
                flowTrans += 1;
                flowAmount += t.amount;
        return flowTrans, flowAmount;
    
    def getIncomingRateOnChannel(self, peer, amount):
        timeInt = (getCurTick() - self.channels[peer].lastSeenTransTS)/SECOND;
        if timeInt != 0:
            newRate = amount/timeInt;
            self.channels[peer].incomingTransRate = 0.7 * self.channels[peer].incomingTransRate + 0.3 * newRate;
            self.channels[peer].lastSeenTransTS = getCurTick()
        return self.channels[peer].incomingTransRate;
    
    def periodicHello(self, param):
        self.sendHello()
        simEvent.addEvent(param, self.periodicHello, param)
        
    def proactiveRouting(self, param):
        self.sendRreq(param[0], param[1], param[2])
        simEvent.addEvent(param[2], self.proactiveRouting, param)
        
    def onDemandRouting(self, param):
        self.sendRreq(param[0], param[1], param[2])
    
    def sendHello(self):
        trLenTb, trAmTb = self.getPendTransAmountAllFlow()
        #print('send hello', [n for n in self.pcnLinks])
        for n in self.pcnLinks:
            hello = simMsg.Hello(self.id, n, trLenTb, trAmTb)
            self.msgSeq += 1;
            helloMsg = simMsg.Message(self.id, n, simMsg.MTYPE_CONTROL, self.msgSeq, hello);
            helloMsg.setCtrlMtype(simMsg.MTYPE_CTRL_HELLO);
            self.sendMsg(helloMsg) 
            pcnStat.gStat.hello += 1;
        
    def sendRreq(self, dest, amount, transId):
        nexts = routing.getNextHops(self.id, dest, 0)
        for n in nexts:
            self.msgSeq += 1;
            rreq = simMsg.PbtRreq(self.id, dest, amount, transId)
            rreq.path.append(self.id)
            rreqMsg = simMsg.Message(self.id, n, simMsg.MTYPE_ROUTING_RREQ, self.msgSeq, rreq);
            MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] initiate RREQ to "+str(n), self.id)
            self.sendMsg(rreqMsg) 
            pcnStat.gStat.rreq += 1;
    
    def sendRrep(self, rreq):        
        prev = self.rt.recvRreqFrom[rreq.id];
        self.msgSeq += 1;
        rrep = simMsg.PbtRrep(rreq.id, rreq.src, rreq.dst, rreq.amount, rreq.trId)
        rrep.path.insert(0, self.id)
        rrep.capa = 10000000; #big number for init value
        rrepMsg = simMsg.Message(self.id, prev, simMsg.MTYPE_ROUTING_RREP, self.msgSeq, rrep);
        MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] initiate RREP to "+str(prev), self.id)
        self.sendMsg(rrepMsg) 
        pcnStat.gStat.rrep += 1;
        
    def relayRreq(self, rreq):
        nexts = routing.getNextHops(self.id, rreq.dst, 0)
        for n in nexts:
            if n not in rreq.path: # not reverse flooding
                if self.channels[n].isPayable(rreq.amount):
                    self.msgSeq += 1;
                    rreq.path.append(self.id)
                    rreqMsg = simMsg.Message(self.id, n, simMsg.MTYPE_ROUTING_RREQ, self.msgSeq, rreq);
                    MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] relay RREQ to "+str(n), self.id)
                    self.sendMsg(rreqMsg)
                    pcnStat.gStat.rreq += 1;
            
    def relayRrep(self, rcvRrep):
        prev = self.rt.recvRreqFrom[rcvRrep.id];
        rrep = simMsg.PbtRrep(rcvRrep.id, rcvRrep.src, rcvRrep.dst, rcvRrep.amount, rcvRrep.trId)
        rrep.path = rcvRrep.path
        if self.channels[rrep.path[0]].curBal < rcvRrep.capa:
            rrep.capa = self.channels[rrep.path[0]].curBal;
        rrep.path.insert(0, self.id)
        rrepMsg = simMsg.Message(self.id, prev, simMsg.MTYPE_ROUTING_RREP, self.msgSeq, rrep);
        MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] relay RREP to "+str(prev), self.id)
        self.sendMsg(rrepMsg) 
        pcnStat.gStat.rrep += 1;
        
    def handleRreq(self, msg):
        MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] recv RREQ["+str(msg.payload.src)+"--"+str(msg.payload.dst)+ "] from "+str(msg.src), self.id)
        if msg.payload.id not in self.seenRREQ: # new RREQ
            self.rt.recvRreqFrom[msg.payload.id] = msg.src;
            msg.payload.path.append(self.id);
            self.rt.updateEntry(msg.payload.src, msg.src, len(msg.payload.path), 0, 0); #capa & delay is not set yet        
            self.ngbs.updateEntry(msg.src)
            self.seenRREQ.append(msg.payload.id)
            if msg.payload.dst == self.id:
                self.sendRrep(msg.payload);
            else:
                self.relayRreq(msg.payload)
    
    def handleRrep(self, msg):
        MSG_LOG(LOG_TYPE_NETWORK, "[node "+str(self.id)+"] recv RREP from "+str(msg.src), self.id)
        if msg.payload.id not in self.seenRREP: #new RREP
            self.seenRREP.append(msg.payload.id)
            self.ngbs.updateEntry(msg.src)
            if msg.payload.src == self.id:        
                if self.rt.mode == routing.PROACTIVE_ROUTING:
                    #for source routing
                    self.rt.updatePbtEntry(msg.payload.dst, msg.payload.path, msg.payload.capa, getCurTick() +  1*SECOND)
                    MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] find path "+ str(msg.payload.path) + "----" +str(self.rt.pbtTable[msg.payload.dst].path), self.id)
                    #per-hop routing
                    self.rt.updateEntry(msg.payload.dst, msg.src, len(msg.payload.path), msg.payload.capa, 0); #delay is not set yet
                elif self.rt.mode == routing.ONDEMAND_ROUTING:
                    tr = self.dePayQ(msg.payload.trId)
                    if not tr:
                        return; #multiple rrep can arrive here
                    tr.mode = simMsg.TRANS_MODE_STATIC_PBT;
                    tr.path = copy.deepcopy(msg.payload.path);
                    trMsg = simMsg.Message(self.id, tr.path.pop(0), 1, self.msgSeq, tr);
                    self.sendMsg(trMsg) 
                    pcnStat.gStat.numPayment += 1;            
            else:
                self.relayRrep(msg.payload);
    
    def myPayIds(self):
        payIds = []
        for p in self.myPay:
            payIds.append(p.pbtId)
        return payIds;
    
    def dePayQ(self, payId):
        pay = 0;
        if payId in self.myPayIds():
            for p in self.myPay:
                if p.pbtId == payId:
                    pay = p;
                    self.myPay.remove(p)
                    MSG_LOG(LOG_TYPE_PROCESS, "[payer "+str(self.id)+"] dequeue trans: " + str(len(self.myPay)), self.id)
                    return pay        
                
    def selectPayChannel(self, neighbors, trans):
        linkWeight = {}
        _V = 1
        for n in neighbors:
            qTr, qAm = self.getPendTransAmountPerNgb(n, trans.flowId)
            nTr, nAm = self.ngbs.lookupPendTrans(n, trans.flowId)
            #weight calculation Delta_Q - V*pentalty
            linkWeight[n] = (qAm - nAm) - _V * 1/self.getIncomingRateOnChannel(n, 0)
        _maxVal = max(linkWeight.values())
        MSG_LOG(LOG_TYPE_USER_SPEC, "[node "+str(self.id)+"] QBL weight " + str(linkWeight), self.id)
        for k, v in linkWeight.items():
            if v == _maxVal:
                return k;
                  
    def payTo(self, payer, payee, amount, nextHop, deadline, routingPeriod = 10*SECOND):
        if (payer, payee) not in self.pbtFlow:
            self.pbtFlow.append((payer, payee))
            
        tr = simMsg.Transaction(payer, payee, amount, deadline);
        tr.pbtId = tr.id;
        tr.startTime = getCurTick();
        #transaction mode pbt (static) vs. per-hop (QBL) (dyanmic)
        tr.mode = simMsg.TRANS_MODE_STATIC_PBT;
        #tr.mode = simMsg.TRANS_MODE_DYNAMIC_PBT
        

        self.myPay.append(tr);
        self.myUnpaid.append(tr.pbtId) #payment completion check
        MSG_LOG(LOG_TYPE_PROCESS, "[payer "+str(self.id)+"] enqueue trans: " + str(len(self.myPay)), self.id)
        
        if payee not in self.rt.pbtTable:    # proactive routing for a new payee        
            if self.rt.mode == routing.PROACTIVE_ROUTING and not self.proRtActivated :
                self.proRtActivated = True
                self.proactiveRouting((payee, amount, routingPeriod))
                     
    
    def blockchainAccess(self):
        pcnStat.gStat.outage += 1;
        
    def sendLock(self, trans, deadline, nextHop):
        tr = simMsg.Transaction(trans.send, trans.recv, trans.amount, deadline);        
        tr.pbtId = trans.pbtId;
        tr.startTime = trans.startTime;
        tr.path = trans.path;
        tr.mode = trans.mode;
        self.msgSeq += 1;
        trMsg = simMsg.Message(self.id, nextHop, 1, self.msgSeq, tr);
        self.sendMsg(trMsg)  
        
    def sendSecret(self, peer, pbtId):
        cm = simMsg.Message(self.id, peer, simMsg.MTYPE_CONTROL, self.msgSeq, pbtId);
        cm.setCtrlMtype(simMsg.MTYPE_CTRL_SECRET);
        self.sendMsg(cm);
    
    def sendUnlock(self, peer, pbtId):
        newTrans = simMsg.Message(self.id, peer, simMsg.MTYPE_TRANSACTION_COMP, self.msgSeq, pbtId);
        self.sendMsg(newTrans);
        
    def sendMsg(self, msg):
        MSG_LOG(LOG_TYPE_NETWORK, "[node "+str(self.id)+"] send msg " + str(msg.type) + ','+ str(msg.ctrlType) + " to "+str(msg.dst), self.id)
        self.pcnLinks[msg.dst].sendMsg(msg);
    
    def recvMsg(self, msg):
        MSG_LOG(LOG_TYPE_NETWORK, "[node "+str(self.id)+"] recv msg " + str(msg.type) + ','+ str(msg.ctrlType) + " from "+str(msg.src), self.id)
        self.rcvMsgBuffer.append(msg);
    
    #periodic process   
    def doProcess(self, period=10*SECOND):
        if self.state == NODE_STATUS_INIT and keepAliveBoot:  #node initial processes
            self.periodicHello(period)
            self.state = NODE_STATUS_RUNNING
        #self.rt.obsoleteEntries(); #routing table update
        #process pending transaction on payer's Q
        if self.myPay:
            if self.rt.mode == routing.ONDEMAND_ROUTING and self.rt.onDemandTimer < getCurTick():
                self.onDemandRouting((self.myPay[0].recv, self.myPay[0].amount, self.myPay[0].pbtId))
                self.rt.onDemandTimer += 0.1* SECOND; #100 ms waiting for next rreq
            
            elif self.rt.mode == routing.PROACTIVE_ROUTING:
                for tr in self.myPay:
                    if tr:
                        if tr.mode == simMsg.TRANS_MODE_STATIC_PBT:                    
                            if tr.recv in self.rt.pbtTable:
                                tr.path = copy.deepcopy(self.rt.pbtTable[tr.recv].path);     
                                MSG_LOG(LOG_TYPE_PROCESS, "[node "+str(self.id)+"] dequeue payment to path "+ str(self.rt.pbtTable[tr.recv].path) +" PBT: "+str(tr.pbtId), self.id)
                                nextHop = tr.path.pop(0)
                                self.channels[nextHop].lock(tr);
                                #for payer, unlimited balance is given
                                self.channels[nextHop].curBal += tr.amount;
                                trMsg = simMsg.Message(self.id, nextHop, 1, self.msgSeq, tr);
                                self.sendMsg(trMsg) 
                                pcnStat.gStat.numPayment += 1;
                                self.myPay.remove(tr);
                                
                        elif tr.mode == simMsg.TRANS_MODE_DYNAMIC_PBT: #QBL fowarding
                            ngbs = self.rt.getNextHops(tr.recv)
                            if not ngbs: #no route info
                                continue;    
                            nh = self.selectPayChannel(ngbs, tr)
                            self.channels[nh].lock(tr);
                            self.channels[nh].curBal += tr.amount;
                            self.msgSeq += 1;
                            trMsg = simMsg.Message(self.id, nh, 1, self.msgSeq, tr);
                            self.sendMsg(trMsg) 
                            pcnStat.gStat.numPayment += 1;
                            self.myPay.remove(tr);
                            
        #process pending transaction on channels   
        for c in self.channels.values():
            c.checkExpiredTrans()
            if c.pendTrans:
                #if getCurTick() % 1000 == 0:
                #    MSG_LOG(LOG_TYPE_USER_SPEC, "[node "+str(self.id)+"] process pending trans to " + str(c.id[1]) + " Queue length " + str(len(c.pendTrans)))
                if c.id not in pcnStat.gStat.queuedTrans:
                    pcnStat.gStat.queuedTrans[c.id] = 0
                    pcnStat.gStat.maxTxQLen[c.id] = 0

                pcnStat.gStat.queuedTrans[c.id] = pcnStat.gStat.queuedTrans[c.id] * 0.9 + len(c.pendTrans) * 0.1
                pcnStat.gStat.maxTxQLen[c.id] = max(pcnStat.gStat.maxTxQLen[c.id], len(c.pendTrans))
                for t in c.pendTrans:
                    pbtId, payer, payee, amount = t.getTransInfo();
                    if c.isPayable(amount):
                        c.lock(t);
                        if t.mode == simMsg.TRANS_MODE_STATIC_PBT:
                            t.path.pop(0)
                        self.sendLock(t, getCurTick() + 3*SECOND, c.id[1]);
                        c.pendTrans.remove(t)
                    elif t.exp < getCurTick():
                        MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[node "+str(self.id)+"] drops expired PBT " + str(t.pbtId) )
                        c.pendTrans.remove(t)  
                        del self.pbtInfo[pbtId];
                    
        if self.rcvMsgBuffer:
            msg = self.rcvMsgBuffer.pop(0);
            if msg.type == simMsg.MTYPE_CONTROL:
                #MSG_LOG(LOG_TYPE_PROCESS, "[node "+str(self.id)+"] do ctrl process")
                if msg.ctrlType == simMsg.MTYPE_CTRL_SECRET:
                    self.channels[msg.src].unlock(msg.payload)
                    self.sendUnlock(msg.src, msg.payload)
                    #print("node ", self.id, " ", msg.payload, " ", self.pbtInfo);                                       
                    if msg.payload in self.myUnpaid:
                        self.myUnpaid.remove(msg.payload)
                        pcnStat.gStat.numTransaction += 1;
                        pcnStat.gStat.succPbt.add(msg.payload)
                    else:
                        self.sendSecret(self.pbtInfo[msg.payload][0], msg.payload)
                elif msg.ctrlType == simMsg.MTYPE_CTRL_ACK:
                    # maybe, ack for transaction will be handled later, msg.payload.transId
                    self.ngbs.updateEntry(msg.src, msg.payload.flowId, msg.payload.pendTrans, msg.payload.pendAmount)
                elif msg.ctrlType == simMsg.MTYPE_CTRL_HELLO:
                    MSG_LOG(LOG_TYPE_PCN_ROUTING, "[node "+str(self.id)+"] recv HELLO from " + str(msg.src) + " flows: "+str(msg.payload.transLenTable), self.id)
                    pcnStat.gStat.recvhello += 1;
                    for f in msg.payload.transLenTable:
                        self.ngbs.updateEntry(msg.payload.id, f, msg.payload.transLenTable[f], msg.payload.transAmountTable[f])
                        
                        
            #receive transactions
            elif msg.type == simMsg.MTYPE_TRANSACTION: 
                #MSG_LOG(LOG_TYPE_PROCESS, "[node "+str(self.id)+"] do trans process")
                pbtId, payer, payee, amount = msg.payload.getTransInfo();                
                # penalty function update for incoming transaction rate
                newRate = self.getIncomingRateOnChannel(msg.src, amount)
                
                if payee == self.id:
                    self.channels[msg.src].addRcvLockTrans(msg.payload);
                    self.sendSecret(msg.src, pbtId)
                    #pcnStat.gStat.numTransaction += 1; #think the case PSP doesn't unlock later
                    pcnStat.gStat.avgPayDelay[(msg.payload.send, msg.payload.recv)] = pcnStat.gStat.avgPayDelay[(msg.payload.send, msg.payload.recv)] * 0.8 + (getCurTick() - msg.payload.startTime) * 0.2;
                    if not pcnStat.gStat.minPayDelay[(msg.payload.send, msg.payload.recv)]:
                        pcnStat.gStat.minPayDelay[(msg.payload.send, msg.payload.recv)] = pcnStat.gStat.avgPayDelay[(msg.payload.send, msg.payload.recv)]
                    pcnStat.gStat.minPayDelay[(msg.payload.send, msg.payload.recv)] = min(pcnStat.gStat.minPayDelay[(msg.payload.send, msg.payload.recv)],(getCurTick() - msg.payload.startTime))                        
                    pcnStat.gStat.maxPayDelay[(msg.payload.send, msg.payload.recv)] = max(pcnStat.gStat.maxPayDelay[(msg.payload.send, msg.payload.recv)],(getCurTick() - msg.payload.startTime))
                    MSG_LOG(LOG_TYPE_USER_SPEC, "[node "+str(self.id)+"] latency " + str(getCurTick() - msg.payload.startTime), self.id)
                else:
                    if msg.payload.mode == simMsg.TRANS_MODE_STATIC_PBT:                    
                        ##if want to join in flow, then generate TR; otherwise, drop
                        nh = msg.payload.path[0];   
                        # pending transactio Q
                        self.channels[nh].pendTrans.append(msg.payload)
                        MSG_LOG(LOG_TYPE_PROCESS, "[node "+str(self.id)+"] queue static trans to " + str(nh) + " Q-size: "+str(len(self.channels[nh].pendTrans)), self.id)
                        self.channels[msg.src].addRcvLockTrans(msg.payload); 
                        self.pbtInfo[pbtId] = (msg.src, nh);                            
                        #pcnStat.gStat.rejectPbt += 1;
                    elif msg.payload.mode == simMsg.TRANS_MODE_DYNAMIC_PBT: #oppotunistic forwarding 
                        ack = simMsg.TransAck(msg.payload.id, msg.payload.flowId)
                        ack.pendTrans, ack.pendAmount = self.getPendTransAmountPerFlow(msg.payload.flowId)
                        self.msgSeq += 1;
                        ackMsg = simMsg.Message(self.id, msg.src, simMsg.MTYPE_CONTROL, self.msgSeq, ack);
                        ackMsg.setCtrlMtype(simMsg.MTYPE_CTRL_ACK);
                        self.sendMsg(ackMsg)
                        #forward transactions based on QLB                        
                        ngbs = self.rt.getNextHops(msg.payload.recv)
                        if not ngbs: #no route info, so put it back end (transaction schedule needed)
                            self.rcvMsgBuffer.append(msg)                            
                        else:
                            MSG_LOG(LOG_TYPE_USER_SPEC, "[node "+str(self.id)+"] QBL neighbors " + str(ngbs) + " for a dest "+str(msg.payload.recv), self.id)
                            nh = self.selectPayChannel(ngbs, msg.payload)
                            self.channels[nh].pendTrans.append(msg.payload)
                            MSG_LOG(LOG_TYPE_PROCESS, "[node "+str(self.id)+"] queue dynamic trans to " + str(nh) + " Q-size: "+str(len(self.channels[nh].pendTrans)), self.id)
                            self.channels[msg.src].addRcvLockTrans(msg.payload); 
                            self.pbtInfo[pbtId] = (msg.src, nh); 
                            
                            
            elif msg.type == simMsg.MTYPE_TRANSACTION_COMP:
                amount = self.channels[msg.src].reImburse(msg.payload)
                MSG_LOG(LOG_TYPE_PCN_PROTOCOL, "[node "+str(self.id)+"] reimburse $" + str(amount) + " from " + str(msg.src) + "=> "+str(self.channels[msg.src].curBal), self.id)
                pcnStat.gStat.incentive[self.id] += 1;
                if msg.payload in self.pbtInfo:
                    del self.pbtInfo[msg.payload];
                    
            elif msg.type == simMsg.MTYPE_ROUTING_RREQ:
                self.handleRreq(msg);
            elif msg.type == simMsg.MTYPE_ROUTING_RREP:
                self.handleRrep(msg);
        