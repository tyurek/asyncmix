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

def polynomial_multiply_constant(poly1, c):
    #myzero will be appropriate whether we are in ZR or G
    myzero = poly1[0] - poly1[0]
    product = [myzero] * len(poly1)
    for i in range(len(product)):
        product[i] = product[i] + poly1[i] * c
    return product

def polynomial_multiply(poly1, poly2):
    myzero = poly1[0] - poly1[0]
    product = [myzero] * (len(poly1) + len(poly2) -1)
    for i in range(len(poly1)):
        temp = polynomial_multiply_constant(poly2, poly1[i])
        while i > 0:
            temp.insert(0,myzero)
            i -= 1
        product = polynomial_add(product, temp)
    return product

def polynomial_add(poly1, poly2):
    myzero = poly2[0] - poly2[0]
    if len(poly1) >= len(poly2):
        bigger = poly1
        smaller = poly2
    else:
        bigger = poly2
        smaller = poly1
    polysum = [myzero] * len(bigger)
    for i in range(len(bigger)):
        polysum[i] = polysum[i] + bigger[i]
        if i < len(smaller):
            polysum[i] = polysum[i] + smaller[i]
    return polysum

# Polynomial projection (evaluate the bivariate polynomial at a given y to get a univariate polynomial)
def projf(poly, y):
#Note that ZERO ** 0 evaluates to 0 rather than 1, so this function requires some light tweaking to work.
    y = ONE * y
    t = len(poly)
    out = [ZERO] * t
    for i in range(t):
        for j in range(t):
            if j != 0:
                out[i] += (poly[i][j]) * (y ** (j))
            else:
                out[i] += (poly[i][j])
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
    #The following line makes it so this code works for both members of G and ZR
    out = ONE * (coords[0][1] - coords[0][1])
    for i in range(order):
        out = out + (lagrange_at_x(S,xs[i],x) * sortedcoords[i][1])
    return out

#Turns out a separate interpolation function for commitments is unnecessary
#but I'll leave it here in case it's useful later on
def interpolate_commitment_at_x(coords, x, order = -1):
    if order == -1:
        order = len(coords)
    xs = []
    sortedcoords = sorted(coords, key=lambda x: x[0])
    for coord in sortedcoords:
        xs.append(coord[0])
    S = set(xs[0:order])
    out = ONE
    for i in range(order):
        if i == 0:
            out = (sortedcoords[i][1] ** (lagrange_at_x(S,xs[i],x)))
        else:
            out = out * (sortedcoords[i][1] ** (lagrange_at_x(S,xs[i],x)))
    return out

def lagrange_at_x(S,j,x):
    S = sorted(S)
    assert j in S
    mul = lambda a,b: a*b
    num = reduce(mul, [x - jj  for jj in S if jj != j], ONE)
    den = reduce(mul, [j - jj  for jj in S if jj != j], ONE)
    return num / den

def interpolate_poly(coords):
    myone = coords[0][1] / coords[0][1]
    myzero = coords[0][1] - coords[0][1]
    poly = [myzero] * len(coords)
    for i in range(len(coords)):
        temp = [myone]
        for j in range(len(coords)):
            if i == j:
                temp  = polynomial_multiply(temp, [coords[j][1]])
                continue
            temp = polynomial_multiply(temp, [myzero -(coords[j][0] * myone), myone])
            temp = polynomial_divide(temp, [coords[i][0] *myone -coords[j][0] *myone])
        poly = polynomial_add(poly, temp)
    return poly

#this is necessary because ints have a limited size
def hexstring_to_ZR(string):
    i = len(string) - 1
    out = ZERO
    while i >= 0:
        if i > 0:
            temp = ONE * 2
            temp = temp ** (i*4)
        else:
            temp = ONE
        out = out + temp*int(string[i],16)
        i = i - 1
    return out

def intstring_to_ZR(string):
    i = len(string) - 1
    out = ZERO
    while i >= 0:
        if i > 0:
            temp = ONE * 10
            temp = temp ** (i)
        else:
            temp = ONE
        out = out + temp*int(string[i])
        i = i - 1
    return out

#Check that a subset of t+1 points will correctly interpolate to the polynomial which contains all points
def check_commitment_integrity(commitments, t):
    points = []
    for i in commitments:
        points.append([i, commitments[i]])
    out = True
    for i in range(t+1,len(commitments)):
        out = out and (interpolate_at_x(points[:t+1], points[i][0]) == (points[i ][1]))
    return out

