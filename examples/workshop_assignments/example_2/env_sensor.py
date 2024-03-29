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
        step: float  # per second

    @dataclass
    class Saw:
        min: float
        max: float
        step: float

        _internal_start: Optional[float] = 0.0

    @dataclass
    class Gaussian:
        value: float
        max_value: float
        sigma: float  # this is time (seconds)

        _internal_start: Optional[float] = 0.0

    @dataclass
    class Replay:
        values: list
        times: int


class ValueGeneratorType(Enum):
    Constant = 1
    Linear = 2
    Gaussian = 3
    Step = 5
    Saw = 6
    Sinus = 7
    Logarithmic = 8
    Exponential = 9
    Replay = 10


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
        value = None
        replay_counter = 0
        replay_iter = 0
        for c in self.components:
            if c.type in (ValueGeneratorType.Gaussian, ValueGeneratorType.Saw):
                c.properties._internal_start = start
        while True:
            msg = {}
            for c in self.components:
                if c.type == ValueGeneratorType.Constant:
                    value = c.properties.value + c.noise.generate()
                elif c.type == ValueGeneratorType.Linear:
                    value = (
                        c.properties.start + (time.time() - start) * c.properties.step
                    )
                    value += c.noise.generate()
                elif c.type == ValueGeneratorType.Saw:
                    value = (
                        c.properties.min
                        + (time.time() - c.properties._internal_start)
                        * c.properties.step
                    )
                    value += c.noise.generate()
                    if value >= c.properties.max:
                        c.properties._internal_start = time.time()
                elif c.type == ValueGeneratorType.Gaussian:
                    if (
                        time.time() - c.properties._internal_start
                        > 8 * c.properties.sigma
                    ):
                        c.properties._internal_start = time.time()
                    value = c.properties.value
                    _norm_exp = -np.power(
                        time.time()
                        - c.properties._internal_start
                        - 4 * c.properties.sigma,
                        2.0,
                    ) / (2 * np.power(c.properties.sigma, 2.0))
                    value += np.exp(_norm_exp) * (
                        c.properties.max_value - c.properties.value
                    )
                    value += c.noise.generate()
                elif c.type == ValueGeneratorType.Replay:
                    values = c.properties.values
                    times = c.properties.times
                    if replay_iter == times:
                        msg[c.name] = values[-1]
                        continue
                    value = values[replay_counter]
                    replay_counter += 1
                    replay_counter = replay_counter % (len(values))
                    if replay_counter == 0:
                        replay_iter += 1
                msg[c.name] = value

            self.publisher.publish(msg)
            print(f"Publishing {msg}")
            time.sleep(1.0 / self.hz)
            if minutes is not None:
                if time.time() - start < minutes * 60.0:
                    break


class EnvSensorMsg(PubSubMessage):
    temperature: float = 0.0
    humidity: float = 0.0
    pressure: float = 0.0


class EnvSensorNode(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 10
        self.topic = "bedroom.env"
        conn_params = ConnectionParameters(
            host="snf-889260.vm.okeanos.grnet.gr",
            port=1893,
            username="porolog",
            password="fiware",
        )
        super().__init__(
            node_name="entities.env_sensor",
            connection_params=conn_params,
            *args,
            **kwargs,
        )
        self.pub = self.create_publisher(msg_type=EnvSensorMsg, topic=self.topic)

    def init_gen_components(self):
        components = []
        temperature_properties = ValueGeneratorProperties.Gaussian(
            value=10,
            max_value=20,
            sigma=5,
        )
        _gen_type = ValueGeneratorType.Gaussian
        temperature_noise = Noise(
            _type=NoiseType.Gaussian, properties=NoiseGaussian(1, 1)
        )
        temperature_component = ValueComponent(
            _type=_gen_type,
            name="temperature",
            properties=temperature_properties,
            noise=temperature_noise,
        )
        components.append(temperature_component)
        humidity_properties = ValueGeneratorProperties.Linear(start=1, step=0.2)
        _gen_type = ValueGeneratorType.Linear
        humidity_noise = Noise(_type=NoiseType.Uniform, properties=NoiseUniform(0, 1))
        humidity_component = ValueComponent(
            _type=_gen_type,
            name="humidity",
            properties=humidity_properties,
            noise=humidity_noise,
        )
        components.append(humidity_component)
        pressure_properties = ValueGeneratorProperties.Replay(
            values=[0.2, 0.2, 0.2, 0.3, 0.25, 0.25, 0.25, 0.2],
            times=-1,
        )
        _gen_type = ValueGeneratorType.Replay
        pressure_noise = Noise(_type=NoiseType.Zero, properties=NoiseZero())
        pressure_component = ValueComponent(
            _type=_gen_type,
            name="pressure",
            properties=pressure_properties,
            noise=pressure_noise,
        )
        components.append(pressure_component)
        generator = ValueGenerator(self.topic, self.pub_freq, components, self)
        return generator

    def start(self):
        generator = self.init_gen_components()
        generator.start()


if __name__ == "__main__":
    node = EnvSensorNode()
    node.start()
