from commlib.transports.amqp import ConnectionParameters as AMQP_ConnectionParameters
from commlib.transports.redis import ConnectionParameters as Redis_ConnectionParameters

# An index of all current MQTT Brokers {'broker_name': broker_object}. Gets populated by Broker's __init()__.
broker_index = {}


class BrokerAuthPlain:
    def __init__(self, parent, username, password):
        self.parent = parent
        self.username = username
        self.password = password


# A class representing an Automation
class Broker:
    def __init__(self, parent, name, host, port, auth, ssl):
        """
        Creates and returns a Broker object
        :param name: Broker name. e.g: 'home_mqtt'
        :param host: IP address of the MQTT broker used for communications. e.g: '192.168.1.2'
        :param port: Port used for MQTT broker communication
        :param parent: Parameter required for Custom Class compatibility in textX
        """
        # TextX parent attribute. Required to use as custom class during metamodel instantiation
        self.parent = parent
        # MQTT Broker
        self.name = name
        self.host = host
        self.port = port
        self.auth = auth
        self.ssl = ssl


class MQTTBroker(Broker):
    def __init__(self, parent, name, host, port, auth, ssl=False):
        super(MQTTBroker, self).__init__(parent, name, host, port, auth, ssl)
        # lazy import
        from commlib.transports.mqtt import ConnectionParameters
        if self.auth is None:
            username = ''
            password = ''
        else:
            username = self.auth.username
            password = self.auth.password
        self.conn_params = ConnectionParameters(
            host=self.host,
            port=self.port,
            username=username,
            password=password,
        )


class AMQPBroker(Broker):

    def __init__(self, parent, name, host, port, vhost, auth,
                 topicExchange='amq.topic', rpcExchange='DEFAULT',
                 ssl=False):
        super(AMQPBroker, self).__init__(parent, name, host, port, auth, ssl)
        self.vhost = vhost
        self.topicExchange = topicExchange
        self.rpcExchange = rpcExchange

        from commlib.transports.amqp import ConnectionParameters
        # Create commlib-py Credentials and ConnectionParameters objects for AMQP
        if self.auth is None:
            username = ''
            password = ''
        else:
            username = self.auth.username
            password = self.auth.password
        self.conn_params = ConnectionParameters(
            host=self.host,
            port=self.port,
            username=username,
            password=password,
        )

class RedisBroker(Broker):
    def __init__(self, parent, name, host, port, auth, db=0, ssl=False):
        super(RedisBroker, self).__init__(parent, name, host, port, auth, ssl)
        self.db = db

        from commlib.transports.redis import ConnectionParameters
        # Create commlib-py Credentials and ConnectionParameters objects for AMQP
        if self.auth is None:
            username = ''
            password = ''
        else:
            username = self.auth.username
            password = self.auth.password
        self.conn_params = ConnectionParameters(
            host=self.host,
            port=self.port,
            username=username,
            password=password,
        )
