from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random
import hashlib
import collections
from PolyCommitPed import *
from helperfunctions import *

ss512 = PairingGroup('SS512')
#group = PairingGroup('MNT159')
#group = PairingGroup('MNT224')

g1 = group.hash('geng1', G1)
g1.initPP()
#g2 = g1
g2 = group.hash('geng2', G2)
g2.initPP()
ZERO = group.random(ZR, seed=59)*0
ONE = group.random(ZR, seed=60)*0+1
seed=None

#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class VssRecipient:
    #to avoid indexing hell, when scaling this to multiple dimensions, just make new objects
    def __init__ (self, k, t, nodeid, pk, pk2, group=ss512, seed=None):
        self.k = k
        self.t = t
        self.nodeid = nodeid
        self.pk = pk
        self.pk2 = pk2
        self.group = group
        self.seed = seed
        self.hashcommit = None
        self.commitments = None
        self.mywitnesses = None
        self.myhashwitness = None
        self.sendecho = None
        self.hashpoly = None
        self.share = None
        self.ready = False
        self.recshare = False
        self.poly = None
        self.polyhat = None
        self.hashpoly = None
        self.hashpolyhat = None
        self.pc = PolyCommitPed(t=t, pk=pk, group=group)
        self.pc2 = PolyCommitPed(t=k, pk=pk2, group=group)
        self.interpolatedpolyatzero = None
        self.interpolatedpolyhatatzero = None
        self.readymessages = [None] * (k+1)
        self.recsharemessages = [None] * (k+1)
        #Technically these following two lists will contain hashes of commitments to hashes, as we only need to count how many duplicates we have
        self.echoedhashcommits = [None] * (k+1)
        self.readyhashcommits = [None] * (k+1)

    def receive_msg(self, msg):
        if msg['type'] == 'send':
            if self.check_send_correctness(msg):
                self.hashcommit = msg['hashcommit']
                self.hashpolyhat = msg['hashpolyhat']
                self.commitments = msg['commitments']
                self.poly = msg['poly']
                self.polyhat = msg['polyhat']
                self.mywitnesses = []
                self.mywitnesses.append(None)
                for j in range(1,self.k+1):
                    self.mywitnesses.append(self.pc.create_witness(msg['poly'], msg['polyhat'], j))
                self.myhashwitness = self.pc2.create_witness(self.hashpoly, msg['hashpolyhat'], self.nodeid)
                self.sendecho = True
            else:
                self.sendecho = False
        if msg['type'] == 'echo':
            #This code keeps a tally of how many times each message has been received and checks if it's over the threshold
            #First make sure we haven't received this particular echo message before and that we still care about echo messages
            if self.echoedhashcommits[msg['id']] == None and not self.ready:
            #We take a hash of these commitments for the sole purpose of being able to compare them with python tools
                self.echoedhashcommits[msg['id']] = hashlib.sha256(group.serialize(msg['hashcommit'])).hexdigest()
                for key, value in collections.Counter(self.echoedhashcommits).iteritems():
                    if value >= (self.k - self.t) and key != None:
                        self.ready = True
                        #We're sharing the hash polynomial commitment we received iff it's the same one that k - t others gave us
                        self.share = key == hashlib.sha256(group.serialize(self.hashcommit)).hexdigest()
                        self.hashcommit = msg['hashcommit']
        if msg['type'] == 'ready':
            #Ignore invalid messages and messages where we have already received a valid message from that sender
            if self.readymessages[msg['id']] is not None or (msg['share'] and not self.check_ready_correctness(msg)):
                return
            #print "Correct ready!"
            self.readymessages[msg['id']] = msg
            if not self.ready:
                #This is very similar to how we receive echo messages. Basically a fallback if we don't get enough echos
                if self.readyhashcommits[msg['id']] == None and self.nosharehashcommits[msg['id']] == None:
                    self.readyhashcommits[msg['id']] = hashlib.sha256(group.serialize(msg['hashcommit'])).hexdigest()
                    for key, value in collections.Counter(self.readyhashcommits).iteritems():
                        if value >= (self.t + 1) and key != None:
                            self.ready = True
                            #We're sharing whatever hash polynomial commitment we received t + 1 of
                            self.share = key == hashlib.sha256(group.serialize(self.hashcommit)).hexdigest()
                            self.hashcommit = msg['hashcommit']
            if not self.ready:
                return
            validmessagecount = 0
            for message in self.readymessages:
                if message is not None and message['hashcommit'] == self.hashcommit:
                    validmessagecount += 1
            if validmessagecount >= (self.k - self.t):
                interpolatedpolycoords = []
                interpolatedpolyhatcoords = []
                interpolatedcommitmentcoords = []
                interpolatedwitnesscoords = []
                for message in self.readymessages:
                    if message is None or not message['share'] or message['hashcommit'] != self.hashcommit:
                        continue
                    interpolatedpolycoords.append([message['id'], message['polypoint']])
                    interpolatedpolyhatcoords.append([message['id'], message['polyhatpoint']])
                    interpolatedcommitmentcoords.append([message['id'], message['commitment']])
                    interpolatedwitnesscoords.append([message['id'], message['polywitness']])
                    if len(interpolatedpolycoords) == (self.t + 1):
                        break
                self.interpolatedpolyatzero = interpolate_at_x(interpolatedpolycoords, x=0)
                self.interpolatedpolyhatatzero = interpolate_at_x(interpolatedpolyhatcoords, x=0)
                self.interpolatedzerocommitment = interpolate_at_x(interpolatedcommitmentcoords, x=0)
                self.interpolatedzerowitness = interpolate_at_x(interpolatedwitnesscoords, x=0)
                self.recshare = True
                #Check the validity of any recshare messages we may have received before we could have checked them
                for i in range(len(self.recsharemessages)):
                    if self.recsharemessages[i] is None:
                        continue
                    if not self.check_recshare_correctness(self.recsharemessages[i]):
                        self.recsharemessages[i] = None
                    
                    
        if msg['type'] == 'recshare':
            #Ignore messages where we have already received a message from that sender
            #Still hold onto messages we receive even if we can't yet validate them
            if self.recsharemessages[msg['id']] is not None:
                return
            if not self.recshare:
                self.recsharemessages[msg['id']] = msg
                return
            if not self.check_recshare_correctness(msg):
                print "Invalid message!"
                return
            self.recsharemessages[msg['id']] = msg
            msgcount = 0
            for msg in self.recsharemessages:
                if msg is not None:
                    msgcount += 1
            if msgcount == self.t + 1:
                secretcoords = []
                for msg in self.recsharemessages:
                    if msg is not None:
                        secretcoords.append([msg['id'], msg['polypoint']])
                print "Node " + str(self.nodeid) + ": The secret is " + str(interpolate_at_x(secretcoords,0))

    def check_send_correctness(self, sendmsg):
        #verify commitments can be interpolated from each other
        commitmentsvalid = check_commitment_integrity(sendmsg['commitments'], self.t)
        #verify correctness of witnesses
        witnessesvalid = True
        for i in range(len(sendmsg['witnesses'])):
            #Taking advantage of the polynomial symmetry, we know points on other polynomials too. f(nodeid, i) == f(i, nodeid)
            witnessesvalid = witnessesvalid and \
                self.pc.verify_eval(sendmsg['commitments'][i], self.nodeid, f(sendmsg['poly'],i), f(sendmsg['polyhat'],i), sendmsg['witnesses'][i])
        #veryify correctness of hash polynomial commitment
        self.hashpoly = []
        for c in sendmsg['commitments']:
            self.hashpoly.append(hexstring_to_ZR(hashlib.sha256(group.serialize(c)).hexdigest()))
        hashpolycommitmentvalid = self.pc2.verify_poly(sendmsg['hashcommit'], self.hashpoly, sendmsg['hashpolyhat'])
        #verify correctness of regular polynomial
        polyvalid = self.pc.verify_poly(sendmsg['commitments'][self.nodeid], sendmsg['poly'], sendmsg['polyhat'])
        return commitmentsvalid and witnessesvalid and hashpolycommitmentvalid and polyvalid

    def check_ready_correctness(self, readymsg):
        return self.pc.verify_eval(readymsg['commitment'], self.nodeid, readymsg['polypoint'], readymsg['polyhatpoint'], readymsg['polywitness']) and \
            self.pc2.verify_eval(readymsg['hashcommit'], readymsg['id'], f(self.hashpoly, readymsg['id']), \
            readymsg['hashpolyhatpoint'], readymsg['hashpolywitness'])

    def check_recshare_correctness(self, recsharemsg):
        return self.pc.verify_eval(self.interpolatedzerocommitment, recsharemsg['id'], recsharemsg['polypoint'], recsharemsg['polyhatpoint'],  recsharemsg['polywitness'])

    def send_echomsg(self):
        if type(self.sendecho) is not bool:
            print "Can not send echo, no send message received"
            return None
        elif not self.sendecho:
            print "Invalid send message, can not echo"
            return None
        else:
            echomsg = {}
            echomsg['type'] = 'echo'
            echomsg['hashcommit'] = self.hashcommit
            echomsg['id'] = self.nodeid
            return echomsg

    #Send a ready message to party j
    def send_readymsg(self,j):
        if not self.ready:
            print "Can not send ready message, I have not received enough echo messages"
            return None
        readymsg = {}
        readymsg['type'] = 'ready'
        readymsg['id'] = self.nodeid
        readymsg['share'] = self.share
        readymsg['hashcommit'] = self.hashcommit
        if self.share:
            readymsg['polypoint'] = f(self.poly, j)
            readymsg['polyhatpoint'] = f(self.polyhat, j)
            readymsg['polywitness'] = self.mywitnesses[j]
            readymsg['commitment'] = self.commitments[self.nodeid]
            readymsg['hashpolyhatpoint'] = f(self.hashpolyhat, self.nodeid)
            readymsg['hashpolywitness'] = self.myhashwitness
        return readymsg
    
    def send_recsharemsg(self):
        if not self.recshare:
            print "Can not send Rec-Share message, I have not received enough ready messages"
            return None
        recsharemsg = {}
        recsharemsg['type'] = 'recshare'
        recsharemsg['id'] = self.nodeid
        recsharemsg['polypoint'] = self.interpolatedpolyatzero
        recsharemsg['polyhatpoint'] = self.interpolatedpolyhatatzero
        recsharemsg['polywitness'] = self.interpolatedzerowitness
        return recsharemsg
        

