from VssDealer import *
from VssRecipient import *
import os
import gevent
from gevent import Greenlet
from gevent.queue import Queue

def simple_router(participantids, maxdelay=0.01, seed=None):
    """Builds a set of connected channels, with random delay
    @return (receives, sends)
    """
    rnd = random.Random(seed)
    #if seed is not None: print 'ROUTER SEED: %f' % (seed,)
    
    queues = {}
    for _ in participantids:
        queues[_] = Queue()
    
    def makeSend(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            #print 'SEND %8s [%2d -> %2d] %.2f' % (o[0], i, j, delay)
            gevent.spawn_later(delay, queues[j].put, (i,o))
            #queues[j].put((i, o))
        return _send
    
    def makeRecv(j):
        def _recv():
            (i,o) = queues[j].get()
            #print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i,o)
        return _recv
    
    sends = {}
    receives = {}
    for i in participantids:
        sends[i] = makeSend(i)
        receives[i] = makeRecv(i)    
    return (sends, receives)

def main():
    offset = 69
    t = 4
    n = 13
    seed = None
    symmetric = False
    if not symmetric:
        #group = PairingGroup('BN256')
        group = PairingGroup('MNT159')
        alpha = group.random(ZR, seed=seed)
        alpha2 = group.random(ZR, seed=seed)
        pkg = group.random(G1, seed=seed)
        pkghat = group.random(G2, seed=seed)
        pkh = group.random(G1, seed=seed)
        pk2g = group.random(G1, seed=seed)
        pk2ghat = group.random(G2, seed=seed)
        pk2h = group.random(G1, seed=seed)
        pk = []
        pk2 = []
        for i in range(t+1):
            pk.append(pkg**(alpha**i))
        for i in range(2):
            pk.append(pkghat**(alpha**i))
        for i in range(t+1):
            pk.append(pkh**(alpha**i))
        for i in range(n+1):
            pk2.append(pk2g**(alpha2**i))
        for i in range(2):
            pk2.append(pk2ghat**(alpha2**i))
        for i in range(n+1):
            pk2.append(pk2h**(alpha2**i))
    else:
        #group = PairingGroup('SS1536')
        group = PairingGroup('SS512')
        alpha = group.random(ZR, seed=seed)
        alpha2 = group.random(ZR, seed=seed)
        pkg = group.random(G1, seed=seed)
        pkg2 = group.random(G1, seed=seed)
        pkh = group.random(G1, seed=seed)
        pkh2 = group.random(G1, seed=seed)
        pk = []
        pk2 = []
        for i in range(t+1):
            pk.append(pkg**(alpha**i))
        for i in range(t+1):
            pk.append(pkh**(alpha**i))
        for i in range(n+1):
            pk2.append(pkg2**(alpha2**i))
        for i in range(n+1):
            pk2.append(pkh2**(alpha2**i))
    #Preprocessing to speed up exponentiation
    for item in pk:
        item.initPP()
    for item in pk2:
        item.initPP()
    
    participantids = []
    for i in range(n):
        participantids.append(i+1+offset)
    dealerid = 4242
    sends, recvs = simple_router(participantids + [dealerid], seed=seed)
    threads = []

    #Initialize Players
    thread = Greenlet(VssDealer, k=n, t=t,  secret=[42,69,420,11111,1717], pk=pk, pk2=pk2, participantids=participantids, group=group, symflag=symmetric, send_function=sends[dealerid])
    thread.start()
    threads.append(thread)

    for i in range(n):
        thread = Greenlet(VssRecipient, k=n, t=t, nodeid=i+1+offset, pk=pk, pk2=pk2, participantids=participantids, group=group, symflag=symmetric, send_function=sends[i+1+offset], recv_function=recvs[i+1+offset])
        thread.start()
        threads.append(thread)

    gevent.joinall(threads)


if __name__ == "__main__":
    debug = True
    main()
