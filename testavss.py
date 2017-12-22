from VssDealer import *
from VssRecipient import *

alpha = group.random(ZR, seed=seed)
alpha2 = group.random(ZR, seed=seed)
pkg = group.random(G1, seed=seed)
pkg2 = group.random(G1, seed=seed)
pkh = group.random(G1, seed=seed)
pkh2 = group.random(G1, seed=seed)
t = 3
k = 5
pk = []
pk2 = []
for i in range(t+1):
    pk.append(pkg**(alpha**i))
for i in range(t+1):
    pk.append(pkh**(alpha**i))
for i in range(k+1):
    pk2.append(pkg2**(alpha2**i))
for i in range(k+1):
    pk2.append(pkh2**(alpha2**i))

#Initialize Players
dealer = VssDealer(k=5, t=3, secret=42, pk=pk, pk2=pk2)
p1 = VssRecipient(k=5, t=3, nodeid=1, pk=pk, pk2=pk2)
p2 = VssRecipient(k=5, t=3, nodeid=2, pk=pk, pk2=pk2)
p3 = VssRecipient(k=5, t=3, nodeid=3, pk=pk, pk2=pk2)
p4 = VssRecipient(k=5, t=3, nodeid=4, pk=pk, pk2=pk2)
p5 = VssRecipient(k=5, t=3, nodeid=5, pk=pk, pk2=pk2)

#Deal out send messages
p1.receive_msg(dealer.send_sendmsg(1))
p2.receive_msg(dealer.send_sendmsg(2))
p3.receive_msg(dealer.send_sendmsg(3))
p4.receive_msg(dealer.send_sendmsg(4))
p5.receive_msg(dealer.send_sendmsg(5))

#Players send out echo messages
p1.receive_msg(p2.send_echomsg())
p1.receive_msg(p3.send_echomsg())
p1.receive_msg(p4.send_echomsg())
p1.receive_msg(p5.send_echomsg())

p2.receive_msg(p1.send_echomsg())
p2.receive_msg(p3.send_echomsg())
p2.receive_msg(p4.send_echomsg())
p2.receive_msg(p5.send_echomsg())

p3.receive_msg(p1.send_echomsg())
p3.receive_msg(p2.send_echomsg())
p3.receive_msg(p4.send_echomsg())
p3.receive_msg(p5.send_echomsg())

p4.receive_msg(p1.send_echomsg())
p4.receive_msg(p2.send_echomsg())
p4.receive_msg(p3.send_echomsg())
p4.receive_msg(p5.send_echomsg())

p5.receive_msg(p1.send_echomsg())
p5.receive_msg(p2.send_echomsg())
p5.receive_msg(p3.send_echomsg())
p5.receive_msg(p4.send_echomsg())

#Players send out ready messages
p1.receive_msg(p2.send_readymsg(1))
p1.receive_msg(p3.send_readymsg(1))
p1.receive_msg(p4.send_readymsg(1))
p1.receive_msg(p5.send_readymsg(1))

p2.receive_msg(p1.send_readymsg(2))
p2.receive_msg(p3.send_readymsg(2))
p2.receive_msg(p4.send_readymsg(2))
p2.receive_msg(p5.send_readymsg(2))

p3.receive_msg(p1.send_readymsg(3))
p3.receive_msg(p2.send_readymsg(3))
p3.receive_msg(p4.send_readymsg(3))
p3.receive_msg(p5.send_readymsg(3))

p4.receive_msg(p1.send_readymsg(4))
p4.receive_msg(p2.send_readymsg(4))
p4.receive_msg(p3.send_readymsg(4))
p4.receive_msg(p5.send_readymsg(4))

p5.receive_msg(p1.send_readymsg(5))
p5.receive_msg(p2.send_readymsg(5))
p5.receive_msg(p3.send_readymsg(5))
p5.receive_msg(p4.send_readymsg(5))

#END SH PHASE

secretcoords = []
secretcoords.append([1, p1.send_recsharemsg()['polypoint']])
secretcoords.append([2, p2.send_recsharemsg()['polypoint']])
secretcoords.append([3, p3.send_recsharemsg()['polypoint']])
secretcoords.append([4, p4.send_recsharemsg()['polypoint']])
print "The secret is: " + str(interpolate_at_x(secretcoords,0))
