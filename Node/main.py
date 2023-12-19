import network
import socket
import time
#import pycom
from lib.utils import buffer,parse_packet, icmp_reply, tcp_syn, tcp_ack, config,decrease_or_discard,exist_in_buffer,arp_response,tcp_synack,tcp_fin,HEADER_PROTOCOLS,log_message,COLORS,discard_tcp
import _thread
import json

# COM6

lora, s = config()

mac = lora.mac()

# caracteristics of own device
board = {
    "name": "board14",
    "mac": lora.mac(),
    "gateway": None,
    "status": 1,
    "color": "red",
}

info_interval = 10

while True:
    log_message("buffer",buffer)

    # Openning a session with the gateway, to send its information
    if info_interval == 10 :
        if board["gateway"]:
            _thread.start_new_thread(tcp_syn, (board["mac"],board["gateway"],))
        info_interval = 0
    else:
        info_interval += 1



    packet = s.recv(64)

    if packet:
        try:
            data = parse_packet(packet)
        except Exception:
            data = parse_packet(packet, param=True)

        log_message("receiver",data)

        # ARP
        if data[0] == 0x6 and not exist_in_buffer([(0,0x7),[3,mac],(4,data[3])]):
            _thread.start_new_thread(arp_response, (mac, data[3],board["name"],))
            board["gateway"] = data[3]
            print("GATEWAY:\t",board["gateway"])

        # ICMP
        elif data[0] == 0x0 and not exist_in_buffer([(0,0x1),[3,mac],(4,data[3])]):
            _thread.start_new_thread(icmp_reply, (mac, data[3],))

        # TCP
        elif data[0] == 0x2 and data[4] == mac and not exist_in_buffer([(0,3),(3,mac),(4,data[3]),(6,(data[5]+1))]):
            _thread.start_new_thread(tcp_synack, (mac, data[3],data[5],))

        # ack
        elif data[0] == 0x3 and data[4] == mac and not exist_in_buffer([(0, 0x4), (3, mac), (4, data[3]), (5, data[5]+1),(6,json.dumps(board))]):
            # Check if ackID from TCP SynAck is synID from TCP Syn + 1
            syn = exist_in_buffer([
                (0, 0x2), (3, mac), (4, data[3]), (5, data[6]-1)
            ])
            if syn:
                _thread.start_new_thread(
                    tcp_ack, (mac, data[3], data[5], json.dumps(board),)
                )
        
        elif data[0] == 0x4 and data[4] == mac and not exist_in_buffer([(0,5),(3,mac),(4,data[3]),(5,(data[5]+1))]):
            # Check if the size and the message are the same
            if len(data[6]) == (data[2] - HEADER_PROTOCOLS[0x4]):
                _thread.start_new_thread(tcp_fin, (mac, data[3],data[5],))    
                message = data[6].decode('utf-8').split("|")
                if message[0] == "status" and (message[1] == "0" or message[1] == "1"):
                    board["status"] = int(message[1])
                elif message[0] == "color" and message[1] in COLORS.keys():
                    board["color"] = message[1]

            else:
                _thread.start_new_thread(tcp_fin, (mac, data[3],0,))    
        
        elif data[0] == 0x5 and data[4] == mac:
            # Check if finID from TCP Fin is ackID from TCP Ack + 1
            ack = exist_in_buffer([
                (0, 0x4), (3, data[4]), (4, data[3]), (5, data[5]-1)
            ])
            if ack:
                log_message("tcp session closed",mac,data[3])
            else:
                log_message("tcp session failed",mac,data[3])
            
            discard_tcp(mac,data[3])
            
        
    #print("BOARD:\t",board)
    decrease_or_discard(buffer)
    time.sleep(1)
