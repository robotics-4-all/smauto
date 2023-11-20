#!/usr/bin/env python

import time
import random

from enum import Enum
from dataclasses import dataclass
import time
import numpy as np
from typing import Optional

from commlib.transports.mqtt import ConnectionParameters
from rich import print
from commlib.msg import PubSubMessage, BaseModel
from commlib.utils import Rate
from commlib.node import Node
from datetime import datetime


class Time(BaseModel):
    hour: int = 0
    minute: int = 0
    second: int = 0
    time_str: str = ''


class ClockMsg(PubSubMessage):
    time: Time


class SystemClock(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 1
        self.topic = 'system.clock'
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        super().__init__(
            node_name='system_clock',
            connection_params=conn_params,
            *args, **kwargs
        )
        self.pub = self.create_publisher(
            msg_type=ClockMsg,
            topic=self.topic
        )
        self.rate = Rate(self.pub_freq)

    def start(self):
        self.run()
        while True:
            self.send_msg()
            self.rate.sleep()

    def send_msg(self):
        now = datetime.now()
        t_str = now.strftime("%H:%M:%S")
        hour = int(now.hour)
        minute = int(now.minute)
        second = int(now.second)
        msg = ClockMsg(time=Time(
            hour=hour,
            minute=minute,
            second=second,
            time_str=t_str
        ))
        self.pub.publish(msg)


if __name__ == '__main__':
    clock = SystemClock()
    clock.start()