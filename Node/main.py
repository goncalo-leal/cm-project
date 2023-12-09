from network import LoRa
import socket
import time
import pycom
from utils import parse_packet, compose_packet, icmp_reply, tcp_fin, tcp_synack
# from lib.utils import parse_packet,compose_packet,icmp_reply

# COM6

lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)

mac = lora.mac()

while True:
    '''
    packet = s.recv(64)
    if packet:
        print('Packet received')
        request = parse_packet(packet)
        if mac == request[3]:
            print('Request received')
            response = icmp_reply(mac,request[2])
    '''

    packet = s.recv(512)
    hasSync = False
    if packet:
        syn = parse_packet(packet)
        print('SYN', syn)
        if syn[0] == 0x2:
            syn_ack = tcp_synack(mac, syn[2], syn[4])
            s.send(syn_ack)
            hasSync = True

    if hasSync:
        packet = s.recv(512)
        if packet:
            ack = parse_packet(packet,True)
            print('ACK:', ack)
            if ack[0] == 0x4:
                print('Message: ', ack[5])
                fin = tcp_fin(mac, ack[2], 1)
                s.send(fin)

    time.sleep(0.5)
