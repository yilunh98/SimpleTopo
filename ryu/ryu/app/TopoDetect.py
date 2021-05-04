from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick

from ryu.ofproto import ofproto_v1_3

from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER,DEAD_DISPATCHER,HANDSHAKE_DISPATCHER 
from ryu.controller.handler import set_ev_cls

from ryu.lib import hub
from ryu.lib.packet import packet,ethernet

from ryu.topology.switches import Switches
from ryu.topology.switches import LLDPPacket

import time

ECHO_REQUEST_INTERVAL = 0.05
DELAY_DETECTING_PERIOD = 5

class DelayDetect(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self,*args,**kwargs):
        super(DelayDetect,self).__init__(*args,**kwargs)
        self.name = "delay"

        self.topology = lookup_service_brick("topology") 
        self.switches = lookup_service_brick("switches") 

        self.dpid2switch = {} 
        self.dpid2echoDelay = {}

        self.src_sport_dst2Delay = {} 

        self.detector_thread = hub.spawn(self._detector)

    def _detector(self):
        while True:
            if self.topology == None:
                self.topology = lookup_service_brick("topology")
            if self.topology.net_flag:
                print("------------------_detector------------------")
                self._send_echo_request()
                self.get_link_delay()
                if self.topology.net_flag:
                    try:
                        self.show_delay()
                    except Exception as err:
                        print("------------------Detect delay failure!!!------------------")
            hub.sleep(DELAY_DETECTING_PERIOD) 

    def get_link_delay(self):
 
        print("--------------get_link_delay-----------")
        for src_sport_dst in self.src_sport_dst2Delay.keys():
                src,sport,dst = tuple(map(eval,src_sport_dst.split("-")))
                if src in self.dpid2echoDelay.keys() and dst in self.dpid2echoDelay.keys():
                    sid,did = self.topology.dpid2id[src],self.topology.dpid2id[dst]
                    if self.topology.net_topo[sid][did] != 0:
                        if self.topology.net_topo[sid][did][0] == sport:
                            s_d_delay = self.src_sport_dst2Delay[src_sport_dst]-(self.dpid2echoDelay[src]+self.dpid2echoDelay[dst])/2;
                            if s_d_delay < 0: 
                                continue
                            self.topology.net_topo[sid][did][1] = self.src_sport_dst2Delay[src_sport_dst]-(self.dpid2echoDelay[src]+self.dpid2echoDelay[dst])/2


    def _send_echo_request(self):
        for datapath in self.dpid2switch.values():
            parser = datapath.ofproto_parser
            echo_req = parser.OFPEchoRequest(datapath,data=bytes("%.12f"%time.time(),encoding="utf8")) 

            datapath.send_msg(echo_req)

            hub.sleep(ECHO_REQUEST_INTERVAL)

    @set_ev_cls(ofp_event.EventOFPEchoReply,[MAIN_DISPATCHER,CONFIG_DISPATCHER,HANDSHAKE_DISPATCHER])
    def echo_reply_handler(self,ev):
        """
              Controller
                  |    
     echo latency |  
                 '|'
                   Switch      
        """
        now_timestamp = time.time()
        try:
            echo_delay = now_timestamp - eval(ev.msg.data)
            self.dpid2echoDelay[ev.msg.datapath.id] = echo_delay
        except:
            return


    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,ev): 
        """
                      Controller
                    |        /|\    
                   \|/         |
                Switch----->Switch
        """
        msg = ev.msg
        try:
            src_dpid,src_outport = LLDPPacket.lldp_parse(msg.data) 
            dst_dpid = msg.datapath.id
            dst_inport = msg.match['in_port']
            if self.switches is None:
                self.switches = lookup_service_brick("switches") 

            for port in self.switches.ports.keys(): 
                if src_dpid == port.dpid and src_outport == port.port_no: 
                    port_data = self.switches.ports[port] 
                    timestamp = port_data.timestamp
                    if timestamp:
                        delay = time.time() - timestamp
                        self._save_delay_data(src=src_dpid,dst=dst_dpid,src_port=src_outport,lldpdealy=delay)
        except:
            return

    def _save_delay_data(self,src,dst,src_port,lldpdealy):
        key = "%s-%s-%s"%(src,src_port,dst)
        self.src_sport_dst2Delay[key] = lldpdealy

    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.dpid2switch:
                self.logger.debug('Register datapath: %016x', datapath.id)
                self.dpid2switch[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.dpid2switch:
                self.logger.debug('Unregister datapath: %016x', datapath.id)
                del self.dpid2switch[datapath.id]

        if self.topology == None:
            self.topology = lookup_service_brick("topology")
        print("-----------------------_state_change_handler-----------------------")
        print(self.topology.show_topology())
        print(self.switches)

    def show_delay(self):
        print("-----------------------show echo delay-----------------------")
        for key,val in self.dpid2echoDelay.items():
            print("s%d----%.12f"%(key,val))
        print("-----------------------show LLDP delay-----------------------")
        for key,val in self.src_sport_dst2Delay.items():
            print("%s----%.12f"%(key,val))