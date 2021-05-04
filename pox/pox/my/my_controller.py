#!/usr/bin/python
# Copyright 2012 William Yu
# wyu@ateneo.edu
#
# This file is part of POX.
#
# POX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# POX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with POX. If not, see <http://www.gnu.org/licenses/>.
#

"""
This is a demonstration file created to show how to obtain flow
and port statistics from OpenFlow 1.0-enabled switches. The flow
statistics handler contains a summary of web-only traffic.
"""

# standard includes
from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str, str_to_dpid
from pox.lib.util import str_to_bool
import time
import csv
import numpy as np
import pandas as pd


# include as part of the betta branch
from pox.openflow.of_json import *

log = core.getLogger()
_flood_delay = 0
bw_util = []


with open('ports_stats.csv', 'w', newline='') as file:
    header = ['sw',
              'collisions',
              'port_no',
              'rx_bytes',
              'rx_crc_err',
              'rx_dropped',
              'rx_errors',
              'rx_frame_err',
              'rx_over_err',
              'rx_packets',
              'tx_bytes',
              'tx_dropped',
              'tx_errors',
              'tx_packets']
    writer = csv.writer(file)
    writer.writerow(header)


class Tutorial(object):
    """
  A Tutorial object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """

    def __init__(self, connection):
        # Keep track of the connection to the switch so that we can
        # send it messages!
        self.connection = connection

        # This binds our PacketIn event listener
        connection.addListeners(self)

        # Use this table to keep track of which ethernet address is on
        # which switch port (keys are MACs, values are ports).
        self.mac_to_port = {}

    def resend_packet(self, packet_in, out_port):
        """
    Instructs the switch to resend a packet that it had sent to us.
    "packet_in" is the ofp_packet_in object the switch had sent to the
    controller due to a table-miss.
    """
        msg = of.ofp_packet_out()
        msg.data = packet_in

        # Add an action to send to the specified port
        action = of.ofp_action_output(port=out_port)
        msg.actions.append(action)

        # Send message to switch
        self.connection.send(msg)

    def act_like_hub(self, packet, packet_in):
        """
    Implement hub-like behavior -- send all packets to all ports besides
    the input port.
    """

        # We want to output to all ports -- we do that using the special
        # OFPP_ALL port as the output port.  (We could have also used
        # OFPP_FLOOD.)
        self.resend_packet(packet_in, of.OFPP_ALL)

        # Note that if we didn't get a valid buffer_id, a slightly better
        # implementation would check that we got the full data before
        # sending it (len(packet_in.data) should be == packet_in.total_len)).

    def act_like_switch(self, packet, packet_in):
        """
    Implement switch-like behavior.
    """

        """ # DELETE THIS LINE TO START WORKING ON THIS (AND THE ONE BELOW!) #
    # Here's some psuedocode to start you off implementing a learning
    # switch.  You'll need to rewrite it as real Python code.
    # Learn the port for the source MAC
    self.mac_to_port ... <add or update entry>
    if the port associated with the destination MAC of the packet is known:
      # Send packet out the associated port
      self.resend_packet(packet_in, ...)
      # Once you have the above working, try pushing a flow entry
      # instead of resending the packet (comment out the above and
      # uncomment and complete the below.)
      log.debug("Installing flow...")
      # Maybe the log statement should have source/destination/port?
      #msg = of.ofp_flow_mod()
      #
      ## Set fields to match received packet
      #msg.match = of.ofp_match.from_packet(packet)
      #
      #< Set other fields of flow_mod (timeouts? buffer_id?) >
      #
      #< Add an output action, and send -- similar to resend_packet() >
    else:
      # Flood the packet out everything but the input port
      # This part looks familiar, right?
      self.resend_packet(packet_in, of.OFPP_ALL)
    """  # DELETE THIS LINE TO START WORKING ON THIS #

    def _handle_PacketIn(self, event):
        """
    Handles packet in messages from the switch.
    """

        packet = event.parsed  # This is the parsed packet data.
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return

        packet_in = event.ofp  # The actual ofp_packet_in message.

        # Comment out the following line and uncomment the one after
        # when starting the exercise.
        self.act_like_hub(packet, packet_in)
        # self.act_like_switch(packet, packet_in)


class LearningSwitch(object):
    """
  The learning switch "brain" associated with a single OpenFlow switch.
  When we see a packet, we'd like to output it on a port which will
  eventually lead to the destination.  To accomplish this, we build a
  table that maps addresses to ports.
  We populate the table by observing traffic.  When we see a packet
  from some source coming from some port, we know that source is out
  that port.
  When we want to forward traffic, we look up the desintation in our
  table.  If we don't know the port, we simply send the message out
  all ports except the one it came in on.  (In the presence of loops,
  this is bad!).
  In short, our algorithm looks like this:
  For each packet from the switch:
  1) Use source address and switch port to update address/port table
  2) Is transparent = False and either Ethertype is LLDP or the packet's
     destination address is a Bridge Filtered address?
     Yes:
        2a) Drop packet -- don't forward link-local traffic (LLDP, 802.1x)
            DONE
  3) Is destination multicast?
     Yes:
        3a) Flood the packet
            DONE
  4) Port for destination address in our address/port table?
     No:
        4a) Flood the packet
            DONE
  5) Is output port the same as input port?
     Yes:
        5a) Drop packet and similar ones for a while
  6) Install flow table entry in the switch so that this
     flow goes out the appopriate port
     6a) Send the packet out appropriate port
  """

    def __init__(self, connection, transparent):
        # Switch we'll be adding L2 learning switch capabilities to
        self.connection = connection
        self.transparent = transparent

        # Our table
        self.macToPort = {}

        # We want to hear PacketIn messages, so we listen
        # to the connection
        connection.addListeners(self)

        # We just use this to know when to log a helpful message
        self.hold_down_expired = _flood_delay == 0

        # log.debug("Initializing LearningSwitch, transparent=%s",
        #          str(self.transparent))

    def _handle_PacketIn(self, event):
        """
    Handle packet in messages from the switch to implement above algorithm.
    """

        packet = event.parsed

        def flood(message=None):
            """ Floods the packet """
            msg = of.ofp_packet_out()
            if time.time() - self.connection.connect_time >= _flood_delay:
                # Only flood if we've been connected for a little while...

                if self.hold_down_expired is False:
                    # Oh yes it is!
                    self.hold_down_expired = True
                    log.info("%s: Flood hold-down expired -- flooding",
                             dpid_to_str(event.dpid))

                if message is not None: log.debug(message)
                # log.debug("%i: flood %s -> %s", event.dpid,packet.src,packet.dst)
                # OFPP_FLOOD is optional; on some switches you may need to change
                # this to OFPP_ALL.
                msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            else:
                pass
                # log.info("Holding down flood for %s", dpid_to_str(event.dpid))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        def drop(duration=None):
            """
      Drops this packet and optionally installs a flow to continue
      dropping similar ones for a while
      """
            if duration is not None:
                if not isinstance(duration, tuple):
                    duration = (duration, duration)
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(packet)
                msg.idle_timeout = duration[0]
                msg.hard_timeout = duration[1]
                msg.buffer_id = event.ofp.buffer_id
                self.connection.send(msg)
            elif event.ofp.buffer_id is not None:
                msg = of.ofp_packet_out()
                msg.buffer_id = event.ofp.buffer_id
                msg.in_port = event.port
                self.connection.send(msg)

        self.macToPort[packet.src] = event.port  # 1

        if not self.transparent:  # 2
            if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
                drop()  # 2a
                return

        if packet.dst.is_multicast:
            flood()  # 3a
        else:
            if packet.dst not in self.macToPort:  # 4
                flood("Port for %s unknown -- flooding" % (packet.dst,))  # 4a
            else:
                port = self.macToPort[packet.dst]
                if port == event.port:  # 5
                    # 5a
                    log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
                                % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
                    drop(10)
                    return
                # 6
                log.debug("installing flow for %s.%i -> %s.%i" %
                          (packet.src, event.port, packet.dst, port))
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(packet, event.port)
                msg.idle_timeout = 10
                msg.hard_timeout = 30
                msg.actions.append(of.ofp_action_output(port=port))
                msg.data = event.ofp  # 6a
                self.connection.send(msg)


class l2_learning(object):
    """
  Waits for OpenFlow switches to connect and makes them learning switches.
  """

    def __init__(self, transparent=False, ignore=None):
        """
    Initialize
    See LearningSwitch for meaning of 'transparent'
    'ignore' is an optional list/set of DPIDs to ignore
    """
        core.openflow.addListeners(self)
        self.transparent = transparent
        self.ignore = set(ignore) if ignore else ()

    def _handle_ConnectionUp(self, event):
        if event.dpid in self.ignore:
            log.debug("Ignoring connection %s" % (event.connection,))
            return
        log.debug("Connection %s" % (event.connection,))
        LearningSwitch(event.connection, self.transparent)


# handler for timer function that sends the requests to all the
# switches connected to the controller.
def create_dataset():

    df = pd.read_csv('ports_stats.csv', usecols=[0, 2, 3])
    bw = []

    if len(df) > 50:
        for i in range(6):
            byte_port1 = df[(df['sw'] == '00-00-00-00-00-0'+str(i+1)) & (df['port_no'] == 1)]['rx_bytes'].tolist()
            bw_port1 = byte_port1[1]-byte_port1[0]
            byte_port2 = df[(df['sw'] == '00-00-00-00-00-0'+str(i+1)) & (df['port_no'] == 2)]['rx_bytes'].tolist()
            bw_port2 = byte_port2[1]-byte_port2[0]
            byte_port3 = df[(df['sw'] == '00-00-00-00-00-0'+str(i+1)) & (df['port_no'] == 3)]['rx_bytes'].tolist()
            bw_port3 = byte_port3[1]-byte_port3[0]
            byte_port4 = df[(df['sw'] == '00-00-00-00-00-0'+str(i+1)) & (df['port_no'] == 4)]['rx_bytes'].tolist()
            if len(byte_port4) == 0:
                bw.extend([bw_port1, bw_port2, bw_port3])
            else:
                bw_port4 = byte_port4[1] - byte_port4[0]
                bw.extend([bw_port1, bw_port2, bw_port3, bw_port4])
        f = open('ports_stats.csv', "w")
        f.truncate()
        f.close
    else:
        print('wait for another 10 seconds')

    return bw



def _timer_func():
    for connection in core.openflow._connections.values():
        connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
        connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    log.debug("Sent %i flow/port stats request(s)", len(core.openflow._connections))


# handler to display flow statistics received in JSON format
# structure of event.stats is defined by ofp_flow_stats()
def _handle_flowstats_received(event):
    stats = flow_stats_to_list(event.stats)
    log.debug("FlowStatsReceived from %s: %s",
              dpidToStr(event.connection.dpid), stats)

    # Get number of bytes/packets in flows for web traffic only
    web_bytes = 0
    web_flows = 0
    web_packet = 0
    log.info(event.stats)
    for f in event.stats:
        if f.match.tp_dst == 80 or f.match.tp_src == 80:
            web_bytes += f.byte_count
            web_packet += f.packet_count
            web_flows += 1
    log.info("Web traffic from %s: %s bytes (%s packets) over %s flows",
             dpidToStr(event.connection.dpid), web_bytes, web_packet, web_flows)


# handler to display port statistics received in JSON format
def _handle_portstats_received(event):
    stats = flow_stats_to_list(event.stats)
    id = dpidToStr(event.connection.dpid)
    log.debug(type(stats))
    log.debug("PortStatsReceived from %s: %s",
              id, stats)
    with open('ports_stats.csv', 'a+', newline='') as file:
        header = ['sw',
                  'collisions',
                  'port_no',
                  'rx_bytes',
                  'rx_crc_err',
                  'rx_dropped',
                  'rx_errors',
                  'rx_frame_err',
                  'rx_over_err',
                  'rx_packets',
                  'tx_bytes',
                  'tx_dropped',
                  'tx_errors',
                  'tx_packets']
        writer = csv.DictWriter(file, fieldnames=header)
        for line in stats:
            line['sw'] = id
            writer.writerow(line)



# main functiont to launch the module
def launch():
    from pox.lib.recoco import Timer

    def start_switch(event):
        log.debug("Controlling %s" % (event.connection,))
        Tutorial(event.connection)

    # attach handsers to listners
    core.registerNew(l2_learning, str_to_bool(False), None)
    core.openflow.addListenerByName("FlowStatsReceived",
                                    _handle_flowstats_received)
    core.openflow.addListenerByName("PortStatsReceived",
                                    _handle_portstats_received)

    # timer set to execute every five seconds
    Timer(10, _timer_func, recurring=True)
    global bw_util
    bw_util.extend(create_dataset())
    bw_util = np.array(bw_util).reshape(-1, 20)