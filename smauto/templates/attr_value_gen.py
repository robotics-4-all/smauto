from enum import Enum
from dataclasses import dataclass
from os import wait
import random
import time
import numpy as np

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

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
      increase: float # per second


    @dataclass
    class Gaussian:
      value: float
      max_value: float
      sigma: float # this is time (seconds)


class ValueGeneratorType(Enum):
    Constant = 1
    Linear = 2
    Gaussian = 3
    Step = 4
    Saw = 5
    Sinus = 6
    Logarithmic = 7
    Exponential = 8
# ----------------------------------------


class ValueComponent:
    def __init__(self, _type, name, properties, noise):
        self.type = _type
        self.name = name
        self.properties = properties
        self.noise = noise


class ValueGenerator:
    def __init__(self, namespace, name, hz, components, connection):
        self.namespace = namespace
        self.name = name
        self.hz = hz
        self.components = components

        self.commlib_node = Node(
            connection_params=connection,
            debug=True
        )
        topic = f"{self.namespace}/{self.name}" if self.namespace != None else f"{self.name}"
        self.publisher = self.commlib_node.create_publisher(topic=topic)

    def generate(self, minutes = 1):
        start = time.time()
        internal_start = start
        value = None
        while time.time() - start < minutes * 60.0:
            msg = {}
            for c in self.components:
                if c.type == ValueGeneratorType.Constant:
                    value = c.properties.value + c.noise.generate()
                elif c.type == ValueGeneratorType.Linear:
                    value = c.properties.start + (time.time() - start) * c.properties.increase
                    value += c.noise.generate()
                elif c.type == ValueGeneratorType.Gaussian:
                    if time.time() - internal_start > 8 * c.properties.sigma:
                        internal_start = time.time()
                    value = c.properties.value
                    _norm_exp = -np.power(
                        time.time() - internal_start - 4 * c.properties.sigma, 2.
                    ) / (2 * np.power(c.properties.sigma, 2.))
                    value += np.exp(_norm_exp) * (c.properties.max_value - c.properties.value)
                    value += c.noise.generate()
                msg[c.name] = value

            self.publisher.publish(
                {
                    'timestamp': time.time(),
                    'data': msg
                }
            )
            print(f"Publishing {msg}")
            time.sleep(1.0 / self.hz)


if __name__ == '__main__':
    components = []

    # Constant example
    temperature_properties = ValueGeneratorProperties.Constant(value = 27)
    temperature_noise = Noise(
      _type = NoiseType.Gaussian,
      properties = NoiseGaussian(mu = 0, sigma = 0.3)
    )
    temperature_component = ValueComponent(
        _type = ValueGeneratorType.Constant,
        name = "temperature",
        properties = temperature_properties,
        noise = temperature_noise
    )
    components.append(temperature_component)

    # Linear example
    pressure_properties = ValueGeneratorProperties.Linear(start = 27, increase = 0.1)
    pressure_noise = Noise(
      _type=NoiseType.Gaussian,
      properties=NoiseGaussian(mu = 0, sigma = 0.3)
    )
    pressure_component = ValueComponent(
        _type=ValueGeneratorType.Linear,
        name="pressure",
        properties=pressure_properties,
        noise=pressure_noise
    )
    components.append(pressure_component)

    # Gaussian example
    humidity_properties = ValueGeneratorProperties.Gaussian(
        value=27,
        max_value=32,
        sigma = 2
    )
    humidity_noise = Noise(
      _type = NoiseType.Gaussian,
      properties = NoiseGaussian(mu=0, sigma=0.3)
    )
    humidity_component = ValueComponent(
        _type = ValueGeneratorType.Gaussian,
        name = "humidity",
        properties = humidity_properties,
        noise = humidity_noise
    )
    components.append(humidity_component)

    # The generator
    connection = ConnectionParameters(
        host="83.212.106.23",
        port=1893,
        username="porolog",
        password="fiware"
    )
    generator = ValueGenerator(
        namespace="smauto",
        name="bme",
        hz=2,
        components=components,
        connection=connection
    )
    generator.generate(minutes=1)
