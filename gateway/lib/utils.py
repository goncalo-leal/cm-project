import struct
import time
from network import LoRa
import socket
import os

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
    0x3: '!BH8s8sBB',           # TCP SynAck: id, size, MAC src, MAC dest, synID, ackID
    0x4: '!BQ8s8sB%ds',         # TCP Ack: id, size, MAC src, MAC dest, ackID, data
    0x5: '!BH8s8sB',            # TCP Fin: id, size, MAC src, MAC dest, finID

}

HEADER_PROTOCOLS = {
    0x0: 16,
    0x1: 16,
    0x2: 17,
    0x3: 18,
    0x4: 17,
    0x5: 17,
}

# ----------------------------------


def parse_packet(packet, param=None):
    id = struct.unpack('!B', packet[:1])[0]

    if id not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + id)

    if param:
        size = struct.unpack('!Q', packet[1:9])[0] - HEADER_PROTOCOLS[id]
        return list(struct.unpack(PROTOCOLS[id] % size, packet))

    return list(struct.unpack(PROTOCOLS[id], packet))


def compose_packet(data, param=None):
    if data[0] not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + data[0])

    if param:
        return struct.pack(PROTOCOLS[data[0]] % param, *data)

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

    synID = ord(os.urandom(1))

    syn = compose_packet([0x2, 17, src, dest, synID])
    return syn


def tcp_synack(src, dest, synID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                 # TCP Behaviour -> ackID = synID + 1
    synID = ord(os.urandom(1))

    synack = compose_packet([0x3, 18, src, dest, synID, ackID])
    return synack


def tcp_ack(src, dest, synID, data):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                   # TCP Behaviour -> ackID = synID + 1
    size = len(data)

    ack = compose_packet(
        [0x4, size + HEADER_PROTOCOLS[0x4], src, dest, ackID, data], size)
    return ack


def tcp_fin(src, dest, finID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    fin = compose_packet([0x5, 17, src, dest, finID])
    return fin
