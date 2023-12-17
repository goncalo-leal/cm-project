from network import LoRa
import socket
import time
import pycom
import json
from utils import parse_packet, compose_packet, icmp_reply, tcp_fin, tcp_synack,config

# COM6

lora, s = config()

mac = lora.mac()

while True:
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
                print('Message: ', json.loads(ack[5]))
                if all(led_key in ack[5] for led_key in ["green", "yellow", "red"]):
                    # Control the LEDs based on the received values
                    if ack[5]["green"]:
                        pycom.rgbled(0x007f00)  # Green LED
                    else:
                        pycom.rgbled(0x000000)  # Turn off the green LED

                    if ack[5]["yellow"]:
                        pycom.rgbled(0x7f7f00)  # Yellow LED
                    else:
                        pycom.rgbled(0x000000)  # Turn off the yellow LED

                    if ack[5]["red"]:
                        pycom.rgbled(0x7f0000)  # Red LED
                    else:
                        pycom.rgbled(0x000000)  # Turn off the red LED
                fin = tcp_fin(mac, ack[2], 1)
                s.send(fin)

    time.sleep(0.5)
