# -*- coding: utf-8 -*-
"""
Created on Thu Jan 21 15:28:02 2021

@author: Gachon
"""
import simEvent;
import random;

class SocketConnect:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.delay = 11;
    def sendMsg(self, msg):
        txDelay = int(random.expovariate(1/self.delay)) +1
        #print("send msg delay ", txDelay)
        simEvent.addEvent(txDelay, self.dst.recvMsg, msg);
    def recvMsg(self, msg):
        self.dst.recvMsg(msg)
        