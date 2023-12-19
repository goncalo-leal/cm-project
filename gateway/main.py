# main.py -- put your code here!
# from network import LoRa
import network
import socket
import time
# from lib.utils import parse_packet,compose_packet,icmp_request
from lib.utils import buffer, parse_packet, icmp_request, tcp_syn, tcp_ack, config, decrease_or_discard, exist_in_buffer, arp_request,discard_tcp,discard_arp,discard_icmp,log_message,tcp_synack,HEADER_PROTOCOLS,tcp_fin
import _thread
import json

# COM4

lora, s = config()
mac = lora.mac()

# caracteristics of own device
board = {
    "name": "board1",
    "mac": lora.mac(),
}



known_nodes = []
active_nodes = []
arp_timeout = 60
keepalive = 30
mac_to_devices = {}

messages = [{
    "device": "board14",
    "message": "color|cyan",
},
{
    "device": "all",
    "message": "status|0",
}]

next_message = None
packet_loss = 0

info = None
while True:
    log_message("buffer",buffer)

    # Scanning for new nodes
    if arp_timeout == 60:
        _thread.start_new_thread(arp_request, (mac,board["name"],))
        arp_timeout = 0


    # Testing connectivity
    if len(active_nodes) != len(known_nodes) or keepalive == 30:
        for node in known_nodes:
            if node not in active_nodes and not exist_in_buffer([(0, 0), (3, mac), (4, node)]):
                _thread.start_new_thread(icmp_request, (mac, node,))


    # if there is a message send through tcp
    if next_message and len(active_nodes) > 0:
        devices_to_mac = {v: k for k, v in mac_to_devices.items()}        
        if next_message["device"] == "all":
            for node in active_nodes:
                if not exist_in_buffer([(0, 0x2), (3, mac), (4, node)]):
                    _thread.start_new_thread(tcp_syn, (mac, node, ))
        elif next_message["device"] in devices_to_mac.keys():
            if not exist_in_buffer([(0, 0x2), (3, mac), (4, devices_to_mac[next_message["device"]])]):
                _thread.start_new_thread(
                    tcp_syn, (mac, devices_to_mac[next_message["device"]], )
                )
    else:
        if len(messages) > 0 and not next_message:
            next_message = messages.pop(0)

            

    # receive packet
    packet = s.recv(128)

    # check if packet is not empty
    if packet:
        print("packet:  ",packet)

        try:
            # unpack the packet that received
            data = parse_packet(packet)
        except Exception:
            # unpack the packet that received, with param, which means is a tcp packet
            data = parse_packet(packet, param=True)
        
        log_message("receiver",data)

        # ARP
        # check if ARP Reply is well done
        if data[0] == 0x7 and data[4] == mac:
            known_nodes.append(data[3])
            mac_to_devices[data[3]] = data[5].decode('utf-8').rstrip('\x00')   # Unpack this to a string this is in bytes
            discard_arp(mac,data[3])

        # ICMP
        # check if ICMP Reply is well done
        elif data[0] == 0x1 and data[4] == mac and data[3] in known_nodes:
            active_nodes.append(data[3])
            discard_icmp(mac,data[3])


        # TCP
        # synack
        elif data[0] == 0x2 and data[4] == mac and not exist_in_buffer([(0,3),(3,mac),(4,data[3]),(6,(data[5]+1))]):
            _thread.start_new_thread(tcp_synack, (mac, data[3],data[5],))

        # ack
        elif data[0] == 0x3 and data[4] == mac and data[3] in active_nodes and not exist_in_buffer([(0, 0x4), (3, mac), (4, data[3]), (5, data[5]+1),(6,next_message["message"])]):
            # Check if ackID from TCP SynAck is synID from TCP Syn + 1
            syn = exist_in_buffer([
                (0, 0x2), (3, mac), (4, data[3]), (5, data[6]-1)
            ])
            if syn:
                _thread.start_new_thread(
                    tcp_ack, (mac, data[3], data[5], next_message["message"],)
                )

        # fin
        elif data[0] == 0x4 and data[4] == mac and not exist_in_buffer([(0,5),(3,mac),(4,data[3]),(5,(data[5]+1))]):
            # Check if the size and the message are the same
            if len(data[6]) == (data[2] - HEADER_PROTOCOLS[0x4]):
                _thread.start_new_thread(tcp_fin, (mac, data[3],data[5],))    
                info = data[6]
                print("info:    ",json.loads(info))
            else:
                _thread.start_new_thread(tcp_fin, (mac, data[3],0,))  

        elif data[0] == 0x5 and data[4] == mac and data[3] in active_nodes:
            # Check if finID from TCP Fin is ackID from TCP Ack + 1
            ack = exist_in_buffer([
                (0, 0x4), (3, data[4]), (4, data[3]), (5, data[5]-1)
            ])
            if ack:
                log_message("tcp session closed",mac,data[3])
                next_message = None
            else:
                log_message("tcp session failed",mac,data[3])
            
            discard_tcp(mac,data[3])
    
    

    decrease_or_discard(buffer)
    arp_timeout += 1
    keepalive += 1
    time.sleep(1)
