from network import LoRa
import socket
import time
import struct

_LORA_PKG_FORMAT = "!BB%ds"
_LORA_PKG_ACK_FORMAT = "BBB"

lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)


while True:
    recv_pkg = lora_sock.recv(512)
    if len(recv_pkg) > 2:
        print('Received: {}'.format(recv_pkg))
        recv_pkg_len = recv_pkg[1]

        device_id, pkg_len, msg = struct.unpack(_LORA_PKG_FORMAT % recv_pkg_len, recv_pkg)

        print('Device: %d - Pkg:  %s' % (device_id, msg))

        ack_pkg = struct.pack(_LORA_PKG_ACK_FORMAT, device_id, 1, 200)
        lora_sock.send(ack_pkg)


