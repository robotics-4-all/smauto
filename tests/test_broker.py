"""Tests for smauto.lib.broker — Broker classes, RESTEndpoint, EntitySource, Property."""

from smauto.lib.broker import (
    Broker,
    MQTTBroker,
    AMQPBroker,
    RedisBroker,
    RESTEndpoint,
    BrokerAuthPlain,
    EntitySource,
    Property,
)


class TestBrokerAuthPlain:
    def test_init(self):
        auth = BrokerAuthPlain(None, "user", "pass")
        assert auth.username == "user"
        assert auth.password == "pass"
        assert auth.parent is None


class TestBroker:
    def test_init(self):
        auth = BrokerAuthPlain(None, "u", "p")
        b = Broker(None, "test_broker", "localhost", 1883, auth, None)
        assert b.name == "test_broker"
        assert b.host == "localhost"
        assert b.port == 1883
        assert b.auth is auth
        assert b.ssl is False  # None -> False

    def test_ssl_true(self):
        b = Broker(None, "b", "host", 1883, None, True)
        assert b.ssl is True

    def test_ssl_false_explicit(self):
        b = Broker(None, "b", "host", 1883, None, False)
        assert b.ssl is False


class TestMQTTBroker:
    def test_init_defaults(self):
        b = MQTTBroker(None, "mqtt", "localhost", 1883, None)
        assert b.name == "mqtt"
        assert b.host == "localhost"
        assert b.port == 1883
        assert b.ssl is False
        assert b.basePath == ""
        assert b.webPath == "/mqtt"
        assert b.webPort == 8883

    def test_init_custom(self):
        auth = BrokerAuthPlain(None, "u", "p")
        b = MQTTBroker(
            None,
            "mqtt",
            "10.0.0.1",
            8883,
            auth,
            ssl=True,
            basePath="/base",
            webPath="/ws",
            webPort=9883,
        )
        assert b.ssl is True
        assert b.basePath == "/base"
        assert b.webPath == "/ws"
        assert b.webPort == 9883
        assert b.auth.username == "u"

    def test_inherits_broker(self):
        b = MQTTBroker(None, "m", "h", 1883, None)
        assert isinstance(b, Broker)


class TestAMQPBroker:
    def test_init_defaults(self):
        b = AMQPBroker(None, "amqp", "localhost", 5672, "/", None)
        assert b.name == "amqp"
        assert b.vhost == "/"
        assert b.topicExchange == "amq.topic"
        assert b.rpcExchange == "DEFAULT"
        assert b.ssl is False

    def test_init_custom(self):
        b = AMQPBroker(
            None,
            "amqp",
            "host",
            5672,
            "/prod",
            None,
            topicE="custom.topic",
            rpcE="custom.rpc",
            ssl=True,
        )
        assert b.topicExchange == "custom.topic"
        assert b.rpcExchange == "custom.rpc"
        assert b.ssl is True

    def test_inherits_broker(self):
        b = AMQPBroker(None, "a", "h", 5672, "/", None)
        assert isinstance(b, Broker)


class TestRedisBroker:
    def test_init_defaults(self):
        b = RedisBroker(None, "redis", "localhost", 6379, None)
        assert b.db == 0
        assert b.ssl is False

    def test_init_custom(self):
        b = RedisBroker(None, "redis", "host", 6379, None, db=3, ssl=True)
        assert b.db == 3
        assert b.ssl is True

    def test_inherits_broker(self):
        b = RedisBroker(None, "r", "h", 6379, None)
        assert isinstance(b, Broker)


class TestRESTEndpoint:
    def test_init_defaults(self):
        ep = RESTEndpoint(None, "api", "GET", "localhost", 8080, "/data")
        assert ep.name == "api"
        assert ep.verb == "GET"
        assert ep.host == "localhost"
        assert ep.port == 8080
        assert ep.path == "/data"
        assert ep.baseUrl == ""
        assert ep.queryParams == []
        assert ep.pathParams == []
        assert ep.bodyParams == []
        assert ep.headers == []

    def test_init_custom(self):
        qp = [Property(None, "q", "str")]
        hp = [Property(None, "auth", "str")]
        ep = RESTEndpoint(
            None,
            "api",
            "POST",
            "host",
            443,
            "/api/v1",
            baseUrl="https://example.com",
            queryParams=qp,
            headers=hp,
        )
        assert ep.baseUrl == "https://example.com"
        assert len(ep.queryParams) == 1
        assert len(ep.headers) == 1
        assert ep.pathParams == []
        assert ep.bodyParams == []


class TestProperty:
    def test_init(self):
        p = Property(None, "count", "int")
        assert p.name == "count"
        assert p.type == "int"
        assert p.parent is None


class TestEntitySource:
    def test_init(self):
        broker = MQTTBroker(None, "b", "h", 1883, None)
        es = EntitySource(None, broker)
        assert es.ref is broker
        assert es.parent is None
