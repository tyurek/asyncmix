from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.core.engine.util import objectToBytes, bytesToObject
from base64 import encodestring, decodestring
import random
import hashlib
import collections
import json
from PolyCommitPed import *
from helperfunctions import *


#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class VssRecipient:
    def __init__ (self, k, t, nodeid, pk, pk2, participantids, group, symflag, send_function, recv_function, vssinstance=1, seed=None):
        self.k = k
        self.t = t
        self.nodeid = nodeid
        self.pk = pk
        self.pk2 = pk2
        self.participantids = participantids
        self.group = group
        self.vssinstance = vssinstance
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
        self.finished = False
        self.poly = None
        self.polyhat = None
        self.hashpoly = None
        self.hashpolyhat = None
        self.pc = PolyCommitPed(t=t, pk=pk, group=group, symflag=symflag)
        self.pc2 = PolyCommitPed(t=k, pk=pk2, group=group, symflag=symflag)
        self.interpolatedpolyatzero = None
        self.interpolatedpolyhatatzero = None
        self.readymessages = {}
        self.recsharemessages = {}
        self.send_function = send_function
        #Technically these following two lists will contain hashes of commitments to hashes, as we only need to count how many duplicates we have
        self.echoedhashcommits = {}
        self.readyhashcommits = {}
        while not self.finished:
            sender, msg = recv_function()
            self.receive_msg(msg)
        
    def receive_msg(self, msg):
        if msg is None:
            return
        if type(msg) is not dict:
            msg = json.loads(msg)
        if msg['type'] == 'send':
            for key, value in msg.iteritems():
                if key != 'type' and key != 'instance':
                    msg[key] = bytesToObject(value, self.group)
            for key, value in msg['commitments'].iteritems():
                msg['commitments'][int(key)] = msg['commitments'][key]
                del msg['commitments'][key]
            for key, value in msg['witnesses'].iteritems():
                msg['witnesses'][int(key)] = msg['witnesses'][key]
                del msg['witnesses'][key]
            #print msg
            if self.check_send_correctness(msg):
                self.hashcommit = msg['hashcommit']
                self.hashpolyhat = msg['hashpolyhat']
                self.commitments = msg['commitments']
                self.poly = msg['poly']
                self.polyhat = msg['polyhat']
                self.mywitnesses = {}
                #for j in range(1,self.k+1):
                for j in msg['commitments']:
                    #We don't need a witness at 0. It wouldn't really hurt though
                    if j != 0:
                        self.mywitnesses[j] = self.pc.create_witness(msg['poly'], msg['polyhat'], j)
                self.myhashwitness = self.pc2.create_witness(self.hashpoly, msg['hashpolyhat'], self.nodeid)
                self.sendecho = True
                for j in self.participantids:
                    self.send_function(j, self.send_echomsg())
            else:
                self.sendecho = False
        if msg['type'] == 'echo':
            #This code keeps a tally of how many times each message has been received and checks if it's over the threshold
            #First make sure we haven't received this particular echo message before and that we still care about echo messages
            #if self.echoedhashcommits[msg['id']] == None and not self.ready:
            if msg['id'] not in self.echoedhashcommits and not self.ready:
                msg['hashcommit'] = bytesToObject(msg['hashcommit'],self.group)
            #We take a hash of these commitments for the sole purpose of being able to compare them with python tools
                self.echoedhashcommits[msg['id']] = hashlib.sha256(str(msg['hashcommit'])).hexdigest()
                #for key, value in collections.Counter(self.echoedhashcommits).iteritems():
                for key, value in collections.Counter(self.echoedhashcommits.values()).iteritems():
                    if value >= (self.k - self.t) and key != None:
                        self.ready = True
                        #We're sharing the hash polynomial commitment we received iff it's the same one that k - t others gave us
                        self.share = key == hashlib.sha256(str(self.hashcommit)).hexdigest()
                        self.hashcommit = msg['hashcommit']
                        for j in self.participantids:
                            self.send_function(j, self.send_readymsg(j))
        if msg['type'] == 'ready':
            for key, value in msg.iteritems():
                if key not in ['type', 'id', 'share']:
                    msg[key] = bytesToObject(msg[key], self.group)
            #Ignore invalid messages and messages where we have already received a valid message from that sender
            #if self.readymessages[msg['id']] is not None or (msg['share'] and not self.check_ready_correctness(msg)):
            if msg['id'] in self.readymessages or (msg['share'] and not self.check_ready_correctness(msg)):
                return
            self.readymessages[msg['id']] = msg
            if not self.ready:
                #This is very similar to how we receive echo messages. Basically a fallback if we don't get enough echos
                #if self.readyhashcommits[msg['id']] == None and self.nosharehashcommits[msg['id']] == None:
                if msg['id'] not in self.readyhashcommits and self.nosharehashcommits[msg['id']] == None:
                    self.readyhashcommits[msg['id']] = hashlib.sha256(str(msg['hashcommit'])).hexdigest()
                    for key, value in collections.Counter(self.readyhashcommits.values()).iteritems():
                        if value >= (self.t + 1) and key != None:
                            self.ready = True
                            #We're sharing whatever hash polynomial commitment we received t + 1 of
                            self.share = key == hashlib.sha256(str(self.hashcommit)).hexdigest()
                            self.hashcommit = msg['hashcommit']
                            for j in self.participantids:
                                self.send_function(j, self.send_readymsg(j))
            if not self.ready:
                return
            validmessagecount = 0
            for key, message in self.readymessages.iteritems():
                if message is not None and message['hashcommit'] == self.hashcommit:
                    validmessagecount += 1
            if validmessagecount >= (self.k - self.t):
                interpolatedpolycoords = []
                interpolatedpolyhatcoords = []
                interpolatedcommitmentcoords = []
                interpolatedwitnesscoords = []
                for key, message in self.readymessages.iteritems():
                    if message is None or not message['share'] or message['hashcommit'] != self.hashcommit:
                        continue
                    interpolatedpolycoords.append([message['id'], message['polypoint']])
                    interpolatedpolyhatcoords.append([message['id'], message['polyhatpoint']])
                    interpolatedcommitmentcoords.append([message['id'], message['commitment']])
                    interpolatedwitnesscoords.append([message['id'], message['polywitness']])
                    if len(interpolatedpolycoords) == (self.t + 1):
                        break
                self.interpolatedpolyatzero = interpolate_at_x(interpolatedpolycoords, 0, self.group)
                self.interpolatedpolyhatatzero = interpolate_at_x(interpolatedpolyhatcoords, 0, self.group)
                self.interpolatedzerocommitment = interpolate_at_x(interpolatedcommitmentcoords, 0, self.group)
                self.interpolatedzerowitness = interpolate_at_x(interpolatedwitnesscoords, 0, self.group)
                self.recshare = True
                for j in self.participantids:
                    self.send_function(j, self.send_recsharemsg())
                #Check the validity of any recshare messages we may have received before we could have checked them
                #for i in range(len(self.recsharemessages)):
                for i in self.recsharemessages:
                    #if self.recsharemessages[i] is None:
                    #    continue
                    if not self.check_recshare_correctness(self.recsharemessages[i]):
                        del self.recsharemessages[i]
                        #self.recsharemessages[i] = None
                    
                    
        if msg['type'] == 'recshare':
            for key, value in msg.iteritems():
                if key not in ['type', 'id']:
                    msg[key] = bytesToObject(msg[key], self.group)
            #Ignore messages where we have already received a message from that sender
            #Still hold onto messages we receive even if we can't yet validate them
            if msg['id'] in self.recsharemessages:
                return
            if not self.recshare:
                self.recsharemessages[msg['id']] = msg
                return
            if not self.check_recshare_correctness(msg):
                print "Invalid message!"
                return
            self.recsharemessages[msg['id']] = msg
            msgcount = 0
            for key, msg in self.recsharemessages.iteritems():
                if msg is not None:
                    msgcount += 1
            if msgcount == self.t + 1:
                secretcoords = []
                for key, msg in self.recsharemessages.iteritems():
                    if msg is not None:
                        secretcoords.append([msg['id'], msg['polypoint']])
                secrets = []
                for i in range(self.t + 1):
                    secrets.append(interpolate_at_x(secretcoords,i,self.group))
                print "Node " + str(self.nodeid) + ": The secret is " + str(secrets)
                self.finished = True

    def check_send_correctness(self, sendmsg):
        #verify commitments can be interpolated from each other
        commitmentsvalid = check_commitment_integrity(sendmsg['commitments'], self.t, self.group)
        #verify correctness of witnesses
        witnessesvalid = True
        #i is the key for the dictionary. i.e. a list of ids of all participants
        for i in sendmsg['witnesses']:
            #Taking advantage of the polynomial symmetry, we know points on other polynomials too. f(nodeid, i) == f(i, nodeid)
            witnessesvalid = witnessesvalid and \
                self.pc.verify_eval(sendmsg['commitments'][i], self.nodeid, f(sendmsg['poly'],i), f(sendmsg['polyhat'],i), sendmsg['witnesses'][i])
        #veryify correctness of hash polynomial commitment
        #hashpoly must be generated the same way as in VssDealer
        hashpolypoints = []
        ONE = self.group.random(ZR, seed=60)*0+1
        for i in sendmsg['commitments']:
            hashpolypoints.append([ONE * i, hexstring_to_ZR(hashlib.sha256(str(sendmsg['commitments'][i])).hexdigest(), self.group)])
        self.hashpoly = interpolate_poly(hashpolypoints)
        hashpolycommitmentvalid = self.pc2.verify_poly(sendmsg['hashcommit'], self.hashpoly, sendmsg['hashpolyhat'])
        #verify correctness of regular polynomial
        polyvalid = self.pc.verify_poly(sendmsg['commitments'][self.nodeid], sendmsg['poly'], sendmsg['polyhat'])
        return commitmentsvalid and witnessesvalid and hashpolycommitmentvalid and polyvalid

    def check_ready_correctness(self, readymsg):
        return self.pc.verify_eval(readymsg['commitment'], self.nodeid, readymsg['polypoint'], readymsg['polyhatpoint'], readymsg['polywitness']) and \
            self.pc2.verify_eval(readymsg['hashcommit'], readymsg['id'], hexstring_to_ZR(hashlib.sha256(str(readymsg['commitment'])).hexdigest(), self.group), \
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
            echomsg['hashcommit'] = objectToBytes(self.hashcommit, self.group)
            echomsg['id'] = self.nodeid
            return json.dumps(echomsg)

    #Send a ready message to party j
    def send_readymsg(self,j):
        if not self.ready:
            print "Can not send ready message, I have not received enough echo messages"
            return None
        readymsg = {}
        readymsg['type'] = 'ready'
        readymsg['id'] = self.nodeid
        readymsg['share'] = self.share
        readymsg['hashcommit'] = objectToBytes(self.hashcommit, self.group)
        if self.share:
            readymsg['polypoint'] = objectToBytes(f(self.poly, j), self.group)
            readymsg['polyhatpoint'] = objectToBytes(f(self.polyhat, j), self.group)
            readymsg['polywitness'] = objectToBytes(self.mywitnesses[j], self.group)
            readymsg['commitment'] = objectToBytes(self.commitments[self.nodeid], self.group)
            readymsg['hashpolyhatpoint'] = objectToBytes(f(self.hashpolyhat, self.nodeid), self.group)
            readymsg['hashpolywitness'] = objectToBytes(self.myhashwitness, self.group)
        return json.dumps(readymsg)
    
    def send_recsharemsg(self):
        if not self.recshare:
            print "Can not send Rec-Share message, I have not received enough ready messages"
            return None
        recsharemsg = {}
        recsharemsg['type'] = 'recshare'
        recsharemsg['id'] = self.nodeid
        recsharemsg['polypoint'] = objectToBytes(self.interpolatedpolyatzero, self.group)
        recsharemsg['polyhatpoint'] = objectToBytes(self.interpolatedpolyhatatzero, self.group)
        recsharemsg['polywitness'] = objectToBytes(self.interpolatedzerowitness, self.group)
        return json.dumps(recsharemsg)




