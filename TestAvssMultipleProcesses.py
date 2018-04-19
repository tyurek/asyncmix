from VssDealer import *
from VssRecipient import *
import socket
import sys
from Queue import Queue
import pickle
from threading import Thread


class Params(object):
    """
    Parameters which are common and to be used by all participants.
    """

    def __init__(self, dealer_id, n, t, pk, pk2, group_name, offset,
                 symmetric):
        self.dealer_id = dealer_id
        self.n = n
        self.t = t
        self.pk = pk
        self.pk2 = pk2
        self.group_name = group_name
        self.offset = offset
        self.symmetric = symmetric


class Sender(object):
    """
    To abstract sending a message to a particular Node.
    """

    def send_msg(self, msg, ip, receiver_port):
        receiver = socket.socket()
        receiver.connect((ip, receiver_port))
        receiver.send(pickle.dumps(msg))
        receiver.close()


class Listener(object):
    """
    To abstract receiving messages from any node.
    """

    def __init__(self, listener_port):
        self.listener = socket.socket()
        self.listener.bind(('', listener_port))
        self.MAX_BYTES = 1024*16
        thread = Thread(target=self.__start_listener)
        # thread.setDaemon(True)
        thread.start()
        self.queue = Queue()

    def __start_listener(self):
        self.listener.listen(5)
        while True:
            sender, address = self.listener.accept()
            # print('Got connection from', address)
            received_msg = sender.recv(self.MAX_BYTES)
            # print(">> Recieved")
            self.queue.put(pickle.loads(received_msg))
            sender.close()

    def get_msg(self):
        """
        Returns a received message from the queue.
        Blocks until there is a message to return.
        """

        return self.queue.get(block=True)


class NodeDetails(object):
    """
    Denotes the details which are used to send and
    receive messages from a node.
    """

    def __init__(self, ip, sender_port, listener_port):
        self.ip = ip
        self.sender_port = sender_port
        self.listener_port = listener_port


class Config(object):
    """
    Describes the config which contains node information.
    The config is of the form:
        Id:Ip:Sender_Port:Listener_Port
    """

    def __init__(self, config_file_path):
        self.config = {}
        with open(config_file_path, "r") as file_handle:
            for line in file_handle:
                idx, ip, sender_port, listener_port = line.split(":")
                idx = int(idx)
                self.config[idx] = NodeDetails(ip, int(sender_port),
                                               int(listener_port))


def simple_router(participantids, config, sender, listener, offset):
    """
    Builds a set of connected channels.
    @return (receives, sends)
    """

    def makeSend(i):
        def _send(j, o):
            # print('SEND %8s [%2d -> %2d]' % (o[0], i, j))
            sender.send_msg((i, o), config[j-offset-1].ip,
                            config[j-offset-1].listener_port)
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


def get_params(idx):
    offset = 69
    t = 2
    n = 7
    seed = None
    symmetric = False

    if not symmetric:
        # group = PairingGroup('BN256')
        group_name = 'MNT159'
        group = PairingGroup(group_name)
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
        # group = PairingGroup('SS1536')
        group_name = 'SS512'
        group = PairingGroup(group_name)
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

    # Preprocessing to speed up exponentiation
    for item in pk:
        item.initPP()
    for item in pk2:
        item.initPP()

    pkBytes = objectToBytes(pk, group)
    pk2Bytes = objectToBytes(pk2, group)
    dealerid = -1
    return Params(dealerid, n, t, pkBytes, pk2Bytes, group_name, offset,
                  symmetric)


def start(params, config, sender, listener):
    n = params.n
    t = params.t
    group_name = params.group_name
    group = PairingGroup(group_name)
    pk = bytesToObject(params.pk, group)
    pk2 = bytesToObject(params.pk2, group)
    offset = params.offset
    symmetric = params.symmetric
    dealerid = params.dealer_id

    participantids = []
    for i in range(n):
        participantids.append(i+1+offset)

    # print('-'*64)
    # print(participantids)
    # print('-'*64)
    # print(pk)
    # print('-'*64)
    # print(pk2)

    # Initialize Players
    sends, recvs = simple_router(participantids + [dealerid], config, sender,
                                 listener, offset)
    if idx == -1:
        VssDealer(k=n, t=t,  secret=[42, 69, 420, 11111, 1717], pk=pk, pk2=pk2,
                  participantids=participantids, group=group,
                  symflag=symmetric, send_function=sends[dealerid])
    else:
        i = idx
        VssRecipient(k=n, t=t, nodeid=i+1+offset, pk=pk, pk2=pk2,
                     participantids=participantids, group=group,
                     symflag=symmetric, send_function=sends[i+1+offset],
                     recv_function=recvs[i+1+offset], reconstruction=True)



config = Config(sys.argv[1]).config
idx = int(sys.argv[2])

listener = Listener(config[idx].listener_port)
sender = Sender()
debug = True

if idx == -1:
    params = get_params(idx)
    for keys in config.keys():
        if keys != -1:
            # print("### ATTEMPTING SEND")
            sender.send_msg(params, config[keys].ip,
                            config[keys].listener_port)
            # print("### SEND SUCCESSFUL")
else:
    params = listener.get_msg()

start(params, config, sender, listener)
