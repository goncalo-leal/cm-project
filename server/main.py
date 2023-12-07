import paho.mqtt.client as mqtt
import time

broker_address="localhost" #"broker.hivemq.com"
broker_port=1883

client = mqtt.Client("server")
client.connect(broker_address, broker_port, 60)

while True:
    print("Sending ON to light1")
    client.publish("cm-project/server/light1", "ON")
    time.sleep(10)