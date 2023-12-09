# main.py -- put your code here!
# from network import LoRa
import network
import socket
import time
import pycom
#from lib.utils import parse_packet,compose_packet,icmp_request
from utils import parse_packet,compose_packet,icmp_request, setUp

# LoRa Configuration:
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

# Socket Configuration:
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)

# COM4

known_nodes = [b'p\xb3\xd5I\x99x1_']
active_nodes = []


# info, socket_info = setUp()

while True:
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
    time.sleep(5)