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

#Class representing a participant in the scheme. t is the threshold and k is the number of participants
class Node:
    def __init__ (self, k, t, secret, nodeid, seed=None):
        # Random polynomial coefficients constructed in the form
        #[c       x        x^2        ...  x^(t-1)
        # y       xy       x^2y       ...  x^(t-1)y
        # y^2     xy^2     x^2y^2     ...  x^(t-1)y^2
        # ...     ...      ...        ...  ...
        # y^(t-1) xy^(t-1) x^2y^(t-1) ...  x^(t-1)y^(t-1)]
        self.a = [list(group.random(ZR, count=t, seed=seed)) for i in range(t)]
        self.a[0][0] = secret
        #Create a list with k ZEROs
        self.SKs = [ZERO] * k
        #SKs[j] contains all the polynomial projections for dimension j
        for j in range(k):
            for i in range(0, k + 1):
                if self.SKs[j] == ZERO:
                    self.SKs[j] = [projf(self.a, i, power=(j+1))]
                else:
                    self.SKs[j].append(projf(self.a, i, power=(j+1)))
        self.nodeid = nodeid
        self.t = t
        self.k = k
        #receivedpoly is the list of one dimensional polynomials received in the first sharing step
        self.receivedpoly = [ZERO] * (k + 1)
        #reconstructionpoints is the list of points needed to reconstruct each second step polynomial
        self.reconstructionpoints = [ZERO] * (k + 1)
        self.sumpoint = [ZERO]

    def get_SK(self, dim, i):
        return self.SKs[dim-1][i]

    def get_nodeid(self):
        return self.nodeid

    def receive_poly(self, poly, sender):
        self.receivedpoly[sender] = poly

    def get_poly(self, sender):
        return self.receivedpoly[sender]

    def receive_reconstruction(self, point, polynum):
        if point[0] == "UNDEFINED" or point[1] == "UNDEFINED":
            return
        if self.reconstructionpoints[polynum] == ZERO:
            self.reconstructionpoints[polynum] = [point]
        else:
            self.reconstructionpoints[polynum].append(point)

    def restore_reconstruction_polys(self):
        mysum = ZERO
        for polynum in range(1,len(self.reconstructionpoints)):
            pointcount = 0
            for point in self.reconstructionpoints[polynum]:
                if point != ZERO:
                    pointcount += 1
            if pointcount < self.t:
                print "error: node "+ str(self.nodeid) + " unable to restore polynomial " + str(polynum) + " due to lack of points. (" \
                    + str(self.t) + " needed, " + str(pointcount) + " found). Final answer will be incorrect"
                self.sumpoint = [self.nodeid, ZERO]
                return
            mysum += (interpolate_at_x(self.reconstructionpoints[polynum], self.nodeid, order=self.t))
        self.sumpoint = [self.nodeid, mysum]

    def get_sumpoint(self):
        return self.sumpoint

