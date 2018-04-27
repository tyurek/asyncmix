from Crypto.Cipher import AES
from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.core.engine.util import objectToBytes, bytesToObject
from base64 import encodestring, decodestring
import random
import hashlib
import collections
import json
import ast
from PolyCommitPed import *
from helperfunctions import *
from reliablebroadcast import *


#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class HBVssRecipient:
    def __init__ (self, k, t, nodeid, sk, pk, participantids, participantkeys, group, symflag, send_function, recv_function, sid=1, reconstruction=True, seed=None):
        self.group = group
        self.send_function = send_function
        self.participantids = participantids
        #TODO: Code assumes ReliableBroadcast will complete before receiving other messages. This may not be the case
        message = ast.literal_eval(reliablebroadcast(sid, nodeid, k+1, f=t, leader=k, input=None, receive=recv_function, send=send_function))
        self.sharedkey = participantkeys[k]**sk
        self.finished = False
        self.okcount = 0
        self.output = None
        self.encshares = message['shares']
        self.pc = PolyCommitPed(t=t, pk=pk, group=group, symflag=symflag)
        self.share = self.decrypt(self.sharedkey, message['shares'][nodeid])
        self.commit = bytesToObject(message['commit'], self.group)
        self.witnesses = bytesToObject(message['witnesses'], self.group)
        fixedwitnesses = {}
        for key, value in self.witnesses.iteritems():
            fixedwitnesses[int(key)] = self.witnesses[key]
        self.witnesses = fixedwitnesses
        #interpolate the rest of the witnesses
        coords = []
        for key, value in self.witnesses.iteritems():
            coords.append([key,value])
        for i in range(t+1,k):
            self.witnesses[i] = interpolate_at_x(coords, i, group)
        polyhat = bytesToObject(message['polyhat'], self.group)
        if self.pc.verify_eval(self.commit, nodeid, self.share, f(polyhat,nodeid), self.witnesses[nodeid]):
            self.send_ok_msgs()
        else:
            self.send_implicate_msgs()
        while not self.finished:
            sender, msg = recv_function()
            #msg = ast.literal_eval(msg)
            if msg[0] == "ok":
                #TODO: Enforce one OK message per participant
                self.okcount += 1
                if self.okcount == 2*t + 1:
                    self.output = self.share
                    print "Share:", self.share
                if self.okcount == k:
                    self.finished = True
            elif msg[0] == 'implicate':
                print "Wowzers!"
        

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

    def check_implication(key, implicatorid):
        share = self.decrypt(key, self.encshares[implicatorid])
        

    def send_ok_msgs(self):
        msg = []
        msg.append("ok")
        for j in self.participantids:
            self.send_function(j, msg)

    def send_implicate_msgs(self):
        msg = []
        msg.append("implicate")
        msg.append(self.sharedkey)
        for j in self.participantids:
            self.send_function(j, msg)

        
