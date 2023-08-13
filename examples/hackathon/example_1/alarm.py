#!/usr/bin/env python

import time
import random

from enum import Enum
from dataclasses import dataclass
import time
import numpy as np
from typing import Optional

from commlib.transports.mqtt import ConnectionParameters
from rich import print, console, pretty
from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node

pretty.install()
console = console.Console()




class AlarmMsg(PubSubMessage):
        state: int = 0


class AlarmNode(Node):
    def __init__(self, *args, **kwargs):
        self.tick_hz = 1
        self.topic = 'alarm'
        conn_params = ConnectionParameters(
            host='snf-889260.vm.okeanos.grnet.gr',
            port=1893,
            username='porolog',
            password='fiware',
        )
        super().__init__(
            node_name='entities.alarm',
            connection_params=conn_params,
            *args, **kwargs
        )
        self.sub = self.create_subscriber(
            msg_type=AlarmMsg,
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
    node = AlarmNode()
    node.start()