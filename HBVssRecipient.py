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
        message = ast.literal_eval(reliablebroadcast(sid, nodeid, k+1, f=t, leader=k, input=None, receive=recv_function, send=send_function))
        #print participantkeys[k]**sk
        share = self.decrypt(participantkeys[k]**sk, message['shares'][nodeid])
        print str(nodeid) + ": " + str(share)
     
    def decrypt(self, key, ciphertext):
        decryptor = AES.new(objectToBytes(key, self.group)[:32], AES.MODE_CBC, 'This is an IV456')
        plaintext_bytes = decryptor.decrypt(ciphertext)
        #now we need to strip the padding off the end
        #if it's stupid but it works...
        elementsize = len(objectToBytes(self.group.random(ZR), self.group))
        paddingsize = (16 -elementsize%16)%16
        #print len(plaintext_bytes)
        plaintext_bytes = plaintext_bytes[:len(plaintext_bytes) - paddingsize]
        #print len(plaintext_bytes)
        return bytesToObject(plaintext_bytes, self.group)
