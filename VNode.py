from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random
import hashlib
from PolyCommitPed import *
from helperfunctions import *

group = PairingGroup('SS512')
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
class VNode:
    #to avoid indexing hell, when scaling this to multiple dimensions, just make new objects
    def __init__ (self, k, t, secret, nodeid, pk, pk2, group=group, seed=None):
        # Random polynomial coefficients constructed in the form
        #[c       x        x^2        ...  x^t
        # y       xy       x^2y       ...  x^t*y
        # y^2     x*y^2    x^2*y^2    ...  x^t*y^2
        # ...     ...      ...        ...  ...
        # y^t     x*y^t    x^2*y^t    ...  x^t*y^t]
        # This is structured so that t+1 points are needed to reconstruct the polynomial
        self.commitments = []
        self.witnessvectors = []
        self.projas = []
        self.projahats = []
        self.hashpoly = []
        self.t = t
        self.k = k
        self.nodeid = nodeid
        self.a = [list(group.random(ZR, count=t+1, seed=seed)) for i in range(t+1)]
        self.ahat = [list(group.random(ZR, count=t+1, seed=seed)) for i in range(t+1)]
        #make the polynomials symmetric
        for i in range(t+1):
            for j in range(i):
                self.a[i][j] = self.a[j][i]
                self.ahat[i][j] = self.ahat[j][i]
        self.a[0][0] = secret
        self.pc = PolyCommitPed(t=t, pk=pk, group=group)
        self.pc2 = PolyCommitPed(t=t, pk=pk2, group=group)
        for j in range(k+1):
            #Create lists of polynomial projections at different points for ease of use
            self.projas.append(projf(self.a, j))
            self.projahats.append(projf(self.ahat, j))
            #Create commitments for each of these projections
            self.commitments.append(self.pc.commit(self.projas[j], self.projahats[j]))
        #A different loop is needed for witnesses so that all projections are already calculated
        for j in range(k+1):
            witnesses = []
            for i in range(k+1):
                witnesses.append(self.pc.create_witness(self.projas[i], self.projahats[i], j))
            self.witnessvectors.append(witnesses)
        #Create the polynomial of hashes of commitments and commit to it
        for c in self.commitments:
            #not sure if there's an agreed upon way to hash a pairing element to something outside the group
            #so I SHA256 hash the bitstring representation of the element
            self.hashpoly.append(hexstring_to_ZR(hashlib.sha256(group.serialize(c)).hexdigest()))
        self.hashpolyhat = list(group.random(ZR, count=t+1, seed=seed))
        self.hashcommit = self.pc2.commit(self.hashpoly, self.hashpolyhat)

    #send a "send" message to party member j
    def send_sendmsg(self, j):
        sendmsg = {}
        #One commitment to the polynomial of hashes of commitments
        sendmsg['hashcommit'] = self.hashcommit
        #List of commitments to casted polynomials, k+1 commitments in all (where k is the number of participants)
        sendmsg['commitments'] = self.commitments
        #Polynomial (degree t) used to commit to the polynomial of hashes
        sendmsg['hashpolyhat'] = self.hashpolyhat
        #List of witnesses to the evaluation of k+1 different points on the polynomial f(j,y) (which is also f(x,j))
        sendmsg['witnesses'] = self.witnessvectors[j]
        #The polynomial (degree t) f(x,j)
        sendmsg['poly'] = self.projas[j]
        #The polynomial (degree t) used to commit to f(x,j)
        sendmsg['polyhat'] = self.projahats[j]
        return sendmsg
    
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
        hashpoly = []
        for c in sendmsg['commitments']:
            hashpoly.append(hexstring_to_ZR(hashlib.sha256(group.serialize(c)).hexdigest()))
        hashpolycommitmentvalid = self.pc2.verify_poly(sendmsg['hashcommit'], hashpoly, sendmsg['hashpolyhat'])
        #verify correctness of regular polynomial
        polyvalid = self.pc.verify_poly(sendmsg['commitments'][self.nodeid], sendmsg['poly'], sendmsg['polyhat'])
        return commitmentsvalid and witnessesvalid and hashpolycommitmentvalid and polyvalid


