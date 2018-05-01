from HBVss2Dealer import *
from HBVss2Recipient import *
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
    offset = -1
    t = 1
    n = 3*t + 1
    seed = None
    symmetric = False
    if not symmetric:
        group = PairingGroup('BN254')
        #group = PairingGroup('MNT159')
    else:
        #group = PairingGroup('SS1536')
        group = PairingGroup('SS512')
    
    pk = [group.random(G1), group.random(G1)]
    participantids = []
    for i in range(n):
        participantids.append(i+1+offset)
    print participantids
    dealerid = n
    sends, recvs = simple_router(participantids + [dealerid], seed=seed)
    threads = []
    participantpubkeys = {}
    participantprivkeys = {}
    g = group.random(ZR)
    for j in participantids + [dealerid]:
        participantprivkeys[j] = group.random(ZR)
        participantpubkeys[j] = g ** participantprivkeys[j]
    time2 = os.times()
    #Initialize Players
    thread = Greenlet(HBVss2Dealer, k=n, t=t,  secret=42, pk=pk, sk=participantprivkeys[dealerid], participantids=participantids, participantkeys=participantpubkeys, group=group, symflag=symmetric, recv_function = recvs[dealerid], send_function=sends[dealerid])
    thread.start()
    threads.append(thread)

    for i in range(n):
        thread = Greenlet(HBVss2Recipient, k=n, t=t, nodeid=i+1+offset, sk=participantprivkeys[i], pk=pk, participantids=participantids, participantkeys=participantpubkeys, group=group, symflag=symmetric, send_function=sends[i+1+offset], recv_function=recvs[i+1+offset], reconstruction=False)
        thread.start()
        threads.append(thread)

    gevent.joinall(threads)
    print "Elapsed Time: " + str(os.times()[4] - time2[4])
    #print threads[1].get().get_share()
    #print threads[1].get().secret


if __name__ == "__main__":
    debug = True
    main()
