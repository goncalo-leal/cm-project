from mqtt import MQTTClient
from network import WLAN
from network import LoRa
import machine
import socket
import pycom
import json
import time

def sub_cb(topic, msg):
   print(msg)

def load_config():
    with open('/flash/gateway_config.json','r') as fp:
        buf = json.load(fp)
    return buf

def wifi_connect(wifi_config):
    print('Connecting to WiFi...',  end='')
    wlan = WLAN(mode=WLAN.STA)
    wlan.connect(
        ssid="goncalo-x1",  # wifi_config['ssid'],
        auth=(WLAN.WPA2, "yBJV3Jg1"), # wifi_config['password']),
        timeout=5000
    )

    while not wlan.isconnected():
        print('.', end='') 
        machine.idle()
    print("Connected to WiFi\n")

    pycom.rgbled(0x103300)

#------------------------------------------

pycom.heartbeat(False)

# Load config
conf = load_config()

print(conf)

# Connect to wifi
if "network" not in conf:
    print("[ERROR] WIFI config missing")
    exit(1)

wifi_connect(conf["network"])

lora = LoRa(mode=LoRa.LORA, region=LoRa.EU868)
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
s.setblocking(False)
i = 0
while True:
    if s.recv(64) == b'Ping':
        s.send('Pong')
        print('Pong {}'.format(i))
        i = i+1
    time.sleep(5)

# client = MQTTClient("device_id", "io.adafruit.com",user="your_username", password="your_api_key", port=1883)

# client.set_callback(sub_cb)
# client.connect()
# client.subscribe(topic="youraccount/feeds/lights")

# while True:
#     print("Sending ON")
#     client.publish(topic="youraccount/feeds/lights", msg="ON")
#     time.sleep(1)
#     print("Sending OFF")
#     client.publish(topic="youraccount/feeds/lights", msg="OFF")
#     client.check_msg()

#     time.sleep(1)