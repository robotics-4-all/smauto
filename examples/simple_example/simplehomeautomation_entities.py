#!/usr/bin/env python

"""
If you are going to execute this in google colab, uncomment the next line
!pip install commlib-py>=0.11.0
"""

import time
import random

from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel
import time
import numpy as np
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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


class Time(BaseModel):
    hour: int = 0
    minute: int = 0
    second: int = 0
    time_str: str = ""


class ClockMsg(PubSubMessage):
    time: Time


class SystemClock(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 1
        self.topic = "system.clock"
        from commlib.transports.mqtt import ConnectionParameters

        conn_params = ConnectionParameters(
            host="localhost",
            port=1883,
            username="",
            password="",
        )
        super().__init__(
            node_name="system_clock", connection_params=conn_params, *args, **kwargs
        )
        self.pub = self.create_publisher(msg_type=ClockMsg, topic=self.topic)
        self.rate = Rate(self.pub_freq)

    def start(self):
        self.run()
        print(f"[*] Initiated System Clock @ {self.topic}")
        while True:
            self.send_msg()
            self.rate.sleep()

    def send_msg(self):
        now = datetime.now()
        t_str = now.strftime("%H:%M:%S")
        hour = int(now.hour)
        minute = int(now.minute)
        second = int(now.second)
        msg = ClockMsg(
            time=Time(hour=hour, minute=minute, second=second, time_str=t_str)
        )
        self.pub.publish(msg)


# ThreadPoolExecutor worker callback
def _worker_clb(f):
    e = f.exception()
    if e is None:
        return
    trace = []
    tb = e.__traceback__
    while tb is not None:
        trace.append(
            {
                "filename": tb.tb_frame.f_code.co_filename,
                "name": tb.tb_frame.f_code.co_name,
                "lineno": tb.tb_lineno,
            }
        )
        tb = tb.tb_next
    print({"type": type(e).__name__, "message": str(e), "trace": trace})


class MotionDetectorMsg(PubSubMessage):
    detected: bool = False
    posX: int = 0
    posY: int = 0
    mode: str = ""


class MotionDetectorNode(Node):
    def __init__(self, *args, **kwargs):
        self.pub_freq = 1
        self.topic = "bedroom.motion_detector"
        self.name = "motion_detector"
        from commlib.transports.mqtt import ConnectionParameters

        conn_params = ConnectionParameters(
            host="localhost",
            port=1883,
            username="",
            password="",
        )
        super().__init__(
            node_name="entities.motion_detector",
            connection_params=conn_params,
            *args,
            **kwargs,
        )
        self.pub = self.create_publisher(msg_type=MotionDetectorMsg, topic=self.topic)

    def init_gen_components(self):
        components = []
        detected_properties = ValueGeneratorProperties.Constant(0)
        _gen_type = ValueGeneratorType.Constant
        detected_noise = Noise(_type=NoiseType.Zero, properties=NoiseZero())
        detected_component = ValueComponent(
            _type=_gen_type,
            name="detected",
            properties=detected_properties,
            noise=detected_noise,
        )
        components.append(detected_component)
        posX_properties = ValueGeneratorProperties.Constant(0)
        _gen_type = ValueGeneratorType.Constant
        posX_noise = Noise(_type=NoiseType.Zero, properties=NoiseZero())
        posX_component = ValueComponent(
            _type=_gen_type, name="posX", properties=posX_properties, noise=posX_noise
        )
        components.append(posX_component)
        posY_properties = ValueGeneratorProperties.Constant(0)
        _gen_type = ValueGeneratorType.Constant
        posY_noise = Noise(_type=NoiseType.Zero, properties=NoiseZero())
        posY_component = ValueComponent(
            _type=_gen_type, name="posY", properties=posY_properties, noise=posY_noise
        )
        components.append(posY_component)
        mode_properties = ValueGeneratorProperties.Constant(0)
        _gen_type = ValueGeneratorType.Constant
        mode_noise = Noise(_type=NoiseType.Zero, properties=NoiseZero())
        mode_component = ValueComponent(
            _type=_gen_type, name="mode", properties=mode_properties, noise=mode_noise
        )
        components.append(mode_component)
        generator = ValueGenerator(self.topic, self.pub_freq, components, self)
        return generator

    def start(self, executor=None):
        self.run()
        generator = self.init_gen_components()
        if executor:
            work = executor.submit(generator.start).add_done_callback(_worker_clb)
            print(f"[*] Initiated Entity {self.name} @ {self.topic}")
            return work
        else:
            generator.start()
            return self


class BedroomLampMsg(PubSubMessage):
    power: bool = False


class BedroomLampNode(Node):
    def __init__(self, *args, **kwargs):
        self.tick_hz = 1
        self.topic = "bedroom.lamp"
        self.name = "bedroom_lamp"
        from commlib.transports.mqtt import ConnectionParameters

        conn_params = ConnectionParameters(
            host="localhost",
            port=1883,
            username="",
            password="",
        )
        super().__init__(
            node_name="entities.bedroom_lamp",
            connection_params=conn_params,
            *args,
            **kwargs,
        )
        self.sub = self.create_subscriber(
            msg_type=BedroomLampMsg, topic=self.topic, on_message=self._on_message
        )

    def start(self, executor=None):
        self.run()
        print(f"[*] Initiated Entity {self.name} @ {self.topic}")
        return self

    def _on_message(self, msg):
        print(f"[*] State change command received: {msg}")


if __name__ == "__main__":
    sensors = []
    actuators = []
    workers = []
    max_workers = 100
    actuators.append(BedroomLampNode())
    sensors.append(MotionDetectorNode())
    sclock = SystemClock()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        sclock_work = executor.submit(sclock.start).add_done_callback(_worker_clb)
        for node in sensors:
            work = node.start(executor)
            workers.append(work)
        for node in actuators:
            node.start()
