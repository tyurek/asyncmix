from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from base64 import encodestring, decodestring
import random


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

#unknown results will occur if denominator does not perfectly divide numerator
#an input of [a,b,c] corresponds to cx^2 + bx + a
def polynomial_divide(numerator, denominator):
    temp = numerator
    factors = []
    while len(temp) >= len(denominator):
        diff = len(temp) - len(denominator)
        factor = temp[len(temp) - 1] / denominator[len(denominator) - 1]
        factors.insert(0, factor)
        for i in range(len(denominator)):
            temp[i+diff] = temp[i+diff] - (factor * denominator[i])
        temp = temp[:len(temp)-1]
    return factors
# Polynomial projection (evaluate the bivariate polynomial at a given y to get a univariate polynomial)
def projf(poly, y, power = 1):
#Note that ZERO ** 0 evaluates to 0 rather than 1, so this function will behave incorrectly when power = 0.
#However, there is no need to call this function that way for this protocol
    y = ONE * y
    t = len(poly)
    out = [ZERO] * t
    for i in range(t):
        for j in range(t):
            if i == 0 and j == 0:
                out[i] += (poly[i][j] ** power) * (y ** (j))
            else:
                out[i] += (poly[i][j]) * (y ** (j))
    return out
# Polynomial evaluation
def f(poly, x):
    if type(poly) is not list:
        return "UNDEFINED"
    y = ZERO
    xx = ONE
    for coeff in poly:
        y += coeff * xx
        xx *= x
    return y
#interpolates a list of cordinates of the form [x,y] and evaulates at given x
def interpolate_at_x(coords, x, order=-1):
    if order == -1:
        order = len(coords)
    xs = []
    sortedcoords = sorted(coords, key=lambda x: x[0])
    for coord in sortedcoords:
        xs.append(coord[0])
    S = set(xs[0:order])
    out = ZERO
    for i in range(order):
        out = out + (lagrange_at_x(S,xs[i],x) * sortedcoords[i][1])
    return out

def lagrange_at_x(S,j,x):
    S = sorted(S)
    assert j in S
    mul = lambda a,b: a*b
    num = reduce(mul, [x - jj  for jj in S if jj != j], ONE)
    den = reduce(mul, [j - jj  for jj in S if jj != j], ONE)
    return num / den
