import pycom
import utils
import time
import _thread

def sub_cb(topic, msg):
   # This callback is called when a message is received

   # esta função deve ficar na main, porque faz parte da lógica de negócio
   # e não da lógica de comunicação

   # algumas mensagens mqtt devem ter impacto no comportamento do gateway ou dos nodes
   print(topic)
   print(msg)

# def load_config():
#     with open('/flash/gateway_config.json','r') as fp:
#         buf = json.load(fp)
#     return buf

# def wifi_connect(wifi_config):
#     print('Connecting to WiFi...')
#     wlan = WLAN(mode=WLAN.STA)
#     wlan.connect(
#         ssid=wifi_config['ssid'],
#         auth=(WLAN.WPA2, wifi_config['password']),
#         timeout=5000
#     )

#     try:
#         while not wlan.isconnected():
#             machine.idle()
#         print("Connected to WiFi\n")
#         pycom.rgbled(0x103300)
#     except:
#         print("Error connecting to WiFi")
#         pycom.rgbled(0xff0000)
#         time.sleep(5)

#         wifi_connect(wifi_config)


# def get_lora_socket():
#     lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
#     lora_socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
#     lora_socket.setblocking(False)
#     return lora_socket

# def get_mqtt_client(mqtt_config):
#     mqtt_client = MQTTClient(
#         mqtt_config["client_id"],
#         mqtt_config["server"],
#         port=mqtt_config["port"]
#     )
#     mqtt_client.set_callback(sub_cb)
#     mqtt_client.connect()
#     return mqtt_client

#------------------------------------------

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
mac = lora.mac()

# MQTT client
if "mqtt" not in conf:
    print("[ERROR] MQTT config missing")
    exit(1)

mqtt_client = utils.get_mqtt_client(conf["mqtt"], sub_cb)
mqtt_client.subscribe(topic=conf["mqtt"]["topics"]["subscribe"])

pong_counter = 0
known_nodes = [b'p\xb3\xd5I\x99x1_']
active_nodes = []
while True:
    pycom.rgbled(0x00ff00)

    # Testing connectivity
    if len(active_nodes) != len(known_nodes):
        for node in known_nodes:
            if node not in active_nodes and not utils.exist_in_buffer([(0,0),[3,mac],(4,node)]):
                _thread.start_new_thread(utils.icmp_request, (mac, node, lora_socket))
    
    # Receive LoRa packets
    packet = lora_socket.recv(64)
    if packet:
        try:
            data = utils.parse_packet(packet)
        except Exception:
            data = utils.parse_packet(packet, param=True)

        if data[0] == 0x1 and data[4] == mac and data[3] in known_nodes:
            active_nodes.append(data[3])

    print("Known nodes: ", known_nodes)
    print("Active nodes: ", active_nodes)
    print("Buffer: ", utils.get_buffer())
    
    utils.decrease_or_discard()

    # O MQTT ainda não está na versão final, 
    # mas vou deixar isto aqui para conseguir criar os dashboards
    
    
    # mqtt_client.check_msg()

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
    print("Sending ON")
    mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/device01/led_status', msg="1")
    time.sleep(5)
    print("Sending OFF")
    mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"] + '/device02/led_status', msg="0")

    pycom.rgbled(0xff0000)

    time.sleep(10)