# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 23:19:12 2020

@author: Gachon
"""
import simTimer;


class Event:
    def __init__(self, exp, handler, params):
        self.timer = simTimer.Timer(exp);
        self.eventHandler = handler;
        self.params = params;
    def evTimerHandler(self, currTime):
        #print("event occur at ", currTime);
        self.eventHandler(self.params);
    def startEvent(self):
        simTimer.setTimer(self.timer);
        self.timer.setCallback(self.evTimerHandler);
               

class evQueue:
    def __init__(self):
        self.q = [];
    def evEnQ(self, ev):
        self.q.append(ev);
    def evDeQ(self):
        return self.q.pop(0);
    def getQ(self):
        return self.q;
        

eventQueue = 0;

def initEventQ():
    global eventQueue;
    eventQueue = evQueue();

def addEvent(expTime, evHandler, params):
    global eventQueue;
    ev = Event(expTime, evHandler, params);
    eventQueue.evEnQ(ev);
    ev.startEvent();

    


