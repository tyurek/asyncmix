from HBVssDealer import *
from HBVssRecipient import *
import os
import sys
from HelperClasses import Sender, Listener, PublicKeys, Config


def simple_router(participantids, nodes_config, sender, listener, offset):
    """
    Builds a set of connected channels.
    @return (receives, sends)
    """

    def makeSend(i):
        def _send(j, o):
            # print('SEND %8s [%2d -> %2d] [%s:%d]' % (o[0], i, j,
                nodes_config[j].ip, nodes_config[j].listener_port))
            sender.send_msg((i, o), nodes_config[j].ip,
                            nodes_config[j].listener_port)
        return _send

    def makeRecv(j):
        def _recv():
            (i, o) = listener.get_msg()
            # print('RECV %8s [%2d -> %2d]' % (o[0], i, j))
            return (i, o)
        return _recv

    sends = {}
    receives = {}
    for i in participantids:
        sends[i] = makeSend(i)
        receives[i] = makeRecv(i)
    return (sends, receives)

def get_keys(idx, config):
    t = config.t
    n = 3*t + 1
    seed = config.seed
    symmetric = config.symmetric
    if not symmetric:
        #group = PairingGroup('BN256')
        group = PairingGroup(config.group_name)
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
        group = PairingGroup(config.group_name)
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

    g = group.random(ZR)
    participantpubkeys = {}
    participantprivkeys = {}
    for j in range(n+1):
        participantprivkeys[j] =  group.random(ZR)
        participantpubkeys[j] = g ** participantprivkeys[j]
        print j, participantprivkeys[j], participantpubkeys[j]
        participantprivkeys[j] = objectToBytes(participantprivkeys[j], group)
        participantpubkeys[j] = objectToBytes(participantpubkeys[j], group)

    pk_bytes = objectToBytes(pk, group)
    pk2_bytes = objectToBytes(pk2, group)
    return PublicKeys(pk_bytes, pk2_bytes), participantprivkeys, participantpubkeys

def start(idx, public_keys, config, sender, listener, priv_key, pub_keys):

    t = config.t
    n = 3*t + 1

    group = PairingGroup(config.group_name)
    symmetric = config.symmetric
    pk = bytesToObject(public_keys.pk_bytes, group)

    participantids = range(n)
    dealer_id = config.dealer_id
    sends, recvs = simple_router(participantids + [dealer_id], config.nodes,
                                sender, listener, dealer_id)

    time2 = os.times()

    #Initialize Players
    if idx == dealer_id:
        HBVssDealer(k=n, t=t,  secret=42, pk=pk, sk=priv_key,
            participantids=participantids, participantkeys=pub_keys,
            group=group, symflag=symmetric, recv_function = recvs[dealer_id],
            send_function=sends[dealer_id])
    else:
        HBVssRecipient(k=n, t=t, nodeid=idx, sk=priv_key,
            pk=pk, participantids=participantids, reconstruction=True,
            participantkeys=pub_keys, group=group, symflag=symmetric,
            send_function=sends[idx], recv_function=recvs[idx])

    print "Elapsed Time: " + str(os.times()[4] - time2[4])


config = Config(sys.argv[1])
nodes_config = config.nodes
idx = int(sys.argv[2])

listener = Listener(nodes_config[idx].listener_port)
sender = Sender()
debug = True

dealer_id = config.dealer_id

if idx == dealer_id:
    # If dealer, create keys and send to all recipients.
    public_keys, priv_keys, pub_keys = get_keys(idx, config)
    priv_key = priv_keys[dealer_id]
    for key in nodes_config.keys():
        if key != dealer_id:
            sender.send_msg(public_keys, nodes_config[key].ip,
                            nodes_config[key].listener_port)
            sender.send_msg([priv_keys[key], pub_keys], nodes_config[key].ip,
                                nodes_config[key].listener_port)
else:
    # If recipient, wait for keys from the dealer.
    public_keys = listener.get_msg()
    priv_key, pub_keys = listener.get_msg()


group = PairingGroup(config.group_name)
priv_key = bytesToObject(priv_key, group)
for k in pub_keys.keys():
    pub_keys[k] = bytesToObject(pub_keys[k], group)

# print priv_key
# print '-' * 64
# for a, b in pub_keys.items():
#     print a, b
start(idx, public_keys, config, sender, listener, priv_key, pub_keys)
