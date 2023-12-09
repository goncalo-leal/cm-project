import network
import socket
import time
import pycom
# from lib.utils import parse_packet,compose_packet,icmp_request
from utils import buffer,parse_packet, icmp_reply, tcp_syn, tcp_ack, config,decrease_or_discard,exist_in_buffer
import _thread

# COM6

lora, s = config()

mac = lora.mac()

while True:
    try:
        packet = parse_packet(s.recv(64))
    except Exception:
        packet = parse_packet(s.recv(64),True)

    if packet:
        if packet[0] == 0x0 and not exist_in_buffer([(0,1),[3,mac],(4,packet[3])]):
            _thread.start_new_thread(icmp_reply, (mac, packet[3],))
        

    buffer = decrease_or_discard(buffer)
    time.sleep(0.5)
