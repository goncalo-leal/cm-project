from network import LoRa
import socket
import time
import pycom
from utils import parse_packet,compose_packet,icmp_reply
#from lib.utils import parse_packet,compose_packet,icmp_reply

# COM6

lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)

mac = lora.mac()

while True:
    packet = s.recv(64)
    if packet:
        print('Packet received')
        request = parse_packet(packet)
        if mac == request[3]:
            print('Request received')
            response = icmp_reply(mac,request[2])
    time.sleep(0.5)
        