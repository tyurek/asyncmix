from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random
from helperfunctions import *

#group = PairingGroup('SS512')
#group = PairingGroup('MNT159')
#group = PairingGroup('MNT224')


class PolyCommitPed:
    def __init__ (self, t, pk, group, symflag, seed=None):
        self.group = group
        self.pk = pk
        self.g = pk[0]
        #if str(self.group.groupType()) == 'SS512' or str(self.group.groupType()) == 'SS1024' or str(self.group.groupType()) == 'SS1536':
        if symflag:
            self.h = pk[t+1]
            self.symmetric = True
        #elif str(self.group.groupType()) == 'MNT159' or str(self.group.groupType()) == 'MNT224' or str(self.group.groupType()) == 'BN256':
        elif not symflag:
            self.h = pk[t+3]
            self.symmetric = False
        else:
            print "Error: Invalid Curve Specified"
            return
        self.t = t
        self.seed = seed
        self.ONE = group.random(ZR)*0+1
        self.c = self.ONE

    def commit (self, poly, secretpoly):
        #secretpoly is the polynomial phi hat which is used to make the polynomial commitment
        if self.symmetric:
            fudge = 0
        else:
            fudge = 2
        c = self.ONE
        i = 0
        for item in self.pk[:self.t+1]:
            c *= item ** poly[i]
            i += 1
        i = 0
        for item in self.pk[self.t+1+fudge:]:
            c *= item ** secretpoly[i]
            i += 1
        #c should be equivalent to (self.g **(f(poly, self.alpha))) * (self.h **(f(self.secretpoly, self.alpha)))
        return c

    #def open (self):
    #    return {'c': self.c, 'poly': self.poly, 'secretpoly': self.secretpoly} 

    def verify_poly (self, c, poly, secretpoly):
        if self.symmetric:
            fudge = 0
        else:
            fudge = 2
        tempc = self.ONE
        i = 0
        for item in self.pk[:self.t+1]:
            tempc *= item ** poly[i]
            i += 1
        i = 0
        for item in self.pk[self.t+1+fudge:]:
            tempc *= item ** secretpoly[i]
            i += 1
        return c == tempc

    def create_witness(self, poly, secretpoly, i):
        if self.symmetric:
            psi = polynomial_divide([poly[0] - f(poly,i)] + poly[1:], [self.ONE*i*-1,self.ONE])
            psihat = polynomial_divide([secretpoly[0] - f(secretpoly,i)] + secretpoly[1:], [self.ONE*i*-1,self.ONE])
            witness = self.ONE
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
        else:
            psi = polynomial_divide([poly[0] - f(poly,i)] + poly[1:], [self.ONE*i*-1,self.ONE])
            psihat = polynomial_divide([secretpoly[0] - f(secretpoly,i)] + secretpoly[1:], [self.ONE*i*-1,self.ONE])
            witness = self.ONE
            j = 0
            for item in self.pk[:self.t]:
                witness *= item ** psi[j]
                j += 1
            j = 0
            for item in self.pk[self.t+3:self.t+3 + self.t]:
                witness *= item ** psihat[j]
                j += 1
            return witness

    def verify_eval(self, c, i, polyeval, secretpolyeval, witness):
        if self.symmetric:
            lhs =  self.group.pair_prod(c, self.g)
            rhs = self.group.pair_prod(witness, self.pk[1] / (self.g ** i)) * self.group.pair_prod(self.g**polyeval * self.h**secretpolyeval, self.g)
            return lhs == rhs
        else:
            #self.pk[self.t + 1] is ghat in G2
            lhs =  self.group.pair_prod(c, self.pk[self.t + 1])
            rhs = self.group.pair_prod(witness, self.pk[self.t + 2] / (self.pk[self.t + 1] ** i)) * self.group.pair_prod(self.g**polyeval * self.h**secretpolyeval, self.pk[self.t + 1])
            return  lhs == rhs
