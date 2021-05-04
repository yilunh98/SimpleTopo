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

# include as part of the betta branch
from pox.openflow.of_json import *

log = core.getLogger()


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
        # Here's some psuedocode to start you off implementing a learning
        # switch.  You'll need to rewrite it as real Python code.

        # Learn the port for the source MAC
        if packet.src not in self.mac_to_port:
            log.debug("Learned %s from Port %d!" % (packet.src, packet_in.in_port))
            self.mac_to_port[packet.src] = packet_in.in_port

        if packet.dst in self.mac_to_port:
            # Send packet out the associated port
            log.debug("Flow table hit, sending out packet to Port. %d" % self.mac_to_port[packet.dst])
            self.resend_packet(packet_in, self.mac_to_port[packet.dst])

            log.debug("Installing flow ...")
            log.debug("MATCH: In Port :  %s" % packet_in.in_port)
            log.debug("MATCH: Source MAC :  %s" % packet.src)
            log.debug("MATCH: Destination MAC :  %s" % packet.dst)
            log.debug("ACTION: Out Port :  %s" % self.mac_to_port[packet.dst])

            msg = of.ofp_flow_mod()
            msg.match.in_port = self.mac_to_port[packet.src]
            msg.match.dl_src = packet.src
            msg.match.dl_dst = packet.dst
            msg.actions.append(of.ofp_action_output(port=self.mac_to_port[packet.dst]))
            msg.idle_timeout = 60
            msg.hard_timeout = 600
            msg.buffer_id = packet_in.buffer_id
            self.connection.send(msg)

        else:
            # Flood the packet out everything but the input port
            self.resend_packet(packet_in, of.OFPP_ALL)


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
        #self.act_like_hub(packet, packet_in)
        self.act_like_switch(packet, packet_in)


# handler for timer function that sends the requests to all the
# switches connected to the controller.
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
        # if f.match.tp_dst == 80 or f.match.tp_src == 80:
            web_bytes += f.byte_count
            web_packet += f.packet_count
            web_flows += 1
    log.info("Web traffic from %s: %s bytes (%s packets) over %s flows",
             dpidToStr(event.connection.dpid), web_bytes, web_packet, web_flows)


# handler to display port statistics received in JSON format
def _handle_portstats_received(event):
    stats = flow_stats_to_list(event.stats)
    log.debug("PortStatsReceived from %s: %s",
              dpidToStr(event.connection.dpid), stats)


# main functiont to launch the module
def launch():
    from pox.lib.recoco import Timer

    def start_switch(event):
        log.debug("Controlling %s" % (event.connection,))
        Tutorial(event.connection)

    # attach handsers to listners
    core.openflow.addListenerByName("ConnectionUp", start_switch)
    # core.openflow.addListenerByName("FlowStatsReceived",
    #                                 _handle_flowstats_received)
    core.openflow.addListenerByName("PortStatsReceived",
                                    _handle_portstats_received)

    # timer set to execute every five seconds
    Timer(5, _timer_func, recurring=True)
