# main.py -- put your code here!
# from network import LoRa
import network
import socket
import json
import time
import pycom
# from lib.utils import parse_packet,compose_packet,icmp_request
from utils import parse_packet, icmp_request, tcp_syn, tcp_ack, config

# COM4

lora, s = config()
mac = lora.mac()


known_nodes = [b'p\xb3\xd5I\x99x1_']
active_nodes = []


while True:
    '''
    print('Sending request')

    for node in known_nodes:
        # get the mac from the info dictionary
        # mac = info['mac']
        # print("In main.py, mac:" + str(mac))

        request = icmp_request(lora.mac(),node)

        if request:
            print('Request received')
            if request not in active_nodes:
                active_nodes.append(request)

    print(active_nodes)
    '''
    syn = tcp_syn(mac, known_nodes[0])
    print("SYN:", parse_packet(syn))
    s.send(syn)
    timeout = time.time() + 5
    message = {
        "green": True,
        "yellow": False,
        "red": True
        }   


    json_message = json.dumps(message)

    hasSynAck = False

    while time.time() < timeout:
        packet = s.recv(512)

        if packet:
            syn_ack = parse_packet(packet)
            print('SYNACK:', syn_ack)
            if syn_ack[0] == 0x3:
                hasSynAck = True
                print('SYNACK received')
                break

    if hasSynAck:
        ack = tcp_ack(mac, known_nodes[0], syn_ack[4], json_message)
        s.send(ack)
        print('ACK: ', parse_packet(ack, True))
        timeout = time.time() + 5

        while time.time() < timeout:
            packet = s.recv(128)

            if packet:
                fin = parse_packet(packet)
                if fin[0] == 0x5:
                    print('FIN:', fin)

    time.sleep(5)
