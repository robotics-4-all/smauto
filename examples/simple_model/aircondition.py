#!/usr/bin/env python

import time
import random

from commlib.transports.mqtt import ConnectionParameters
from rich import print
from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node

class AirconditionMsg(PubSubMessage):
        power: bool = False
        temperature: float = 0.0
        swing: bool = False
        mode: str = ''


class AirconditionNode(Node):
    def __init__(self, *args, **kwargs):
        self.tick_hz = 1
        self.topic = 'bedroom.aircondition'
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        super().__init__(
            node_name='entities.aircondition',
            connection_params=conn_params,
            *args, **kwargs
        )
        self.sub = self.create_subscriber(
            msg_type=AirconditionMsg,
            topic=self.topic,
            on_message=self._on_message
        )

    def start(self):
        self.run()
        rate = Rate(self.tick_hz)
        while True:
            rate.sleep()

    def _on_message(self, msg):
        print(f'[*] State change command received: {msg}')

if __name__ == '__main__':
    node = AirconditionNode()
    node.start()