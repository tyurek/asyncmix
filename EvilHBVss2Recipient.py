from Crypto.Cipher import AES
from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.core.engine.util import objectToBytes, bytesToObject
from base64 import encodestring, decodestring
import random
import hashlib
import collections
import json
import ast
from gevent import Greenlet
from gevent.queue import Queue
from PolyCommitPed import *
from PolyCommitNP import *
from helperfunctions import *
from reliablebroadcast import *


#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class EvilHBVss2Recipient:
    def __init__ (self, k, t, nodeid, sk, pk, participantids, participantkeys, group, symflag, send_function, recv_function, sid=1, reconstruction=True, seed=None):
        self.group = group
        self.send_function = send_function
        self.participantids = participantids
        self.participantkeys = participantkeys
        self.reconstruction = reconstruction
        self.nodeid = nodeid
        self.t = t
        self.k = k
        self.dealerid = k
        #maybe CRS would be a more fitting name since pk doesn't go with sk?
        self.pk = pk
        self.sk = sk
        self.sharedkey = participantkeys[self.dealerid]**sk
        self.rbfinished = False
        self.finished = False
        self.sendrecs = False
        self.sharevalid = False
        self.okcount = 0
        self.implicatecount = 0
        self.output = None
        self.secret = None
        self.pc = PolyCommitNP(t=t, pk=pk, group=group)
        self.shares = {}
        self.queues = {}
        self.recvs = {}
        msgtypes = ["rb", "hbavss"]
        for msgtype in msgtypes:
            self.queues[msgtype] = Queue()
            self.recvs[msgtype] = self.makeRecv(msgtype)
        
        rb_thread = Greenlet(rbc_and_send, sid, nodeid, k+1, t, k, None, self.recvs["rb"], send_function)
        rb_thread.start()
        #send_function(nodeid, ["send", reliablebroadcast(sid, nodeid, k+1, f=t, leader=k, input=None, receive=self.recvs["rb"], send=send_function)])
        while not self.finished:
            sender, msg = recv_function()
            self.receive_msg(sender,msg)
        
    def receive_msg(self, sender, msg):
        #print msg[0]
        if msg[0] in ["READY", "ECHO", "VAL"]:
            self.queues["rb"].put((sender, msg))
        if msg[0] == "send":
            self.rbfinished = True
            message = ast.literal_eval(msg[1])
            self.encshares = message['shares']
            self.encwitnesses = message['witnesses']
            self.share = self.decrypt(self.sharedkey, message['shares'][self.nodeid])
            self.witness = self.decrypt(self.sharedkey, message['witnesses'][self.nodeid])
            self.commit = bytesToObject(message['commit'], self.group)
            #if self.pc.verify_eval(self.commit, self.nodeid, self.share, self.witness):
            #    self.send_ok_msgs()
            #    self.sendrecs = True
            #else:
            #    self.send_implicate_msgs()
            self.send_implicate_msgs()
            self.finished = True
            while not self.queues["hbavss"].empty():
                (i,o) = self.queues["hbavss"].get()
                self.receive_msg(i,o)
        if not self.rbfinished:
            self.queues["hbavss"].put((sender,msg))
        elif msg[0] == "ok":
            #TODO: Enforce one OK message per participant
            self.okcount += 1
            if self.okcount == 2*self.t + 1:
                self.output = self.share
                #print self.share
                if self.reconstruction and self.sendrecs:
                    self.send_rec_msgs()
                    self.sendrecs = False
            if self.okcount == self.k and not self.reconstruction:
                self.finished = True
        elif msg[0] == 'implicate':
            if self.check_implication(int(sender), msg[1], msg[2]):
                self.implicatecount += 1
                if self.implicatecount == 2*self.t+1:
                    print "Output: None"
                    self.share = None
                    self.finished = True
                if self.sendrecs:
                    self.reconstruction = True
                    self.send_rec_msgs()
                    self.sentdrecs = False
            else:
                self.okcount += 1 
        elif msg[0] == 'rec':
            if self.pc.verify_eval(self.commit, sender, msg[1], msg[2]):
                self.shares[sender] = msg[1]
            if len(self.shares) == self.t + 1:
                coords = []
                for key, value in self.shares.iteritems():
                    coords.append([key, value])
                self.secret = interpolate_at_x(coords, 0, self.group)
                print self.secret
                self.finished = True

    def decrypt(self, key, ciphertext):
        decryptor = AES.new(objectToBytes(key, self.group)[:32], AES.MODE_CBC, 'This is an IV456')
        plaintext_bytes = decryptor.decrypt(ciphertext)
        #now we need to strip the padding off the end
        #if it's stupid but it works...
        elementsize = len(objectToBytes(self.group.random(ZR), self.group))
        paddingsize = (16 -elementsize%16)%16
        #print len(plaintext_bytes)
        #plaintext_bytes = plaintext_bytes[:len(plaintext_bytes) - paddingsize]
        #print len(plaintext_bytes)
        return bytesToObject(plaintext_bytes, self.group)

    #checks if an implicate message is valid
    def check_implication(self, implicatorid, key, proof):
        #First check if they key that was sent is valid
        if not check_same_exponent_proof(proof, self.pk[0],self.participantkeys[self.dealerid], self.participantkeys[implicatorid], key):
            return False
        share = self.decrypt(key, self.encshares[implicatorid])
        witness = self.decrypt(key, self.encwitnesses[implicatorid])
        return not self.pc.verify_eval(self.commit, implicatorid, share, witness)
        
    def send_ok_msgs(self):
        msg = []
        msg.append("ok")
        for j in self.participantids:
            self.send_function(j, msg)

    def send_implicate_msgs(self):
        msg = []
        msg.append("implicate")
        msg.append(self.sharedkey**27)
        #msg.append(self.sharedkey)
        msg.append(prove_same_exponent(self.pk[0], self.participantkeys[self.dealerid],self.sk,self.group))
        for j in self.participantids:
            self.send_function(j, msg)

    def send_rec_msgs(self):
        msg = []
        msg.append("rec")
        msg.append(self.share)
        msg.append(self.witness)
        for j in self.participantids:
            self.send_function(j, msg)
    
    def makeRecv(self, msgtype):
        def _recv():
            (i,o) = self.queues[msgtype].get()
            return (i,o)
        return _recv

def rbc_and_send(sid, nodeid, n, t, k, ignoreme, receive, send):
    msg = reliablebroadcast(sid, nodeid, n, f=t, leader=k, input=None, receive=receive, send=send)
    send(nodeid, ["send", msg])
