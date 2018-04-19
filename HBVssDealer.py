from Crypto.Cipher import AES
from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.core.engine.util import objectToBytes, bytesToObject
from base64 import encodestring, decodestring
import collections
import random
import hashlib
from PolyCommitPed import *
from helperfunctions import *
import os
import json
from reliablebroadcast import *

#Class representing a the dealer in the scheme. t is the threshold and k is the number of participants
class HBVssDealer:
    def __init__ (self, k, t, secret, sk, pk, participantids, participantkeys, group, symflag, recv_function, send_function, sid=1, seed=None):
        # Random polynomial coefficients constructed in the form
        #[c       x        x^2        ...  x^t]
        # This is structured so that t+1 points are needed to reconstruct the polynomial
        ONE = group.random(ZR) * 0 + 1
        self.witnesses = {}
        self.t = t
        self.k = k
        self.group = group
        self.sid = sid
        self.poly = list(group.random(ZR, count=t+1, seed=seed))
        self.poly[0] = ONE* secret
        self.polyhat = list(group.random(ZR, count=t+1, seed=seed))
        self.participantids = participantids
        self.participantkeys = participantkeys
        self.sharedkeys = {}
        for j in participantids:
            self.sharedkeys[j] = self.participantkeys[j] ** sk
        self.pc = PolyCommitPed(t=t, pk=pk, group=group, symflag=symflag)
        self.commitment = self.pc.commit(self.poly, self.polyhat)
        self.shares = {}
        self.encryptedshares = {}
        for j in participantids:
            self.shares[j] = f(self.poly, j)
            self.encryptedshares[j] = self.encrypt(self.sharedkeys[j], self.shares[j])
        #for j in participantids[:t+1]:
        for j in participantids:
            self.witnesses[j] = self.pc.create_witness(self.poly, self.polyhat, j)
        message = {}
        message['commit'] = objectToBytes(self.commitment, self.group)
        message['witnesses'] = objectToBytes(self.witnesses, self.group)
        message['shares'] = self.encryptedshares
        message['dealer'] = k
        message['polyhat'] = objectToBytes(self.polyhat, self.group)
        reliablebroadcast(sid, pid=k, N=k+1, f=t, leader=k, input=str(message), receive=recv_function, send=send_function)

    #wrapper for encryption that nicely converts crypto-things to something you can encrypt
    def encrypt(self, key, plaintext):
        encryptor = AES.new(objectToBytes(key, self.group)[:32], AES.MODE_CBC, 'This is an IV456')
        plaintext_bytes = objectToBytes(plaintext, self.group)
        #seriously, why do I have to do the padding...
        while len(plaintext_bytes) %16 != 0:
            plaintext_bytes = plaintext_bytes + b'\x00'
        return encryptor.encrypt(plaintext_bytes)
    
