# main.py -- put your code here!
# from network import LoRa
import network
import socket
import time
import pycom
# from lib.utils import parse_packet,compose_packet,icmp_request
from utils import buffer,parse_packet, icmp_request, tcp_syn, tcp_ack, config,decrease_or_discard,exist_in_buffer
import _thread

# COM4

lora, s = config()
mac = lora.mac()


known_nodes = [b'p\xb3\xd5I\x99x1_']
active_nodes = []


while True:

    # Testing connectivity
    if len(active_nodes) != len(known_nodes):
        for node in known_nodes:
            if node not in active_nodes and not exist_in_buffer([(0,0),[3,mac],(4,node)]):
                _thread.start_new_thread(icmp_request, (mac, node,))


    packet = s.recv(64)
    if packet:
        try:
            data = parse_packet(packet)
        except Exception:
            data = parse_packet(packet, param=True)

        if data[0] == 0x1 and data[4] == mac and data[3] in known_nodes:
            active_nodes.append(data[3])

            
    print("Known nodes: ", known_nodes)
    print("Active nodes: ", active_nodes)
    print("Buffer: ", buffer)
    
    buffer = decrease_or_discard(buffer)
    time.sleep(4)
