from collections import deque

from smauto.lib.broker import MQTTBroker, AMQPBroker, RedisBroker
from smauto.lib.types import Time


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

    def __init__(
        self, parent, name, etype, freq, topic, broker, attributes, description="", virtual=False
    ):
        """
        Creates and returns an Entity object
        :param name: Entity name. e.g: 'temperature_sensor'
        :param topic: Topic on which entity communicates using the Broker. e.g: 'sensors.temp_sensor' corresponds to
                        topic sensors/temp_sensor
        :param broker: Reference to the Broker used for communications
        :param parent: Parameter required for Custom Class compatibility in textX
        :param virtual: Flag to indicate if the entity is virtual or not
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
        # Flag for virtual entities
        self.virtual = virtual
        # Entity's Attributes
        self.attributes = attributes
        self.description = description
        self.attr_buffs = []
        # Attributes Dictionary
        self.attributes_dict = {
            attribute.name: attribute for attribute in self.attributes
        }
        self.attributes_buff = {attribute.name: None for attribute in self.attributes}

        # Inspect Attributes and if an attribute is a DictAttribute,
        # create its items dictionary for easy updating
        for attr_name, attribute in self.attributes_dict.items():
            if type(attribute) is DictAttribute:
                attribute.items_dict = {item.name: item for item in attribute.items}

    def get_buffer(self, attr_name):
        if (
            len(self.attributes_buff[attr_name])
            != self.attributes_buff[attr_name].maxlen
        ):
            return [0] * self.attributes_buff[attr_name].maxlen
        else:
            return self.attributes_buff[attr_name]

    def init_attr_buffer(self, attr_name, size):
        self.attributes_buff[attr_name] = deque(maxlen=size)
        # self.attributes_buff[attr_name].extend([0] * size)

    def to_camel_case(self, snake_str):
        return "".join(x.capitalize() for x in snake_str.lower().split("_"))

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
        # print(new_state)
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

    def set_virtual(self, value):
        """
        Set the virtual attribute.
        """
        self.virtual = value

    def is_virtual(self):
        """
        Check if the entity is virtual.
        """
        return self.virtual

    def update_attributes(root, state_dict):
        """
        Recursive function used by update_state() mainly to updated
            dictionaries/objects and normal Attributes.
        """
        # Update attributes
        for attribute, value in state_dict.items():
            # If value is a dictionary, also update the Dict's subattributes/items
            if root[attribute].__class__.__name__ == "TimeAttribute":
                setattr(root[attribute].value, "hour", value["hour"])
                setattr(root[attribute].value, "minute", value["minute"])
                setattr(root[attribute].value, "second", value["second"])
            elif type(value) is dict:
                Entity.update_attributes(root[attribute].value, value)
            else:
                root[attribute].value = value


class Attribute:
    def __init__(self, parent, name, value=None):
        self.parent = parent
        self.name = name
        self.value = value


class IntAttribute(Attribute):
    def __init__(self, parent, name, default, generator, noise):
        super().__init__(parent, name, default)
        self.generator = generator
        self.noise = noise
        self.type = "int"
        if self.value is None:
            self.value = 0


class FloatAttribute(Attribute):
    def __init__(self, parent, name, default, generator, noise):
        super().__init__(parent, name, default)
        self.generator = generator
        self.noise = noise
        self.type = "float"
        if self.value is None:
            self.value = 0.0


class StringAttribute(Attribute):
    def __init__(self, parent, name, default):
        super().__init__(parent, name, default)
        self.type = "str"
        if self.value is None:
            self.value = ""


class BoolAttribute(Attribute):
    def __init__(self, parent, name, default, generator):
        super().__init__(parent, name, default)
        self.generator = generator
        self.type = "bool"
        if self.value is None:
            self.value = False


class TimeAttribute(Attribute):
    def __init__(self, parent, name, default):
        super().__init__(parent, name, default)
        self.type = "time"
        if self.value is None:
            self.value = Time(self, 0, 0, 0)


class ListAttribute(Attribute):
    def __init__(self, parent, name, default, generator):
        super().__init__(parent, name, default)
        self.generator = generator
        self.type = "list"
        if self.value is None:
            self.value = []


class DictAttribute(Attribute):
    def __init__(self, parent, name, items, generator):
        # Create dictionary structure from items
        value = {item.name: item for item in items}
        self.generator = generator
        self.type = "dict"
        super().__init__(parent, name, value=value)
        self.items = items
        if self.items is None:
            self.items = []
