import os
from textx import language, metamodel_from_file


def get_metamodel():
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('lang/smauto.tx'),
        classes=[Entity, Attribute, IntAttribute, FloatAttribute,
                 StringAttribute, BoolAttribute, ListAttribute,
                 DictAttribute, Broker, MQTTBroker, AMQPBroker,
                 RedisBroker, BrokerAuthPlain, Automation, Action,
                 IntAction, FloatAction, StringAction, BoolAction,
                 List, Dict]
    )
    return metamodel


@language('smauto', '*.auto')
def language():
    "SmartAutomation (smauto) language"
    return get_metamodel()
