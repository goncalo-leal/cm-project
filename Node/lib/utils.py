import struct
import time
from network import LoRa
import socket
import random

# LoRa Configuration:
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

# Socket Configuration:
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)


# ----------------------------------
# https://docs.python.org/3/library/struct.html
PROTOCOLS = {
    0x0: '!BH8s8s',             # ICMP Request: id, size, MAC src, MAC dest
    0x1: '!BH8s8s',             # ICMP Reply: id, size, MAC dst, MAC src
    0x2: '!BH8s8sB',            # TCP Syn: id, size, MAC src, MAC dest, synID
    0x3: '!BH8s8sB',            # TCP SynAck: id, size, MAC src, MAC dest, synID, ackID
    0x4: '!B%d8s8sBs',          # TCP Ack: id, size, MAC src, MAC dest, ackID, data
    0x5: '!BH8s8sB',            # TCP Fin: id, size, MAC src, MAC dest, finID

}

# ----------------------------------


def parse_packet(packet):
    id = struct.unpack('!B', packet[:1])[0]

    if id not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + id)

    return list(struct.unpack(PROTOCOLS[id], packet))


def compose_packet(data):
    if data[0] not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + data[0])

    return struct.pack(PROTOCOLS[data[0]], *data)


def icmp_request(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    request = compose_packet([0x0, 16, src, dest])
    timeout = time.time() + 5
    s.send(request)

    while time.time() < timeout:
        packet = s.recv(64)

        if packet:
            data = parse_packet(packet)
            if data[0] == 0x1 and data[3] == src:
                return data[2]

    return None


def icmp_reply(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    reply = compose_packet([0x1, 16, src, dest])
    s.send(reply)


def tcp_syn(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    synID = random.randint(0, 128)

    syn = compose_packet([0x2, 16, src, dest, synID])
    timeout = time.time() + 5
    s.send(syn)

    while time.time() < timeout:
        packet = s.recv(64)

        if packet:
            data = parse_packet(packet)
            if data[0] == 0x3 and data[3] == src and data[2] == dest and (data[5] + 1) == synID:
                return data

    return None


def tcp_synack(src, dest, synID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                   # TCP Behaviour -> ackID = synID + 1
    synID = random.randint(0, 128)

    synack = compose_packet([0x3, 16, src, dest, synID, ackID])
    s.send(synack)

def tcp_ack(src, dest, ackID, data, encrypt=False):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ack = compose_packet([0x4, 16, src, dest, ackID, data])
    s.send(ack)
    