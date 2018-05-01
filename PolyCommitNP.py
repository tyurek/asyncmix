from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random
from helperfunctions import *
from math import floor

#group = PairingGroup('SS512')
#group = PairingGroup('MNT159')
#group = PairingGroup('MNT224')


class PolyCommitNP:
    def __init__ (self, t, pk, group, seed=None):
        self.group = group
        self.g = pk[0]
        self.h = pk[1]
        self.t = t
        self.seed = seed
        self.ONE = group.random(ZR)*0+1

    def commit (self, poly, secretpoly):
        #initPP?
        cs = []
        for i in range(self.t+1):
            c = (self.g**poly[i])*(self.h**secretpoly[i])
            cs.append(c)
        return cs

    def verify_eval(self, c, i, polyeval, secretpolyeval, witness=None):
        lhs = self.ONE
        for j in range(len(c)):
            lhs = lhs * c[j]**(i**j)
        rhs = (self.g**polyeval)*(self.h**secretpolyeval)
        return  lhs == rhs
