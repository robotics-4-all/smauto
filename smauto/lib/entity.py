from collections import deque
from commlib.endpoints import endpoint_factory, EndpointType, TransportType

from .broker import MQTTBroker, AMQPBroker, RedisBroker

# Broker classes and their corresponding TransportType
broker_tt = {
    MQTTBroker: TransportType.MQTT,
    AMQPBroker: TransportType.AMQP,
    RedisBroker: TransportType.REDIS
}


# A class representing an entity communicating via an MQTT broker on a specific topic
class Entity:
    """
    The Entity class represents an entity communicating via an MQTT broker on a specific topic.
    ...

    Attributes
    ----------
        name: str
            Entity name. e.g: 'temperature_sensor'
        topic: str
            Topic on which entity communicates. e.g: 'sensors.temp_sensor' corresponds to topic sensors/temp_sensor
        state: dictionary
            Dictionary from the entity's state JSON. Initial state is a blank dictionary {}
        subscriber:
            Communication endpoint built using commlib-py used to subscribe to the Entity's topic

    Methods
    -------
        add_automation(self, automation): Adds an Automation reference to this Entity. Meant to be called by the
            Automation constructor
        update_state(self, new_state): Function for updating Entity state. Meant to be used as a callback function by
            the Entity's subscriber object (commlib-py).



    """

    def __init__(self, parent, name, etype, freq, topic, broker, attributes):
        """
        Creates and returns an Entity object
        :param name: Entity name. e.g: 'temperature_sensor'
        :param topic: Topic on which entity communicates using the Broker. e.g: 'sensors.temp_sensor' corresponds to
                        topic sensors/temp_sensor
        :param broker: Reference to the Broker used for communications
        :param parent: Parameter required for Custom Class compatibility in textX
        :param attributes: List of Attribute objects belonging to the Entity
        """
        # TextX parent attribute. Required to use Entity as a custom class during metamodel instantiation
        self.parent = parent
        # Entity name
        self.name = name
        self.camel_name = self.to_camel_case(name)
        self.etype = etype
        self.freq = freq if freq not in (None, 0) else 1
        # MQTT topic for Entity
        self.topic = topic
        # Entity state
        self.state = {}
        # Set Entity's MQTT Broker
        self.broker = broker
        # Entity's Attributes
        self.attributes = attributes
        # Attributes Dictionary
        self.attributes_dict = {attribute.name: attribute for attribute in self.attributes}
        self.attributes_buff = {attribute.name: None for attribute in self.attributes}

        # Inspect Attributes and if an attribute is a DictAttribute,
        # create its items dictionary for easy updating
        for attr_name, attribute in self.attributes_dict.items():
            if type(attribute) is DictAttribute:
                attribute.items_dict = {
                    item.name: item for item in attribute.items
                }

    def get_buffer(self, attr_name):
        if len(self.attributes_buff[attr_name]) != \
            self.attributes_buff[attr_name].maxlen:
            return [0] * self.attributes_buff[attr_name].maxlen
        else:
            return self.attributes_buff[attr_name]

    def init_attr_buffer(self, attr_name, size):
        self.attributes_buff[attr_name] = deque(maxlen=size)
        # self.attributes_buff[attr_name].extend([0] * size)

    def to_camel_case(self, snake_str):
        return "".join(x.capitalize() for x in snake_str.lower().split("_"))

    def start(self):
        # Create and start communications subscriber on Entity's topic
        self.subscriber = endpoint_factory(
            EndpointType.Subscriber, broker_tt[type(self.broker)])(
            topic=self.topic,
            conn_params=self.broker.conn_params,
            on_message=self.update_state
        )
        self.subscriber.run()

        # Create communications publisher on Entity's topic
        self.publisher = endpoint_factory(EndpointType.Publisher, broker_tt[type(self.broker)])(
            topic=self.topic,
            conn_params=self.broker.conn_params,
        )

    # Callback function for updating Entity state and triggering automations evaluation
    def update_state(self, new_state):
        """
        Function for updating Entity state. Meant to be used as a callback function by the Entity's subscriber object
        (commlib-py).
        :param new_state: Dictionary containing the Entity's state
        :return:
        """
        # Update state
        self.state = new_state
        # Update attributes based on state
        self.update_attributes(self.attributes_dict, new_state)
        self.update_buffers(self.attributes_buff, new_state)

    @staticmethod
    def update_buffers(root, state_dict):
        """
        Recursive function used by update_state() mainly to updated
            dictionaries/objects and normal Attributes.
        """
        # Update attributes
        for attribute, value in state_dict.items():

            # If value is a dictionary, also update the Dict's subattributes/items
            if root[attribute] is not None:
                root[attribute].append(value)

    @staticmethod
    def update_attributes(root, state_dict):
        """
        Recursive function used by update_state() mainly to updated
            dictionaries/objects and normal Attributes.
        """
        # Update attributes
        for attribute, value in state_dict.items():

            # If value is a dictionary, also update the Dict's subattributes/items
            if type(value) is dict:
                Entity.update_attributes(root[attribute].value, value)
            else:
                root[attribute].value = value


class Attribute:
    def __init__(self, parent, name, value=None):
        self.parent = parent
        self.name = name
        self.value = value


class IntAttribute(Attribute):
    def __init__(self, parent, name, generator, noise):
        super().__init__(parent, name)
        self.generator = generator
        self.noise = noise
        self.type = 'int'
        if self.value is None:
            self.value = 0


class FloatAttribute(Attribute):
    def __init__(self, parent, name, generator, noise):
        super().__init__(parent, name)
        self.generator = generator
        self.noise = noise
        self.type = 'float'
        if self.value is None:
            self.value = 0.0


class StringAttribute(Attribute):
    def __init__(self, parent, name):
        super().__init__(parent, name)
        self.type = 'str'
        if self.value is None:
            self.value = ""


class BoolAttribute(Attribute):
    def __init__(self, parent, name):
        super().__init__(parent, name)
        self.type = 'bool'
        if self.value is None:
            self.value = False


class ListAttribute(Attribute):
    def __init__(self, parent, name):
        super().__init__(parent, name)
        self.type = 'list'
        if self.value is None:
            self.value = []


class DictAttribute(Attribute):
    def __init__(self, parent, name, items):
        # Create dictionary structure from items
        value = {item.name: item for item in items}
        self.type = "dict"
        super().__init__(parent, name, value=value)
        self.items = items
        if self.items is None:
            self.items = []
