#!/usr/bin/env python

import time
import random

from enum import Enum
from dataclasses import dataclass
from os import wait
import time
import numpy as np

from commlib.transports.mqtt import ConnectionParameters
from rich import print, console, pretty
from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node

pretty.install()
console = console.Console()


# Noise definitions
# ----------------------------------------
@dataclass
class NoiseUniform:
    min: float
    max: float


@dataclass
class NoiseGaussian:
    mu: float
    sigma: float


@dataclass
class NoiseZero:
    pass


class NoiseType(Enum):
    Uniform = 1
    Gaussian = 2
    Zero = 3


class Noise:
    def __init__(self, _type, properties):
        self.type = _type
        self.properties = properties

    def generate(self):
        if self.type == NoiseType.Uniform:
            return random.uniform(self.properties.min, self.properties.max)
        elif self.type == NoiseType.Gaussian:
            return random.gauss(self.properties.mu, self.properties.sigma)
        elif self.type == NoiseType.Zero:
            return 0
# ----------------------------------------

# Value generator definitions
# ----------------------------------------

@dataclass
class ValueGeneratorProperties:
    @dataclass
    class Constant:
      value: float

    @dataclass
    class Linear:
      start: float
      step: float # per second

    @dataclass
    class Gaussian:
        value: float
        max_value: float
        sigma: float # this is time (seconds)


class ValueGeneratorType(Enum):
    Constant = 1
    Linear = 2
    Gaussian = 3
    Step = 5
    Saw = 6
    Sinus = 7
    Logarithmic = 8
    Exponential = 9
# ----------------------------------------


class ValueComponent:
    def __init__(self, _type, name, properties, noise):
        self.type = _type
        self.name = name
        self.properties = properties
        self.noise = noise


class ValueGenerator:
    def __init__(self, topic, hz, components, commlib_node):
        self.topic = topic
        self.hz = hz
        self.components = components
        self.commlib_node = commlib_node

        self.publisher = self.commlib_node.create_publisher(topic=topic)

    def start(self, minutes=None):
        start = time.time()
        internal_start = start
        value = None
        while True:
            msg = {}
            for c in self.components:
                if c.type == ValueGeneratorType.Constant:
                    value = c.properties.value + c.noise.generate()
                elif c.type == ValueGeneratorType.Linear:
                    value = c.properties.start + (time.time() - start) * c.properties.step
                    value += c.noise.generate()
                elif c.type == ValueGeneratorType.Gaussian:
                    if time.time() - internal_start > 8 * c.properties.sigma:
                        internal_start = time.time()
                    value = c.properties.value
                    _norm_exp = -np.power(time.time() - internal_start - 4 * c.properties.sigma, 2.) / (2 * np.power(c.properties.sigma, 2.))
                    value += np.exp(_norm_exp) * (c.properties.max_value - c.properties.value)
                    value += c.noise.generate()
                msg[c.name] = value

            self.publisher.publish(
                msg
            )
            print(f"Publishing {msg}")
            time.sleep(1.0 / self.hz)
            if minutes is not None:
                if time.time() - start < minutes * 60.0:
                    break


class BedroomHumiditySensorMsg(PubSubMessage):
        humidity: float = 0.0


class BedroomHumiditySensorNode(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 1
        self.topic = 'bedroom.humidity'
        conn_params = ConnectionParameters(
            host='83.212.106.23',
            port=1893,
            username='porolog',
            password='fiware',
        )
        super().__init__(
            node_name='entities.bedroom_humidity_sensor',
            connection_params=conn_params,
            *args, **kwargs
        )
        self.pub = self.create_publisher(
            msg_type=BedroomHumiditySensorMsg,
            topic=self.topic
        )

    def init_gen_components(self):
        components = []
        humidity_properties = ValueGeneratorProperties.Linear(
            start=0,
            step=0.1
        )
        _gen_type = ValueGeneratorType.Linear
        humidity_noise = Noise(
            _type=NoiseType.Gaussian,
            properties=NoiseGaussian(0, 0.05)
        )
        humidity_component = ValueComponent(
            _type=_gen_type,
            name="humidity",
            properties = humidity_properties,
            noise=humidity_noise
        )
        components.append(humidity_component)
        generator = ValueGenerator(
            self.topic,
            self.pub_freq,
            components,
            self
        )
        return generator


    def start(self):
        generator = self.init_gen_components()
        generator.start()

"""
    def start(self):
        self.run()
        rate = Rate(self.pub_freq)
        while True:
            msg = self.gen_data()
            print(f'[bold]\[bedroom_humidity_sensor][/bold] Sending data: {msg}')
            self.pub.publish(msg)
            rate.sleep()

    def gen_data(self):
        msg = BedroomHumiditySensorMsg()
        if not hasattr(self, "_humidity"):
            val = 
        else:
            val = self._humidity + 0.1
        if val > :
            val = 
        self._humidity = val
        msg.humidity = val
        return msg

"""


if __name__ == '__main__':
    node = BedroomHumiditySensorNode()
    node.start()