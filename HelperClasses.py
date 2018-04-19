import socket
import pickle
from threading import Thread
from Queue import Queue


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
