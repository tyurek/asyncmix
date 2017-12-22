from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random
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

class PolyCommitPed:
    def __init__ (self, t, pk, group=group, seed=None):
        self.group = group
        self.pk = pk
        self.g = pk[0]
        self.h = pk[t+1]
        self.t = t
        self.seed = seed
        self.c = ONE

    def commit (self, poly, secretpoly):
        #secretpoly is the polynomial phi hat which is used to make the polynomial commitment
        c = ONE
        i = 0
        for item in self.pk[:self.t+1]:
            c *= item ** poly[i]
            i += 1
        i = 0
        for item in self.pk[self.t+1:]:
            c *= item ** secretpoly[i]
            i += 1
        #c should be equivalent to (self.g **(f(poly, self.alpha))) * (self.h **(f(self.secretpoly, self.alpha)))
        return c

    #def open (self):
    #    return {'c': self.c, 'poly': self.poly, 'secretpoly': self.secretpoly} 

    def verify_poly (self, c, poly, secretpoly):
        tempc = ONE
        i = 0
        for item in self.pk[:self.t+1]:
            tempc *= item ** poly[i]
            i += 1
        i = 0
        for item in self.pk[self.t+1:]:
            tempc *= item ** secretpoly[i]
            i += 1
        return c == tempc

    def create_witness(self, poly, secretpoly, i):
        psi = polynomial_divide([poly[0] - f(poly,i)] + poly[1:], [ONE*i*-1,ONE])
        psihat = polynomial_divide([secretpoly[0] - f(secretpoly,i)] + secretpoly[1:], [ONE*i*-1,ONE])
        witness = ONE
        j = 0
        for item in self.pk[:self.t]:
            witness *= item ** psi[j]
            j += 1
        j = 0
        #funky indexing is due to the structure of pk and that g^alpha^t and h^alpha^t aren't needed
        for item in self.pk[self.t+1:self.t+1 + self.t]:
            witness *= item ** psihat[j]
            j += 1
        #witness should be equivalent to (self.g **(f(psi, self.alpha))) * (self.h **(f(psihat, self.alpha)))
        return witness

    def verify_eval(self, c, i, polyeval, secretpolyeval, witness):
        lhs =  group.pair_prod(c, self.g)
        rhs = group.pair_prod(witness, self.pk[1] / (self.g ** i)) * group.pair_prod(self.g**polyeval * self.h**secretpolyeval, self.g)
        return lhs == rhs
