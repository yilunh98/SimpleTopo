#!/usr/bin/python
#sudo mn --custom exp2.py --controller=remote,ip=127.0.0.1,port=6633


from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, Controller, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.link import TCLink, Intf
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from subprocess import call
from mininet.util import dumpNodeConnections

def myNetwork():
        net = Mininet()
                
        info('***Adding controller\n')
        c0 = net.addController(name='c0', controller=RemoteController, ip='127.0.0.1', protocol='tcp', port=6633)

        info('***Adding switches\n')
        s2 = net.addSwitch('s2', cls=OVSKernelSwitch, dpid='00000000000000000002')
        s1 = net.addSwitch('s1', cls=OVSKernelSwitch, dpid='00000000000000000001')

        info('***Adding host\n')
        h2 = net.addHost('h2',cls=Host, ip='10.0.0.2', defaultRoute=None)
        h3 = net.addHost('h3',cls=Host, ip='10.0.0.3', defaultRoute=None)
        h4 = net.addHost('h4',cls=Host, ip='10.0.0.4', defaultRoute=None)
        h1 = net.addHost('h1',cls=Host, ip='10.0.0.1', defaultRoute=None)
        h5 = net.addHost('h5',cls=Host, ip='10.0.0.5', defaultRoute=None)

        info('***Adding links\n')
        net.addLink(s1,s2)
        net.addLink(s1,h1)
        net.addLink(s1,h2)
        net.addLink(s2,h3)
        net.addLink(s2,h4)
        net.addLink(s2,h5)

        info('***Starting network\n')
        net.build()

        info('***Starting controllers\n')
        for Controller in net.controllers:
                Controller.start()

        info('***Starting switches\n')
        net.get('s2').start([c0])
        net.get('s1').start([c0])

        info('***Post configure switches and hosts\n')

        CLI(net)
        net.stop()

if __name__ == '__main__':
        setLogLevel('info')
        myNetwork()
        # topos = {'mytopo' : (lambda : myNetwork())}


