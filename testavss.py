from VssDealer import *
from VssRecipient import *
import os

def main():
    timetotal = os.times() 
    time = os.times()
    offset = 69
    t = 4
    k = 13
    seed = None
    symmetric = True
    if not symmetric:
        group = PairingGroup('BN256')
        #group = PairingGroup('MNT160')
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
        for i in range(k+1):
            pk2.append(pk2g**(alpha2**i))
        for i in range(2):
            pk2.append(pk2ghat**(alpha2**i))
        for i in range(k+1):
            pk2.append(pk2h**(alpha2**i))
    else:
        group = PairingGroup('SS1536')
        #group = PairingGroup('SS512')
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
        for i in range(k+1):
            pk2.append(pkg2**(alpha2**i))
        for i in range(k+1):
            pk2.append(pkh2**(alpha2**i))
    #Preprocessing to speed up exponentiation
    for item in pk:
        item.initPP()
    for item in pk2:
        item.initPP()
    
    participantids = []
    for i in range(k):
        participantids.append(i+1+offset)

    print "Paramgen Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()

    #Initialize Players
    dealer = VssDealer(k=k, t=t, secret=[42,69,420,11111,1717], pk=pk, pk2=pk2, participantids=participantids, group=group, symflag=symmetric)
    print "Dealer Initialization Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()

    players = []
    for i in range(k):
        players.append(VssRecipient(k=k, t=t, nodeid=i+1+offset, pk=pk, pk2=pk2, group=group, symflag=symmetric))

    print "Player Initialization Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()

    #Deal out send messages
    for i in range(k):
        players[i].receive_msg(dealer.send_sendmsg(i+1+offset))

    print "Dealing Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()
    
    #Players send out echo messages
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            players[i].receive_msg(players[j].send_echomsg())

    print "Echo Messages Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()

    #Players send out ready messages
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            players[i].receive_msg(players[j].send_readymsg(i+1+offset))

    print "Ready Messages Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()

    #END SH PHASE
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            players[i].receive_msg(players[j].send_recsharemsg())

    print "REC SHARE Elapsed Time: " + str(os.times()[4] - time[4])
    time = os.times()
    print "TOTAL Elapsed Time: " + str(os.times()[4] - timetotal[4])

if __name__ == "__main__":
    debug = True
    main()
