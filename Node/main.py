import os
import socket
import time
import struct
from network import LoRa

# A basic package header, B: 1 byte for the deviceId, B: 1 byte for the pkg size
_LORA_PKG_FORMAT = "BB%ds"
_LORA_PKG_ACK_FORMAT = "BBB"
DEVICE_ID = 0x01


# Open a Lora Socket, use tx_iq to avoid listening to our own messages
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915
lora = LoRa(mode=LoRa.LORA, tx_iq=True, region=LoRa.EU868)
lora_sock = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_sock.setblocking(False)

while(True):
    # Package send containing a simple string
    msg = "Device 1 Here"
    pkg = struct.pack(_LORA_PKG_FORMAT % len(msg), DEVICE_ID, len(msg), msg)
    lora_sock.send(pkg)
    print("Sending message '%s'..." % msg)

    # Wait for the response from the gateway. NOTE: For this demo the device does an infinite loop for while waiting the response. Introduce a max_time_waiting for you application
    waiting_ack = True
    while(waiting_ack):
        recv_ack = lora_sock.recv(512)

        if (len(recv_ack) > 0):
            device_id, pkg_len, ack = struct.unpack(_LORA_PKG_ACK_FORMAT, recv_ack)
            if (device_id == DEVICE_ID):
                if (ack == 200):
                    waiting_ack = False
                    print("ACK")
                else:
                    waiting_ack = False
                    print("Message Failed")

    time.sleep(5)