#!/usr/bin/env python

import time
import random

from commlib.transports.mqtt import ConnectionParameters
from rich import print, console, pretty
from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node

pretty.install()
console = console.Console()

class WeatherStationMsg(PubSubMessage):
        temperature: float = 0.0
        humidity: float = 0.0
        airQuality: float = 0.0


class WeatherStationNode(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 1
        self.topic = 'porch.weather_station'
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        super().__init__(
            node_name='entities.weather_station',
            connection_params=conn_params,
            *args, **kwargs
        )
        self.pub = self.create_publisher(
            msg_type=WeatherStationMsg,
            topic=self.topic
        )

    def start(self):
        self.run()
        rate = Rate(self.pub_freq)
        while True:
            msg = self.gen_data()
            print(f'[bold]\[weather_station][/bold] Sending data: {msg}')
            self.pub.publish(msg)
            rate.sleep()

    def gen_data(self):
        msg = WeatherStationMsg()
        msg.temperature = random.uniform(10, 40)
        msg.humidity = random.uniform(10, 40)
        if not hasattr(self, "_airQuality"):
            val = 0
        else:
            val = self._airQuality + 0.1
        if val > 1:
            val = 0
        self._airQuality = val
        msg.airQuality = val
        return msg


if __name__ == '__main__':
    node = WeatherStationNode()
    node.start()