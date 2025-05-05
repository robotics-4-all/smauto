# An index of all current MQTT Brokers {'broker_name': broker_object}. Gets populated by Broker's __init()__.
broker_index = {}


class BrokerAuthPlain:
    def __init__(self, parent, username, password):
        self.parent = parent
        self.username = username
        self.password = password


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
        self.ssl = ssl if ssl is not None else False


class MQTTBroker(Broker):
    def __init__(self, parent, name, host, port, auth, ssl=False,
                 basePath='', webPath='/mqtt', webPort=8883, version='3.1.1'):
        super(MQTTBroker, self).__init__(parent, name, host, port, auth, ssl)
        self.basePath = basePath
        self.webPath = webPath
        self.webPort = webPort
        self.version = version


class AMQPBroker(Broker):
    def __init__(
        self,
        parent,
        name,
        host,
        port,
        vhost,
        auth,
        topicE="amq.topic",
        rpcE="DEFAULT",
        ssl=False,
    ):
        super(AMQPBroker, self).__init__(parent, name, host, port, auth, ssl)
        self.vhost = vhost
        self.topicExchange = topicE
        self.rpcExchange = rpcE


class RedisBroker(Broker):
    def __init__(self, parent, name, host, port, auth, db=0, ssl=False):
        super(RedisBroker, self).__init__(parent, name, host, port, auth, ssl)
        self.db = db
