from Crypto.Cipher import AES
from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.core.engine.util import objectToBytes, bytesToObject
from base64 import encodestring, decodestring
import random
import hashlib
import collections
import json
import ast
import os
import gevent
from gevent import Greenlet
from gevent.queue import Queue
from PolyCommitNP import *
from helperfunctions import *
from HBVss2Recipient import *


#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class HBVss2Server:
    def __init__ (self, k, t, nodeid, sk, pk, participantids, participantkeys, group, symflag, send_function, recv_function, write_function, reconstruction=True):
        starttime = os.times()
        self.avssrecvs = {}
        threads= []
        while True:
            msg = None
            #Terminate after not receiveing a message for x seconds. There needs to be a terminating event for gevent to be happy.
            with gevent.Timeout(100, False) as timeout:
                sender, msg = recv_function()
            if msg is None:
                write_function("killme")
                #print "Am ded now. RIP Me"
                break
            if msg[0] not in self.avssrecvs:
                #print "Server " + str(nodeid) + " Created thread for sid " + str(msg[0])
                self.avssrecvs[msg[0]] = Queue()
                recv = self.makeRecv(msg[0])
                Greenlet(HBVss2Recipient, k=k, t=t, nodeid=nodeid, sk=sk, pk=pk, participantids=participantids, participantkeys=participantkeys, group=group, symflag=symflag, send_function=send_function, recv_function=recv, write_function=write_function, sid=msg[0], reconstruction=reconstruction).start()
            self.avssrecvs[msg[0]].put((sender,msg))


    def makeRecv(self, sid):
        def _recv():
            (i,o) = self.avssrecvs[sid].get()
            return (i,o)
        return _recv
