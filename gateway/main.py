# from mqtt import MQTTClient
from umqttsimple import MQTTClient
from network import WLAN
from network import LoRa
import machine
import socket
import pycom
import json
import time

def sub_cb(topic, msg):
   print(topic)
   print(msg)

def load_config():
    with open('/flash/gateway_config.json','r') as fp:
        buf = json.load(fp)
    return buf

def wifi_connect(wifi_config):
    print('Connecting to WiFi...',  end='')
    wlan = WLAN(mode=WLAN.STA)
    wlan.connect(
        ssid=wifi_config['ssid'],
        auth=(WLAN.WPA2, wifi_config['password']),
        timeout=5000
    )

    try:
        while not wlan.isconnected():
            print('.', end='') 
            machine.idle()
    except:
        print("Error connecting to WiFi")
        pycom.rgbled(0xff0000)
        time.sleep(5)
        wifi_connect(wifi_config)
    
    # TODO: sleep and retry

    print("Connected to WiFi\n")

    pycom.rgbled(0x103300)

def get_lora_socket():
    lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
    lora_socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
    lora_socket.setblocking(False)
    return lora_socket

def get_mqtt_client(mqtt_config):
    mqtt_client = MQTTClient(
        mqtt_config["client_id"],
        mqtt_config["server"],
        port=mqtt_config["port"]
    )
    mqtt_client.set_callback(sub_cb)
    mqtt_client.connect()
    return mqtt_client

#------------------------------------------

pycom.heartbeat(False)

# Load config
conf = load_config()

# Connect to wifi
if "network" not in conf:
    print("[ERROR] WIFI config missing")
    exit(1)

wifi_connect(conf["network"])

# LoRa client
lora_socket = get_lora_socket()

# MQTT client
if "mqtt" not in conf:
    print("[ERROR] MQTT config missing")
    exit(1)

mqtt_client = get_mqtt_client(conf["mqtt"])
mqtt_client.subscribe(topic=conf["mqtt"]["topics"]["subscribe"])

pong_counter = 0
while True:
    pycom.rgbled(0x00ff00)

    if lora_socket.recv(64) == b'Ping':
        lora_socket.send('Pong')
        print('Pong {}'.format(pong_counter))
        pong_counter += 1
    
    mqtt_client.check_msg()
    
    print("Sending ON")
    mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"], msg="ON")
    time.sleep(5)
    print("Sending OFF")
    mqtt_client.publish(topic=conf["mqtt"]["topics"]["publish"], msg="OFF")

    pycom.rgbled(0xff0000)

    time.sleep(10)