#coding:utf-8

#sudo mn --custom exp3.py


from mininet.net import Mininet
from mininet.topo import LinearTopo
 
# 四个交换机每个下边挂载一个主机
 
Linear4 = LinearTopo(k=4)
net = Mininet(topo=Linear4)
net.start()
# net.pingAll()
# net.stop()
 
# single,3
 
# from mininet.topo import SingleSwitchTopo
 
# Single3 = SingleSwitchTopo(k=3)
# net = Mininet(topo=Single3)
# net.start()
# net.pingAll()
# net.stop()
 
 
# # tree,depth=2,fanout=2
 
# from mininet.topolib import TreeTopo
 
# Tree22 = TreeTopo(depth=2, fanout=2)
# net = Mininet(topo=Tree22)
# net.start()
# net.pingAll()
# net.stop()
 
# # create 1 switch,2 host,set hosts IP
 
# net = Mininet()
 
# # Creating nodes in the network
# c0 = net.addController()
# h0 = net.addHost('h0')
# s0 = net.addSwitch('s0')
# h1 = net.addHost('h1')
# # Creating links between nodes in network
# net.addLink(h0, s0)
# net.addLink(h1, s0)
# # configuration of IP address in interfaces
# h0.setIP('192.168.1.1', 24)
# h1.setIP('192.168.1.2', 24)
 
# net.start()
# net.pingAll()
# net.stop()
 
# # add more limits to the host
 
# from mininet.net import Mininet
# from mininet.node import CPULimitedHost
# from mininet.link import TCLink
 
# net = Mininet(host=CPULimitedHost, link=TCLink)
# # Creating nodes in the network
# c0 = net.addController()
# s0 = net.addSwitch('s0')
# h0 = net.addHost('h0')
# h1 = net.addHost('h1', cpu=0.5)
# h2 = net.addHost('h2', cpu=0.5)
# net.addLink(s0, h0, bw=10, delay='5ms',max_queue_size=1000, loss=10, use_htb=True)
# net.addLink(s0, h1)
# net.addLink(s0, h2)
# net.start()
# net.pingAll()
# net.stop()