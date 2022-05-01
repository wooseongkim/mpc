# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 17:43:23 2020

@author: Gachon
"""



#global time (msec)
globalTic = 0;
timeList = 0;


class TimeStamp:
    def __init__(self, d, h, m, s, ms):
        self.date = d;
        self.hour = h;
        self.minute = m;
        self.second = s;
        self.mSecond = ms;

        
class Timer:
    timerId = 0;
    def __init__(self, t_msec):
        self.timer = t_msec;
        Timer.timerId += 1;
        self.timerId = Timer.timerId;
    def setCallback(self, cb):
        self.callback = cb;

class TimerList:
    def __init__(self):
        self.timerQ = [];
    def updateClock(self):
        global globalTic;
        if not self.timerQ:
            return;
        for t in self.timerQ:
            t.timer -= 1;
            if t.timer == 0:
                #print("timer ", t.timerId, " expire");
                t.callback(globalTic);

def initTimeList():
    global timeList;
    timeList = TimerList();
    
def setTimer(timer):
    timeList.timerQ.append(timer);


    