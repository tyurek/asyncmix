import socket
import errno
from socket import error as socket_error
import cPickle as pickle
from threading import Thread
from Queue import Queue
import json
import struct
import sys

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
        receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            receiver.connect((ip, receiver_port))
            data = pickle.dumps(msg)
            padded_msg = struct.pack('>I', len(data)) + data
            receiver.sendall(padded_msg)
            # print(">> SENDING", ip, len(data))
        except socket_error as serr:
            # It is okay to get a connection refused error since
            # other shares might have been used to complete
            # reconstruction and the listener might have terminated.
            print("############# SEND ERROR #############", serr, ip)
            if serr.errno != errno.ECONNREFUSED:
                raise serr
        finally:
            receiver.close()


class Listener(object):
    """
    To abstract receiving messages from any node.
    """

    def __init__(self, listener_port):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # To reuse the same address again since this is a daemon thread.
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(('', listener_port))
        self.MAX_BYTES = 2048
        thread = Thread(target=self.__start_listener)
        thread.setDaemon(True)
        self.queue = Queue()
        thread.start()

    def __start_listener(self):
        try:
            self.listener.listen(5)
            while True:
                sender, address = self.listener.accept()
                # print('Got connection from', address)
                raw_msglen = self.recvall(sender, 4)
                if not raw_msglen:
                    # print "$$$$$ PUTTING NOTHING $$$$"
                    received_msg = [-1, ["JUNK"]]
                else:
                    msglen = struct.unpack('>I', raw_msglen)[0]
                    received_raw_msg = self.recvall(sender, msglen)
                    received_msg = pickle.loads(received_raw_msg)
                    # print(">> RECEIVING", address[0], len(received_raw_msg))
                self.queue.put(received_msg)
                sender.close()
        except ValueError as ex:
            # Eat up any exception, since this is a daemon thread and
            # we don't want to error out.
            print("############# RECV ERROR #############", ex)
            # pass


    def recvall(self, sock, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

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
        self.prepare_config_object(config)
        self.json = config

    def prepare_config_object(self, config):
        self.t = config["T"]
        self.seed = None if config["Seed"] == "" else config["Seed"]
        self.group_name = str(config["GroupName"])
        self.symmetric = config["Symmetric"]
        self.offset = config["Offset"]
        self.is_hbavss = (True if config["Protocol"].lower() == "hbavss" else
                            False)
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