import socket
import pickle
from threading import Thread
from Queue import Queue
import json


class PublicKeys(object):
    """
    Parameters which are common and to be used by all participants.
    """

    def __init__(self, pk_bytes, pk2_bytes):
        self.pk_bytes = pk_bytes
        self.pk2_bytes = pk2_bytes


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

    def __init__(self, config_file_path):
        config = json.load(open(config_file_path))
        self.t = config["T"]
        self.seed = None if config["Seed"] == "" else config["Seed"]
        self.group_name = str(config["GroupName"])
        self.symmetric = config["Symmetric"]
        self.offset = config["Offset"]
        self.dealer_id = config["Dealer"]["Id"]
        self.nodes = {}
        self.nodes[config["Dealer"]["Id"]] = (NodeDetails(
            config["Dealer"]["Ip"],
            config["Dealer"]["SenderPort"],
            config["Dealer"]["ListenerPort"]
            ))
        self.n = len(config["Recipients"])
        for recipient in config["Recipients"]:
            self.nodes[recipient["Id"]] = (NodeDetails(
                recipient["Ip"],
                recipient["SenderPort"],
                recipient["ListenerPort"]
                ))
