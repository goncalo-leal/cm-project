import network
import socket
import time
#import pycom
from lib.utils import buffer,parse_packet, icmp_reply, tcp_syn, tcp_ack, config,decrease_or_discard,exist_in_buffer,arp_response,tcp_synack,tcp_fin,HEADER_PROTOCOLS,log_message
import _thread

# COM6

lora, s = config()

mac = lora.mac()

# caracteristics of own device
board = {
    "name": "board14",
    "mac": lora.mac(),
}

while True:
    log_message("buffer",buffer)

    packet = s.recv(64)

    if packet:
        try:
            data = parse_packet(packet)
        except Exception:
            data = parse_packet(packet, param=True)

        log_message("receiver",data)

        if data[0] == 0x0 and not exist_in_buffer([(0,0x1),[3,mac],(4,data[3])]):
            _thread.start_new_thread(icmp_reply, (mac, data[3],))

        elif data[0] == 0x6 and not exist_in_buffer([(0,0x7),[3,mac],(4,data[3])]):
            _thread.start_new_thread(arp_response, (mac, data[3],board["name"],))
        
        elif data[0] == 0x2 and data[4] == mac and not exist_in_buffer([(0,3),(3,mac),(4,data[3]),(6,(data[5]+1))]):
            _thread.start_new_thread(tcp_synack, (mac, data[3],data[5],))
        
        elif data[0] == 0x4 and data[4] == mac and not exist_in_buffer([(0,5),(3,mac),(4,data[3]),(5,(data[5]+1))]):
            # Check if the size and the message are the same
            if len(data[6]) == (data[2] - HEADER_PROTOCOLS[0x4]):
                _thread.start_new_thread(tcp_fin, (mac, data[3],data[5],))    
                log_message(data[6])
            else:
                _thread.start_new_thread(tcp_fin, (mac, data[3],0,))    
            
        

    decrease_or_discard(buffer)
    time.sleep(1)
