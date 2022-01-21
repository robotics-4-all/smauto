from commlib.transports.mqtt import ConnectionParameters as MQTT_ConnectionParameters, Credentials as MQTT_Credentials
from commlib.transports.amqp import ConnectionParameters as AMQP_ConnectionParameters, Credentials as AMQP_Credentials
from commlib.transports.redis import ConnectionParameters as Redis_ConnectionParameters, Credentials as Redis_Credentials

# An index of all current MQTT Brokers {'broker_name': broker_object}. Gets populated by Broker's __init()__.
broker_index = {}


class BrokerAuthPlain:
    def __init__(self, parent, username, password):
        self.parent = parent
        self.username = username
        self.password = password


# A class representing an Automation
class Broker:
    """
    The Broker class represents an MQTT broker structure used by Entities.
    ...

    Attributes
    ----------
        name: str
            Broker name. e.g: 'home_mqtt'
        host: str
            IP address of the MQTT broker used for communications. e.g: '192.168.1.2'
        credentials: BrokerAuthPlain object
            Object used for authentication

    Methods
    -------
    ---
    """

    def __init__(self, parent, name, host, port, credentials):
        """
        Creates and returns a Broker object
        :param name: Broker name. e.g: 'home_mqtt'
        :param host: IP address of the MQTT broker used for communications. e.g: '192.168.1.2'
        :param port: Port used for MQTT broker communication
        :param credentials: BrokerAuthPlain used for authentication
        :param parent: Parameter required for Custom Class compatibility in textX
        """
        # TextX parent attribute. Required to use as custom class during metamodel instantiation
        self.parent = parent
        # MQTT Broker
        self.name = name
        self.host = host
        self.port = port
        self.credentials = credentials
        

class MQTTBroker(Broker):
    
    def __init__(self, parent, name, host, port, credentials):
        
        super(MQTTBroker, self).__init__(parent, name, host, port, credentials)

        # Create commlib-py Credentials and ConnectionParameters objects for MQTT
        self.credentials = MQTT_Credentials(self.credentials.username, self.credentials.password)
        self.conn_params = MQTT_ConnectionParameters(host=self.host, port=self.port, creds=self.credentials)


class AMQPBroker(Broker):

    def __init__(self, parent, name, host, port, vhost, credentials, exchange=''):

        super(AMQPBroker, self).__init__(parent, name, host, port, credentials)

        self.vhost = vhost
        self.exchange = exchange

        # Create commlib-py Credentials and ConnectionParameters objects for AMQP
        self.credentials = AMQP_Credentials(self.credentials.username, self.credentials.password)
        self.conn_params = AMQP_ConnectionParameters(host=self.host, port=self.port,
                                                     vhost=vhost, creds=self.credentials)


class RedisBroker(Broker):

    def __init__(self, parent, name, host, port, credentials, db=0):

        super(RedisBroker, self).__init__(parent, name, host, port, credentials)

        self.db = db

        # Create commlib-py Credentials and ConnectionParameters objects for Redis
        self.credentials = Redis_Credentials(self.credentials.username, self.credentials.password)
        self.conn_params = Redis_ConnectionParameters(host=self.host, port=self.port,
                                                      creds=self.credentials, db=self.db)

