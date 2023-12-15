import struct
import time
from network import LoRa
import socket
import os


# ----------------------------------
# https://docs.python.org/3/library/struct.html
PROTOCOLS = {
    0x0: '!BBH8s8s',             # ICMP Request: id, timeout, size, MAC src, MAC dest
    0x1: '!BBH8s8s',             # ICMP Reply: id, timeout, size, MAC dst, MAC src
    0x2: '!BBH8s8sB',            # TCP Syn: id, timeout, size, MAC src, MAC dest, synID
    # TCP SynAck: id, timeout, size, MAC src, MAC dest, synID, ackID
    0x3: '!BBH8s8sBB',
    0x4: '!BBQ8s8sB%ds',         # TCP Ack: id, timeout, size, MAC src, MAC dest, ackID, data
    0x5: '!BBH8s8sB',            # TCP Fin: id, timeout, size, MAC src, MAC dest, finID -> If it is 0 then close connection and its ok, different of 0 is wrong and its tcp failed
    0x6: '!BBH8s8s',             # ARP Request: id, timeout, size, MAC src, MAC dest
    0x7: '!BBH8s8s',             # ARP Response: id, timeout, size, MAC dst, MAC src

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


def config():
    # Lora Configuration:
    lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)

    # Socket Configuration:
    s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    s.setblocking(False)

    return lora, s


lora, s = config()

# ----------------------------------

buffer = []

# ----------------------------------


def parse_packet(packet, param=None):
    id = struct.unpack('!B', packet[:1])[0]

    if id not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + id)

    if param:
        size = struct.unpack('!Q', packet[2:10])[0] - HEADER_PROTOCOLS[id]
        return list(struct.unpack(PROTOCOLS[id] % size, packet))

    return list(struct.unpack(PROTOCOLS[id], packet))


def compose_packet(data, param=None):
    if data[0] not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + data[0])

    if param:
        return struct.pack(PROTOCOLS[data[0]] % param, *data)

    return struct.pack(PROTOCOLS[data[0]], *data)


def decrease_or_discard(buffer):
    for packet in buffer:
        packet[1] -= 1
        if packet[1] <= 0:
            buffer.remove(packet)
    return buffer


def exist_in_buffer(params):    # Verifica se algum pacote com os parametros passados existe no buffer
    # params = [(0,0),[2,src],(3,dest)]
    exists = []
    for packet in buffer:
        for param in params:
            if packet[param[0]] == param[1]:
                exists.append(True)
    
    return True if len(exists) == len(params) else False


def icmp_request(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x0, 20, 16, src, dest]
    buffer.append(packet)

    request = compose_packet(packet)
    s.send(request)


def icmp_reply(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x1, 20, 16, src, dest]
    buffer.append(packet)

    reply = compose_packet(packet)
    s.send(reply)

def arp_request(src):
    if len(src) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x6, 20, 16, src, b'\xff\xff\xff\xff\xff\xff\xff\xff']    # Broadcast
    buffer.append(packet)

    request = compose_packet(packet)
    s.send(request)


def arp_response(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x7, 20, 16, src, dest]
    buffer.append(packet)

    reply = compose_packet(packet)
    s.send(reply)



def tcp_syn(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    synID = ord(os.urandom(1))

    syn = compose_packet([0x2, 20, 17, src, dest, synID])
    return syn


def tcp_synack(src, dest, synID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                 # TCP Behaviour -> ackID = synID + 1
    synID = ord(os.urandom(1))

    synack = compose_packet([0x3, 20, 18, src, dest, synID, ackID])
    return synack


def tcp_ack(src, dest, synID, data):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                   # TCP Behaviour -> ackID = synID + 1
    size = len(data)

    ack = compose_packet(
        [0x4, 20, size + HEADER_PROTOCOLS[0x4], src, dest, ackID, data],
        size
    )
    return ack


def tcp_fin(src, dest, finID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    fin = compose_packet([0x5, 20, 17, src, dest, finID])
    return fin


# ----------------------------------
# Objects:


# def icmp(id, src, dest):
#     if len(src) != 8 or len(dest) != 8:
#         raise Exception('Invalid MAC address')

#     request = compose_packet([0x0, 16, src, dest])
#     reply = compose_packet([0x1, 16, src, dest])
#     timeout = time.time() + 5

#     if id == 0:
#         s.send(request)
#         while time.time() < timeout:
#             packet = s.recv(64)
#             if packet:
#                 data = parse_packet(packet)
#                 if data[0] == 0x1 and data[3] == src:
#                     return data[2]
#     if id == 1:
#         s.send(reply)
#     return None
