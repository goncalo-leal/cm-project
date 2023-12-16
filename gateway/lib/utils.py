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
    0x5: '!BBH8s8sB',            # TCP Fin: id, timeout, size, MAC src, MAC dest, finID -> If it is ackID + 1 from ACK then close connection and its ok, if it's different then it's wrong and its tcp failed
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

# parse packet depending on protocol and it's data, if param is true then it's a tcp packet


def parse_packet(packet, param=None):
    id = struct.unpack('!B', packet[:1])[0]

    if id not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + id)

    if param:
        size = struct.unpack('!Q', packet[2:10])[0] - HEADER_PROTOCOLS[id]
        return list(struct.unpack(PROTOCOLS[id] % size, packet))

    return list(struct.unpack(PROTOCOLS[id], packet))

# build packet depending on protocol and it's data


def compose_packet(data, param=None):
    if data[0] not in PROTOCOLS:
        raise Exception('Unknown protocol: ' + data[0])

    if param:
        return struct.pack(PROTOCOLS[data[0]] % param, *data)

    return struct.pack(PROTOCOLS[data[0]], *data)


# decreses timeout of each packet in buffer and discard if timeout is 0
def decrease_or_discard(buffer):
    for packet in buffer:
        packet[1] -= 1
        if packet[1] <= 0:
            buffer.remove(packet)


# check if a packet with the same params exists in buffer, and return it
def exist_in_buffer(params):
    checkParams = []

    for packet in buffer:
        for param in params:
            if param[0] < len(packet):
                if packet[param[0]] == param[1]:
                    checkParams.append(True)
                    if len(checkParams) == len(params):
                        return packet

        checkParams = []

    return None

def discard_from_buffer(params):    # Discard all packets from buffer that match params
    for param in params:
        packet = exist_in_buffer(param)
        if packet:
            buffer.remove(packet)
    return buffer

def icmp_request(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x0, 20, 16, src, dest]
    buffer.append(packet)

    request = compose_packet(packet)
    s.send(request)
    print(time.localtime()[3:6], "\t> icmp request:\t",packet)


def icmp_reply(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x1, 20, 16, src, dest]
    buffer.append(packet)

    reply = compose_packet(packet)
    s.send(reply)
    print(time.localtime()[3:6], "\t> icmp reply:\t",packet)


def arp_request(src):
    if len(src) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x6, 20, 16, src,
              b'\xff\xff\xff\xff\xff\xff\xff\xff']    # Broadcast
    buffer.append(packet)

    request = compose_packet(packet)
    s.send(request)
    print(time.localtime()[3:6], "\t> arp request:\t",packet)


def arp_response(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    packet = [0x7, 20, 16, src, dest]
    buffer.append(packet)

    reply = compose_packet(packet)
    s.send(reply)
    print(time.localtime()[3:6], "\t> arp reply:\t",packet)


def tcp_syn(src, dest):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    synID = ord(os.urandom(1))

    packet = [0x2, 20, 17, src, dest, synID]
    buffer.append(packet)

    syn = compose_packet(packet)
    s.send(syn)
    print(time.localtime()[3:6], "\t> tcp syn:\t",packet)


def tcp_synack(src, dest, synID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                 # TCP Behaviour -> ackID = synID + 1
    synID = ord(os.urandom(1))

    packet = [0x3, 20, 18, src, dest, synID, ackID]
    buffer.append(packet)

    synack = compose_packet(packet)
    s.send(synack)
    print(time.localtime()[3:6], "\t> tcp synack:\t",packet)


def tcp_ack(src, dest, synID, data):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    ackID = synID + 1                   # TCP Behaviour -> ackID = synID + 1
    size = len(data)

    packet = [0x4, 20, size + HEADER_PROTOCOLS[0x4], src, dest, ackID, data]
    buffer.append(packet)

    ack = compose_packet(
        packet,size
    )
    s.send(ack)
    print(time.localtime()[3:6], "\t> tcp ack:\t",packet)


def tcp_fin(src, dest, ackID):
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')

    finID = ackID + 1

    packet = [0x5, 20, 17, src, dest, finID]
    buffer.append(packet)

    fin = compose_packet(packet)
    s.send(fin)
    print(time.localtime()[3:6], "\t> tcp fin:\t",packet)

def discard_tcp(src, dest):     # Discard all TCP packets from src to dest
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')
    
    discard_from_buffer([
        [(0,0x2),(3,src),(4,dest)],
        [(0,0x3),(3,src),(4,dest)],
        [(0,0x4),(3,src),(4,dest)],
        [(0,0x5),(3,src),(4,dest)],
        ])

def discard_arp(src, dest):     # Discard all ARP packets from src to dest
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')
    
    discard_from_buffer([
        [(0,0x6),(3,src),(4,dest)],
        [(0,0x7),(3,src),(4,dest)],
        ])

def discard_icmp(src, dest):     # Discard all ICMP packets from src to dest
    if len(src) != 8 or len(dest) != 8:
        raise Exception('Invalid MAC address')
    
    discard_from_buffer([
        [(0,0x0),(3,src),(4,dest)],
        [(0,0x1),(3,src),(4,dest)],
        ])
    
    






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
