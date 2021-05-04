#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI

from mininet.node import OVSSwitch, Controller, RemoteController


class MyTopo(Topo):
    "Single switch connected to n hosts."

    def build(self):
        # switch1 = self.addSwitch('s1')
        # host1 = self.addHost('h1')
        # host2 = self.addHost('h2')
        # self.addLink(host1, switch1)
        # self.addLink(host2, switch1)

        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')
        switch4 = self.addSwitch('s4')#, stp=True, failMode='standalone')
        switch5 = self.addSwitch('s5')
        switch6 = self.addSwitch('s6')

        host1 = self.addHost('h1')
        host2 = self.addHost('h2')
        host3 = self.addHost('h3')
        host4 = self.addHost('h4')

        self.addLink(host1, switch1)
        self.addLink(host2, switch2)
        self.addLink(switch1, switch3)
        self.addLink(switch3, switch5)
        self.addLink(switch1, switch4)
        self.addLink(switch2, switch3)
        self.addLink(switch2, switch4)
        # self.addLink(switch3, switch6)
        self.addLink(switch4, switch5)
        self.addLink(switch4, switch6)
        self.addLink(host3, switch5)
        self.addLink(host4, switch6)

class SingleSwitchTopo(Topo):
    "Single switch connected to n hosts."
    def build(self, n=2):
        switch = self.addSwitch('s1')
        # Python's range(N) generates 0..N-1
        for h in range(n):
            host = self.addHost('h%s' % (h + 1))
            self.addLink(host, switch)

def simpleTest():
    "Create and test a simple network"
    topo = MyTopo()
    #topo = SingleSwitchTopo(n=4)
    net = Mininet(topo=topo, controller=None)
    net.addController("c0",
                      controller=RemoteController,
                      ip="127.0.0.1",
                      port=6633)


    net.start()

    #print("Dumping host connections")
    #dumpNodeConnections(net.hosts)
    print("Testing network connectivity")
    # net.pingAll()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()
