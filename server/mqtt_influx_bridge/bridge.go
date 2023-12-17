package main

import (
	"errors"
	"context"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
	"fmt"
	"strconv"

	paho "github.com/eclipse/paho.mqtt.golang"
	influxdb "github.com/influxdata/influxdb-client-go/v2"
	"github.com/kelseyhightower/envconfig"
)

// Config is the configuration for the bridge
// This tells the envconfig package what to read from the environment
type Config struct {
	MQTTBroker 			string `envconfig:"MQTT_BROKER" default:"tcp://localhost:1883"`
	MQTTTopic 			string `envconfig:"MQTT_TOPIC" default:"#"`
	InfluxDBHost 		string `envconfig:"INFLUXDB_HOST" default:"http://localhost:8086"`
	InfluxDBName 		string `envconfig:"INFLUXDB_NAME" default:"cm-project"`
	InfluxDBUser 		string `envconfig:"INFLUXDB_USER"`
	InfluxDBPassword 	string `envconfig:"INFLUXDB_PASSWORD"`
	InfluxMeasurement 	string `envconfig:"INFLUX_MEASUREMENT" default:"iotdata"`
	InfluxToken 		string `envconfig:"INFLUX_TOKEN"`
}

// MQTTMessage is the info we expect to receive from MQTT
type MQTTMessage struct {
	Device 		string
	Command 	string
	Value 		int
}

// influx_client is the InfluxDB client initialized in init()
var influx_client influxdb.Client

var config Config

func init() {
	// Read the configuration from the environment
	err := envconfig.Process("", &config)
	if err != nil {
		log.Fatal(err.Error())
	}

	fmt.Println("MQTT_BROKER:", config.MQTTBroker)
	fmt.Println("MQTT_TOPIC:", config.MQTTTopic)
	fmt.Println("INFLUXDB_HOST:", config.InfluxDBHost)
	fmt.Println("INFLUXDB_NAME:", config.InfluxDBName)
	fmt.Println("INFLUXDB_USER:", config.InfluxDBUser)

	// Create database if it does not exist
    // _, err = queryDB(
	// 	influx_client, fmt.Sprintf("CREATE DATABASE %s", config.InfluxDBName),
	// )
    // if err != nil {
    //     log.Fatal(err)
    // }
}

func main() {
    println("Hello, world.")
	
	// Create a channel to receive OS signals
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	// Create a new MQTT client
	opts := paho.NewClientOptions()
	opts.AddBroker(config.MQTTBroker)
	opts.SetClientID("mqtt_influx_bridge")
	opts.SetCleanSession(true)

	// Connect to InfluxDB
	influx_client := influxdb.NewClient(config.InfluxDBHost, config.InfluxToken)
	_, err := influx_client.Health(context.Background())
	if err != nil {
		log.Fatal(err.Error())
	}

	if influx_client == nil {
		log.Fatal("InfluxDB client is nil")
	}

	// Connect to the MQTT broker
	mqtt_client := paho.NewClient(opts)
	if token := mqtt_client.Connect(); token.Wait() && token.Error() != nil {
		log.Fatal(token.Error())
	}

	// Subscribe to the MQTT topic
	if token := mqtt_client.Subscribe(config.MQTTTopic, 1, messageHandler(influx_client)); token.Wait() && token.Error() != nil {
		log.Fatal(token.Error())
	}

	// Wait for a signal to quit
	<-quit
}

// messageHandler is called when a message is received from MQTT
func messageHandler(influx_client influxdb.Client) func (client paho.Client, msg paho.Message) {
	return func (client paho.Client, msg paho.Message) {	
		// Parse the message
		mqttMessage, err := parseMessage(msg)
		if err != nil {
			println("Error parsing message")
			log.Println(err.Error())
			return
		}

		// Write the message to InfluxDB
		err = writeMessage(influx_client, mqttMessage)
		if err != nil {
			log.Println(err.Error())
			println("Error writing message to InfluxDB")
			return
		}
	}
}

// parseMessage parses the message received from MQTT
func parseMessage(msg paho.Message) (MQTTMessage, error) {
	// example topic: cm-project/gateway/device02/led_status
	// device: device02
	// command: led_status
	// value: 1/0

	// Split the topic into parts
	topicParts := strings.Split(msg.Topic(), "/")
	if len(topicParts) < 3 {
		return MQTTMessage{}, errors.New("Invalid topic")
	}

	// Parse the device name
	device := topicParts[2]

	println("Device:", device)

	// Parse the command
	command := topicParts[3]

	// Parse the value to int
	value, err := strconv.Atoi(string(msg.Payload()))
	if err != nil {
		return MQTTMessage{}, err
	}

	// Return the parsed message
	return MQTTMessage{
		Device: device,
		Command: command,
		Value: value,
	}, nil
}

// writeMessage writes the message to InfluxDB
func writeMessage(influx_client influxdb.Client, mqttMessage MQTTMessage) error {
	println("Writing message to InfluxDB")

	if influx_client == nil {
		println("InfluxDB client is nil")
		// Connect to InfluxDB
		influx_client := influxdb.NewClient(config.InfluxDBHost, config.InfluxToken)
		_, err := influx_client.Health(context.Background())
		if err != nil {
			return errors.New(err.Error())
		}

		if influx_client == nil {
			return errors.New("InfluxDB client is nil")
		}
	}

	// Create a new InfluxDB writing client
	writeAPI := influx_client.WriteAPIBlocking("cm-project", "cm-project")

	// Create a new point
	p:= influxdb.NewPoint(
		config.InfluxMeasurement,
		map[string]string{"device": mqttMessage.Device, "command": mqttMessage.Command},
		map[string]interface{}{"value": mqttMessage.Value},
		time.Now(),
	)

	// Write the point
	err := writeAPI.WritePoint(context.Background(), p)
	if err != nil {
		return err
	}

	return nil
}

// func queryDB(clnt influxdb.Client, cmd string) (res []influxdb.Result, err error) {
// 	q := influxdb.Query{
// 		Command:  cmd,
// 		Database: config.InfluxDBName,
// 	}
// 	if response, err := clnt.Query(q); err == nil {
// 		if response.Error() != nil {
// 			return res, response.Error()
// 		}
// 		res = response.Results
// 	}
// 	return res, nil
// }