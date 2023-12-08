import struct
import time
from network import LoRa
import socket

# LoRa Configuration:
lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

# Socket Configuration:
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)


# ----------------------------------

PROTOCOLS = {
    0x0: '!BH8s8s',           # ICMP Request: id, size, MAC src, MAC dest
    0x1: '!BH8s8s',           # ICMP Reply: id, size, MAC dst, MAC src
}

# ----------------------------------


def parse_packet(packet):
    id = struct.unpack('!B', packet[:1])[0]

    if id not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + id)

    return list(struct.unpack(PROTOCOLS[id], packet))


def compose_packet(data):
    if data[0] not in PROTOCOLS:
        raise Exception('Unknown protocol: '+ data[0])

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
