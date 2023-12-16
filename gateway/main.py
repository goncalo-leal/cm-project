# main.py -- put your code here!
# from network import LoRa
import network
import socket
import time
# from lib.utils import parse_packet,compose_packet,icmp_request
from lib.utils import buffer, parse_packet, icmp_request, tcp_syn, tcp_ack, config, decrease_or_discard, exist_in_buffer, arp_request,discard_tcp,discard_arp,discard_icmp
import _thread

# COM4

lora, s = config()
mac = lora.mac()


known_nodes = []
active_nodes = []
arp_timeout = 60
keepalive = 30

message = {
    "device": "all",
    "message": "Send Data",
}

while True:
    print(time.localtime()[3:6], "\t> buffer:\t\t", buffer)

    # Scanning for new nodes
    if arp_timeout == 60:
        _thread.start_new_thread(arp_request, (mac,))
        arp_timeout = 0


    # Testing connectivity
    if len(active_nodes) != len(known_nodes) or keepalive == 30:
        for node in known_nodes:
            if node not in active_nodes and not exist_in_buffer([(0, 0), (3, mac), (4, node)]):
                _thread.start_new_thread(icmp_request, (mac, node,))

    # if there is a message send through tcp
    if message and len(active_nodes) > 0:
        if message["device"] == "all":
            for node in active_nodes:
                if not exist_in_buffer([(0, 0x2), (3, mac), (4, node)]):
                    _thread.start_new_thread(tcp_syn, (mac, node, ))
        elif message["device"] in active_nodes:
            if not exist_in_buffer([(0, 0x2), (3, mac), (4, message["device"])]):
                _thread.start_new_thread(
                    tcp_syn, (mac, message["device"], )
                )
            

    # receive packet
    packet = s.recv(64)

    # check if packet is not empty
    if packet:
        try:
            # unpack the packet that received
            data = parse_packet(packet)
        except Exception:
            # unpack the packet that received, with param, which means is a tcp packet
            data = parse_packet(packet, param=True)
        
        print(time.localtime()[3:6], "\t> receiver:\t", data)

        # check if ICMP Reply is well done
        if data[0] == 0x1 and data[4] == mac and data[3] in known_nodes:
            active_nodes.append(data[3])
            discard_icmp(mac,data[3])


        # check if ARP Reply is well done
        elif data[0] == 0x7 and data[4] == mac:
            known_nodes.append(data[3])
            discard_arp(mac,data[3])

        elif data[0] == 0x3 and data[4] == mac and data[3] in active_nodes and not exist_in_buffer([(0, 0x4), (3, mac), (4, data[3]), (5, data[5]+1),(6,message["message"])]):
            # Check if ackID from TCP SynAck is synID from TCP Syn + 1
            syn = exist_in_buffer([
                (0, 0x2), (3, mac), (4, data[3]), (5, data[6]-1)
            ])
            if syn:
                _thread.start_new_thread(
                    tcp_ack, (mac, data[3], data[5], message["message"],)
                )

        elif data[0] == 0x5 and data[4] == mac and data[3] in active_nodes:
            # Check if finID from TCP Fin is ackID from TCP Ack + 1
            ack = exist_in_buffer([
                (0, 0x4), (3, data[4]), (4, data[3]), (5, data[5]-1)
            ])
            if ack:
                print(time.localtime()[3:6], "\t> tcp session closed between", mac, "and", data[3])
                message = None
            else:
                print(time.localtime()[3:6], "\t> tcp session closed between", mac, "and", data[3])
            
            discard_tcp(mac,data[3])

        # NECESSARIO REMOVER OS PACOTES COM SUCESSO OU FAIL DO BUFFER

    #print("\nKnown nodes: ", known_nodes)
    #print("Active nodes: ", active_nodes)
    #print("Buffer: ", len(buffer))

    print("-----------------------------------------")
    decrease_or_discard(buffer)
    arp_timeout += 1
    keepalive += 1
    time.sleep(1)
