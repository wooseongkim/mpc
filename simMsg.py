# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 18:40:09 2020

@author: Gachon
"""

MTYPE_CONTROL  = 0;
MTYPE_TRANSACTION = 1;
MTYPE_TRANSACTION_COMP = 2;

MTYPE_CTRL_SECRET = 100;
MTYPE_CTRL_ACK = 101;
MTYPE_CTRL_HELLO = 102;

MTYPE_ROUTING = 500
MTYPE_ROUTING_RREQ = 501
MTYPE_ROUTING_RREP = 502

MTYPE_MPC_ROUND_UPDATE = 600
MTYPE_MPC_ROUND_COMPLETE = 601

# PCN messages over L4 
class Message: 
    def __init__(self, src, dst, mType, seq, payload):
        self.src = src;
        self.dst = dst;
        self.type = mType;
        self.ctrlType = 0;
        self.seq = seq;
        self.target = 0;
        self.payload = payload;
    def setTargetReceiver(self, rcv):
        self.target = rcv;
    def setCtrlMtype(self, t):
        self.ctrlType = t;
    

TransactionId = 0;
TRANS_MODE_STATIC_PBT = 0;
TRANS_MODE_DYNAMIC_PBT = 1;
class Transaction:
    def __init__(self, send, recv, amount, exp):
        global TransactionId
        TransactionId = TransactionId+1
        self.id = TransactionId;
        self.flowId = (send, recv)
        self.send = send; #total balance
        self.recv = recv; #amount for pending transaction
        self.amount = amount;
        self.exp = exp;
        self.status = 'active'
        self.pbtId = 0; #set by payer
        self.startTime = 0;
        self.mode = 0;
        self.path = []

    def getTransInfo(self):
        return self.pbtId, self.send, self.recv, self.amount;

class TransAck:
    def __init__(self, transId, flowId):
        self.transId = transId;
        self.flowId = flowId;
        self.pendTrans = 0;
        self.pendAmount = 0;
        
        
RREQ_ID = 0
class PbtRreq:
    def __init__(self, s, d, a, trId):
        global RREQ_ID
        RREQ_ID += 1
        self.id = RREQ_ID
        self.src = s;
        self.dst = d;
        self.amount = a;
        self.trId = trId
        self.path = []

class PbtRrep:
    def __init__(self, rreqId, s, d, a, trId):
        self.id = rreqId
        self.src = s;
        self.dst = d;
        self.amount = a;
        self.path =[]
        self.capa = 0;
        self.trId = trId

class Hello:
    def __init__(self, _id, peer, trLenTb, trAmTb):
        self.id = _id;
        self.peer = peer;
        self.transLenTable = trLenTb;
        self.transAmountTable = trAmTb;
