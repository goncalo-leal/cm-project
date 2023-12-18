import pycom
import lib.utils as utils
import time
import _thread

def sub_cb(topic, msg):
   # This callback is called when a message is received

   # esta função deve ficar na main, porque faz parte da lógica de negócio
   # e não da lógica de comunicação

   # algumas mensagens mqtt devem ter impacto no comportamento do gateway ou dos nodes
   print(topic)
   print(msg)


pycom.heartbeat(False)

# Load config
conf = utils.load_config()

# Connect to wifi
if "network" not in conf:
    print("[ERROR] WIFI config missing")
    exit(1)

wlan = utils.wifi_connect(conf["network"], 2)

# LoRa client
lora, lora_socket = utils.get_lora_socket()

board = {
    "name": conf["device_name"],
    "mac": lora.mac(),
}

# MQTT client
if "mqtt" not in conf:
    print("[ERROR] MQTT config missing")
    exit(1)

mqtt_client = utils.get_mqtt_client(conf["mqtt"], sub_cb)
mqtt_client.subscribe(topic=conf["mqtt"]["topics"]["subscribe"])

known_nodes = []
active_nodes = []
mac_to_devices = {}
arp_timeout = 60
keepalive = 30

message = {
    "device": "all",
    "message": "Send Data",
}

while True:
    pycom.rgbled(0x00ff00)
    utils.log_message("buffer", utils.get_buffer())

    # Scanning for new nodes
    if arp_timeout == 60:
        _thread.start_new_thread(utils.arp_request, (board["mac"], board["name"], lora_socket))
        arp_timeout = 0

    # Testing connectivity
    if len(active_nodes) != len(known_nodes):
        for node in known_nodes:
            if node not in active_nodes and not utils.exist_in_buffer([(0,0),[3, board["mac"]],(4,node)]):
                _thread.start_new_thread(utils.icmp_request, (board["mac"], node, lora_socket))
    
    # TODO: FAZER ARRAY DE MENSAGENS PARA ENVIAR e SE ENVIADO REMOVER DO ARRAY
    # if there is a message send through tcp
    if message and len(active_nodes) > 0:
        devices_to_mac = {v: k for k, v in mac_to_devices.items()}
        if message["device"] == "all":
            # send to all active nodes
            for node in active_nodes:
                if not utils.exist_in_buffer([(0, 0x2), (3, board["mac"]), (4, node)]):
                    _thread.start_new_thread(utils.tcp_syn, (board["mac"], node, lora_socket))
        elif message["device"] in devices_to_mac:
            # send to specific node
            if not utils.exist_in_buffer([(0, 0x2), (3, board["mac"]), (4, devices_to_mac[message["device"]])]):
                _thread.start_new_thread(utils.tcp_syn, (board["mac"], devices_to_mac[message["device"]], lora_socket))

    # Receive LoRa packets
    packet = lora_socket.recv(64)
    if packet:
        # packet is not empty
        try:
            data = utils.parse_packet(packet)
        except Exception:
            # Probably is a tcp packet
            data = utils.parse_packet(packet, param=True)

        print(time.localtime()[3:6], "\t> receiver:\t", data)

        # check if ICMP Reply is correct
        if data[0] == 0x1 and data[4] == board["mac"] and data[3] in known_nodes:
            active_nodes.append(data[3])
            utils.discard_icmp(board["mac"], data[3])
        
        # check if ARP Reply is correct
        elif data[0] == 0x7 and data[4] == board["mac"]:
            known_nodes.append(data[3])
            mac_to_devices[data[3]] = data[5].decode('utf-8').rstrip('\x00')
            print(mac_to_devices)
            utils.discard_arp(board["mac"], data[3])
        
        elif data[0] == 0x3 and data[4] == board["mac"] and data[3] in active_nodes and not utils.exist_in_buffer([(0, 0x4), (3, board["mac"]), (4, data[3]), (5, data[5]+1),(6,message["message"])]):
            # Check if ackID from TCP SynAck is synID from TCP Syn + 1
            syn = utils.exist_in_buffer([
                (0, 0x2), (3, board["mac"]), (4, data[3]), (5, data[6]-1)
            ])
            if syn:
                _thread.start_new_thread(
                    utils.tcp_ack, (board["mac"], data[3], data[5], message["message"], lora_socket)
                )

                utils.log_message("tcp ack", mac_to_devices[data[3]])

                # We received a response, so we can calculate the rtt and the throughput
                rtt = time.time() - syn[6] # syn[6] is the timestamp of the tcp syn
                throughput = (syn[2] + data[2]) / rtt # syn[2] is the number of bits sent and data[2] is the number of bits received

                # This RTT and throughput represents the communication between the gateway and the node

                print("RTT:", rtt)
                print("Throughput:", throughput)
                print(mac_to_devices[data[3]])

                # send these metrics to the mqtt broker
                #TODO: change device name
                mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/' + mac_to_devices[data[3]] + '/rtt', msg=str(rtt))
                mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/' + mac_to_devices[data[3]] + '/throughput', msg=str(throughput))

        elif data[0] == 0x5 and data[4] == board["mac"] and data[3] in active_nodes:
            # Check if ackID from TCP FinAck is finID from TCP Fin + 1
            ack = utils.exist_in_buffer([
                (0, 0x4), (3, board["mac"]), (4, data[3]), (5, data[5]-1)
            ])
            if ack:
                utils.log_message("tcp session closed", board["mac"], data[3])
                # message = None

                # We received a response, so we can calculate the rtt and the throughput
                rtt = time.time() - ack[7] # ack[6] is the timestamp of the tcp ack
                throughput = (ack[2] + data[2]) / rtt # ack[2] is the number of bits sent and data[2] is the number of bits received
                
                # This RTT and throughput represents the communication between the gateway and the node

                print("RTT:", rtt)
                print("Throughput:", throughput)

                # send these metrics to the mqtt broker
                #TODO: change device name
                mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/' + mac_to_devices[data[3]] + '/rtt', msg=str(rtt))
                mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/' + mac_to_devices[data[3]] + '/throughput', msg=str(throughput))
            else:
                utils.log_message("tcp session failed", board["mac"], data[3])

            utils.discard_tcp(board["mac"], data[3])

    print("-----------------------------------------")
    utils.decrease_or_discard()
    arp_timeout += 1
    keepalive += 1

    # O MQTT ainda não está na versão final, 
    # mas vou deixar isto aqui para conseguir criar os dashboards

    # Let's check if we are still connected to wifi
    if not wlan.isconnected():
        print("Disconnected from WiFi")
        pycom.rgbled(0xff0000)
        time.sleep(5)

        wlan = utils.wifi_connect(conf["network"], 5)

    # Let's check if we are still connected to mqtt
    if not mqtt_client.is_connected():
        print("Disconnected from MQTT")
        pycom.rgbled(0xff0000)
        time.sleep(5)

        mqtt_client = utils.get_mqtt_client(conf["mqtt"], sub_cb)
        mqtt_client.subscribe(topic=conf["mqtt"]["topics"]["subscribe"])

    # Let's send some data
    # print("Sending ON")
    # mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/device01/led_status', msg="1")
    # time.sleep(5)
    # print("Sending OFF")
    # mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/device02/led_status', msg="0")

    pycom.rgbled(0xff0000)

    time.sleep(1)