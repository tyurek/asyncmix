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

#Class representing a the dealer in the scheme. t is the threshold and k is the number of participants
class VssDealer:
    def __init__ (self, k, t, secret, pk, pk2, participantids, group, symflag, send_function, sid=1, seed=None):
        # Random polynomial coefficients constructed in the form
        #[c       x        x^2        ...  x^t
        # y       xy       x^2y       ...  x^t*y
        # y^2     x*y^2    x^2*y^2    ...  x^t*y^2
        # ...     ...      ...        ...  ...
        # y^t     x*y^t    x^2*y^t    ...  x^t*y^t]
        # This is structured so that t+1 points are needed to reconstruct the polynomial
        self.commitments = {}
        self.witnessvectors = {}
        self.projas = {}
        self.projahats = {}
        self.hashpoly = []
        self.t = t
        self.k = k
        self.group = group
        self.sid = sid
        self.a = [list(group.random(ZR, count=t+1, seed=seed)) for i in range(t+1)]
        self.ahat = [list(group.random(ZR, count=t+1, seed=seed)) for i in range(t+1)]
        self.participantids = participantids
        ZERO = group.random(ZR, seed=59)*0
        ONE = group.random(ZR, seed=60)*0+1
        #if type(secret) is list:
        if isinstance(secret, collections.Iterable):
            secretpoints = []
            for i in range(t+1):
                if i < len(secret):
                    secretpoints.append([i,secret[i]*ONE])
                else:
                    secretpoints.append([i,ZERO])
            self.a[0] = interpolate_poly(secretpoints)
        else:
            self.a[0][0] = secret
        #make the polynomials symmetric
        for i in range(t+1):
            for j in range(i):
                self.a[i][j] = self.a[j][i]
                self.ahat[i][j] = self.ahat[j][i]
        self.pc = PolyCommitPed(t=t, pk=pk, group=group, symflag=symflag)
        self.pc2 = PolyCommitPed(t=k, pk=pk2, group=group, symflag=symflag)
        time2 = os.times()
        for j in participantids + [0]:
            #Create lists of polynomial projections at different points for ease of use
            self.projas[j] = projf(self.a, j)
            self.projahats[j] = projf(self.ahat, j)
            #Create commitments for each of these projections
            self.commitments[j] = self.pc.commit(self.projas[j], self.projahats[j])
        print "Commitments and Projections Elapsed Time: " + str(os.times()[4] - time2[4])
        time2 = os.times()
        #A different loop is needed for witnesses so that all projections are already calculated
        for j in participantids:
            witnesses = {}
            for i in participantids:
            #for i in participantids[:t+1]:
                witnesses[i] = self.pc.create_witness(self.projas[i], self.projahats[i], j)
                #witnesses[i].initPP()
            #coords = []
            #for key,value in witnesses.iteritems():
            #    coords.append([key, value])
            #witnesspoly = interpolate_poly(coords, self.group)
            #print witnesspoly
            #witnesspoly2 = interpolate_poly(coords)
            #print witnesspoly2
            #for i in participantids[t+1:]:
                #witnesses[i] = interpolate_commitment_at_x(coords, i, self.group)
                #witnesses[i] = interpolate_at_x(coords, i, self.group)
            #    witnesses[i] = f(witnesspoly, i)
            #print witnesses[participantids[7]]
            #print interpolate_at_x(coords, participantids[7], self.group)
            #print f(witnesspoly,participantids[0])
            self.witnessvectors[j] = witnesses
        print "Witnesses Elapsed Time: " + str(os.times()[4] - time2[4])
        time2 = os.times()
        #Create the polynomial of hashes of commitments and commit to it
        hashpolypoints = []
        for i in participantids + [0]:
            #not sure if there's an agreed upon way to hash a pairing element to something outside the group
            #so I SHA256 hash the bitstring representation of the element
            hashpolypoints.append([ONE * i, hexstring_to_ZR(hashlib.sha256(str(self.commitments[i])).hexdigest(), group)])
        self.hashpoly = interpolate_poly(hashpolypoints)
        self.hashpolyhat = list(group.random(ZR, count=k+1, seed=seed))
        self.hashcommit = self.pc2.commit(self.hashpoly, self.hashpolyhat)
        print "The Rest Elapsed Time: " + str(os.times()[4] - time2[4])
        time2 = os.times()
        for j in participantids:
            send_function(j, self.send_sendmsg(j))

    #send a "send" message to party member j
    def send_sendmsg(self, j):
        sendmsg = {}
        sendmsg['sid'] = self.sid
        sendmsg['type'] = 'send'
        #One commitment to the polynomial of hashes of commitments
        sendmsg['hashcommit'] = objectToBytes(self.hashcommit, self.group)
        #List of commitments to casted polynomials, k+1 commitments in all (where k is the number of participants)
        #print str(self.commitments)
        #print bytesToObject(objectToBytes(self.commitments, self.group), self.group)
        sendmsg['commitments'] = objectToBytes(self.commitments, self.group)
        #Polynomial (degree t) used to commit to the polynomial of hashes
        sendmsg['hashpolyhat'] = objectToBytes(self.hashpolyhat, self.group)
        #List of witnesses to the evaluation of k+1 different points on the polynomial f(j,y) (which is also f(x,j))
        sendmsg['witnesses'] = objectToBytes(self.witnessvectors[j], self.group)
        #The polynomial (degree t) f(x,j)
        sendmsg['poly'] = objectToBytes(self.projas[j], self.group)
        #The polynomial (degree t) used to commit to f(x,j)
        sendmsg['polyhat'] = objectToBytes(self.projahats[j], self.group)
        return json.dumps(sendmsg)
    



