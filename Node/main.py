import network
import socket
import time
import pycom
# from lib.utils import parse_packet,compose_packet,icmp_request
from utils import buffer,parse_packet, icmp_reply, tcp_syn, tcp_ack, config,decrease_or_discard,exist_in_buffer,arp_response
import _thread

# COM6

lora, s = config()

mac = lora.mac()

while True:
    packet = s.recv(64)

    if packet:
        try:
            data = parse_packet(packet)
        except Exception:
            data = parse_packet(packet, param=True)

        if data[0] == 0x0 and not exist_in_buffer([(0,1),[3,mac],(4,data[3])]):
            _thread.start_new_thread(icmp_reply, (mac, data[3],))
        elif data[0] == 0x6 and not exist_in_buffer([(0,7),[3,mac],(4,data[3])]):
            _thread.start_new_thread(arp_response, (mac, data[3],))
        

    buffer = decrease_or_discard(buffer)
    time.sleep(0.5)
