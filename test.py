import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
import collections
from matplotlib import rc_file
from matplotlib import rcParams




e1 = 0.2
e2 = 0.1
delta = 0.01
numNodes = 20
# demand = {(1,2):50, (2,1):100, (1,4):50, (4,1):50, (2,4):50, (4,2):100, (1,3):100, (3,1):50,  (2,3):50, (3,2):50, (3,4):100, (4,3):50}
lrate = {'asym':[50, 100], 'sym':[100,100]}


class Topology():
    def __init__(self, numNodes, gType=1, degree=3, tri=0.7, edge=[]):
        self.numNodes = numNodes
        self.edge = edge
        if gType == 0:
            self.graph = nx.Graph()
            self.graph.add_nodes_from(tuple(range(numNodes)))
            self.graph.add_edges_from(edge)
        elif gType == 1:
            self.graph = nx.powerlaw_cluster_graph(numNodes, degree, tri)  # degree=3, triangle=10%
            self.edge = nx.edges(self.graph)
        elif gType == 2:
            self.graph = nx.connected_caveman_graph(5, 4)
            self.edge = nx.edges(self.graph)
#        nx.draw(self.graph, node_size=50)
#        plt.show()
    def updateTopoWithEdge(self, e):
        if e not in self.edge and (e[1], e[0]) not in self.edge:
            self.edge.append(e)
            self.graph.add_edges_from(self.edge)

    def getConnectedPeers(self, n):
        peerIDs = []
        for e in self.edge:
            if n == e[0]:
                peerIDs.append(e[1])
            elif n == e[1]:
                peerIDs.append(e[0])
        return peerIDs



class Params():
    def __init__(self):
        self.adjEdges = {}
        self.lpc = []
        self.lspc = []
        self.demand = {}
        self.ir = {}
        self.partition = []
        self.history = {}
        self.iter = {}
        self.userDemand = 0


# set random PBT demand
def setUserDemand(lrate, para):
    for pc in para.lpc:
        para.demand[pc] = lrate[random.randint(0, len(lrate) - 1)]


# find maximum pc of psp i according to demand
def findMaxPC(mpc, demand):
    _pc = {}
    for (i, j) in mpc:
        if i not in _pc or demand[_pc[i]] < demand[(i, j)]:
            _pc[i] = (i, j)
    # print("max pc list: ", pc.values())
    return _pc


# calculate each MPC payoff
def calCoaltionPayoff(mpc, delta, demand):
    revenue = 0
    cost = 0
    spcRound = int(len(mpc) / 2) - 1
    for pc in mpc:
        revenue += demand[pc]
    revenue = e1 * revenue

    for i, j in findMaxPC(mpc, demand).values():
        if demand[(i, j)] == demand[(j, i)]:
            cost += demand[(i, j)]
        else:
            cost += max(demand[(i, j)], demand[(j, i)])
    cost = e2 * (cost + cost * delta * spcRound)
    return revenue - cost

# calculate total payoff of all mpcs
def calPartitionPayoff(para, delta):
    _totalUtil = 0; _nMpc = 0;
    for p in para.partition:
        if p:
            _nMpc += 1
            _totalUtil += calCoaltionPayoff(p, delta, para.demand)
    return _totalUtil, _totalUtil/_nMpc

# individual payoff
def u_i(spc, mpc, para, delta):
    i, j = spc
    sumIR = 0
    for pc in mpc:
        sumIR += para.ir[pc]
    return para.ir[(i, j)] + para.ir[(j, i)] + 2 * (calCoaltionPayoff(mpc, delta, para.demand) - sumIR) / len(mpc)


# non-cooperative payoff
def calAllIR(delta, para):
    for pc in para.demand:
        util = calCoaltionPayoff([pc], delta, para.demand)
        #print('ir', pc, ':', util)
        para.ir[pc] = util


# initial partitions
def initCoalition(topo, partition):
    for (i, j) in topo.edge:
        partition.append([(i, j), (j, i)])
    #print('initial coalitions: ', len(partition))


def selfishOrder(s_k, s_l, spc, para, delta):
    _to = list(s_l);
    preMpcUtilMargin = 0
    if len(_to) != 0:
        preMpcUtilMargin = calCoaltionPayoff(_to, delta, para.demand)/len(_to)
    oldPayoff = u_i(spc, s_k, para, delta)
    i, j = spc
    _to.extend([(i, j), (j, i)])
    postMpcUtilMargin = calCoaltionPayoff(_to, delta, para.demand)/len(_to)
    newPayoff = u_i(spc, _to, para, delta)
    if newPayoff > oldPayoff and postMpcUtilMargin > preMpcUtilMargin:
        return newPayoff - oldPayoff
    return 0

def paretoOrder(s_k, s_l, spc, para, delta):
    i, j = spc
    s_1 = list(s_l); s_1.extend([(i, j), (j, i)])
    s_2 = list(s_k); s_2.remove((i,j)); s_2.remove((j,i))# s_k \ {i}
    g = selfishOrder(s_k, s_l, spc, para, delta)
    if g > 0:
        if calCoaltionPayoff(s_1, delta, para.demand) > calCoaltionPayoff(s_l, delta, para.demand):
            if calCoaltionPayoff(s_k, delta, para.demand) <= calCoaltionPayoff(s_2, delta, para.demand):
                return g
    return 0
# find max util mpc
def findMaxUtilMpc(pc, para, order_cb, delta):
    s_k = None
    for mpc in para.partition:
        if pc in mpc:
            s_k = mpc
            break
    _maxGain = 0;
    _maxMpc = None;
    for s_l in para.partition:
        if s_k != s_l and s_l not in para.history[pc]:
            g = order_cb(s_k, s_l, pc, para, delta)
            #print('gain: ', g, ' from ', s_k, ' to ', s_l)
            if g > _maxGain:
                _maxGain = g
                _maxMpc = s_l
    if _maxMpc != None:
        para.history[pc].append(_maxMpc)
    return s_k, _maxMpc


def initTopo(numNodes, para, deg=3, conn=0.7):
    topo = Topology(numNodes, 1, deg, conn)
    para.lspc = list(topo.edge)
    for (i, j) in topo.edge:
        para.lpc.extend([(i, j), (j, i)])
    for pc in para.lspc:
        para.history[pc] = []
    for (i, j) in para.lpc:
        if i not in para.adjEdges:
            para.adjEdges[i] = []
        para.adjEdges[i].append(j)
    return topo


def simul(topo, delta, para, fPrefer):
    setUserDemand(lrate[para.userDemand], para)        
    calAllIR(delta, para)
    #    mpc = []
    #    for (i,j) in demand:
    #        mpc.append((i,j))
    #        groupRational = calCoaltionPayoff(mpc, delta)
    #        irSum = sum([ir[pc] for pc in mpc])
    # print('size: {:d} groupRation: {:0.2f} IRsum: {:0.2f} = {:0.2f}'.format(len(mpc), groupRational, irSum, groupRational-irSum))
    # switch algorithm
    initCoalition(topo, para.partition)
    para.iter['nMPC'] = []; para.iter['aUtil'] = []; para.iter['tUtil'] = [];
    NashE = False
    while not NashE:
        numSw = 0
        for (i, j) in para.lspc:
            s_k, s_l = findMaxUtilMpc((i, j), para, fPrefer, delta)
            if s_l != None:
                s_k.remove((i, j));
                s_k.remove((j, i));
                s_l.extend([(i, j), (j, i)])
                # print('sw ', (i,j), ' : ', s_k, s_l )
                n = sum([1 for m in para.partition if m])
                u, avg = calPartitionPayoff(para, delta)
                para.iter['nMPC'].append(n); para.iter['aUtil'].append(avg); para.iter['tUtil'].append(u)
                numSw += 1
        if numSw == 0:
            NashE = True
    return para.partition

####### test procedure ########

e1 = 0.2
e2 = 0.1
delta = 0.1

def genMPC(numNodes):
    para = Params()
    para.userDemand = 'sym'
    t = initTopo(numNodes, para)
    partition = simul(t, delta, para, selfishOrder)
    numMpc = sum([1 for m in para.partition if m])
    return t, partition, para.lpc




#print('--------------- simulation ------------------')
#NUM_EPOCH = 100
#x = []
#y = {}
#y1 = {}
#cdf = {}
#bins ={}
#
#for u in ['asym']:
#    y[u] = []; y1[u] = []
#    x = []
#    for rate in [20, 40, 60, 80, 100]:
#    #for numNodes in [10, 20, 30, 40]:
#        lrate['asym'] = [rate, 100]
#        accNoMPC = 0;
#        accMPCSize = 0;
#        accUtil = 0;
#        for _runs in range(NUM_EPOCH):
#            para = Params()
#            para.userDemand = 'asym'
#            t = initTopo(numNodes, para)
#            partition = simul(t, delta, para, selfishOrder)
#            numMpc = sum([1 for m in para.partition if m])
#            avgSize = sum([len(m) for m in para.partition]) / numMpc
#            # print('total pc: ', len(para.lpc), ' number of MPCs: ', numMpc, ' avgSize: ', avgSize)
#            accNoMPC += numMpc/len(para.partition);
#            accMPCSize += avgSize;
#            tUtil, aUtil = calPartitionPayoff(para, delta)
#            accUtil += tUtil - sum(list(para.ir.values()))
#        y[u].append(accUtil / NUM_EPOCH);
#        y1[u].append(accMPCSize / NUM_EPOCH)

# e1 = 0.2
# e2 = 0.2
# delta = 0.1
#
# y = []; y1 = []
# para = Params()
# t = initTopo(numNodes, para)
# #partition = simul(t, delta, para, selfishOrder)
# partition = simul(t, delta, para, paretoOrder)
# numMpc = sum([1 for m in para.partition if m])
# avgSize = sum([len(m) for m in para.partition]) / numMpc
# y = para.iter['nMPC']
# y1 = para.iter['aUtil']
# y2 = para.iter['tUtil']
# x = [i for i in range(1, len(y)+1)]

#
################## plot configuration ########################
## rcParams dict
#rcParams['axes.labelsize'] = 10
#rcParams['xtick.labelsize'] = 10
#rcParams['ytick.labelsize'] = 10
#rcParams['legend.fontsize'] = 9
#rcParams['font.family'] = 'DeJavu Serif'
#rcParams['font.serif'] = ['Computer Modern Roman']
#rcParams['text.usetex'] = True
#rcParams['figure.figsize'] = 2.5, 2.5
#
##
#
##labels = ['0.1', '0.2', '0.3', '0.4', '0.5']
##labels = ['1', '5', '10', '15', '20']
#labels = ['20', '40', '60','80', '100']
#x = np.arange(len(labels))
#
#
#width = 0.34
#fig, ax1 = plt.subplots()
##rects1 = ax1.bar(x - width/2, y['sym'], width, label='asymmetry')
#rects2 = ax1.bar(x, y['asym'], width, label='asymmetry')
##rects3 = ax1.bar(x + width, y[0.1], width, label='0.01')
#
#
#
#ax1.set_xticks(x, labels)
##ax1.legend(loc='lower right')
##ax1.legend(loc='upper center')
#
##ax1.bar_label(rects1, padding=3)
##ax1.bar_label(rects2, padding=3)
#
#
##ax1.plot(x, y[3], 'r-', marker='o', label="3")
##ax1.plot(x, y[5], 'b--', marker='x', label="5")
##ax1.plot(x, y[7], 'k:', marker='+', label="7")
##ax1.plot(x, y[0.4], 'c-.', marker="v", label="0.4")
##ax1.plot(x, y[0.5], 'm--', marker='s', label="0.5")
##ax1.legend(loc='center right')
#
#
##labels = ['10', '20', '30','40']
##ax1.set_xticks(x, labels)
#
#
##ax1.set_ylabel("Average number of MPCs")
#ax1.set_ylabel("Total marginal payoff")
#ax1.set_xlabel("User demands")
#fig.tight_layout()
## #
## #
## ax2 = ax1.twinx()
## # l3 = ax2.plot(x,y1, label="MPC size", marker='D', s=50)
## l2 = ax2.plot(x, y1[0.1], 'b-+', label="MPC size")
## #ax2.plot(x, y2, 'b--', label="Partition utility")
## ax2.set_ylabel("Average MPC size")
## ax2.legend(loc='lower right')
#
#
## plt.ylabel("Transactions")
## plt.xlabel("Payment interval")
## plt.title("PCN throughput in imbalanced PBT flows")
## plt.legend()
#plt.xticks(x, labels)
#plt.show()
#
#fig.savefig("foo.pdf", bbox_inches='tight')
