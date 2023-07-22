#!/usr/bin/env python

import time

from commlib.msg import PubSubMessage
from commlib.node import Node

class WeatherStation(PubSubMessage):
    temperature: float = 0.0
    humidity: float = 0.0
    airQuality: float = 0.0


TOPIC = 'porch/weather_station'


if __name__ == '__main__':
    from commlib.transports.mqtt import ConnectionParameters
    conn_params = ConnectionParameters()

    node = Node(node_name='sensors.sonar.front',
                connection_params=conn_params,
                # heartbeat_uri='nodes.add_two_ints.heartbeat',
                debug=True)

    pub = node.create_publisher(msg_type=WeatherStation,
                                topic=TOPIC)

    node.run()

    msg = WeatherStation()
    msg.temperature = 34
    msg.humidity = 34
    pub.publish(msg)
    time.sleep(3)
    msg.temperature = 25
    msg.humidity = 10
    pub.publish(msg)
    time.sleep(1)

