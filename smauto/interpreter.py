#!/usr/bin/env python3


import logging
import os
import time
import pathlib

from concurrent.futures import ThreadPoolExecutor

from colorama import Fore, Style, init
from commlib.endpoints import EndpointType, TransportType, endpoint_factory
from commlib.transports.mqtt import \
    ConnectionParameters as MQTT_ConnectionParameters
from commlib.transports.mqtt import Credentials as MQTT_Credentials
from textx import metamodel_from_file

from smauto.lib.automation import (Action, Automation, BoolAction, Dict, FloatAction,
                            IntAction, List, StringAction)
from smauto.lib.broker import (AMQPBroker, Broker, BrokerAuthPlain, MQTTBroker,
                        RedisBroker)
from smauto.lib.entity import (Attribute, BoolAttribute, DictAttribute, Entity,
                        FloatAttribute, IntAttribute, ListAttribute,
                        StringAttribute)


CURRENT_FPATH = pathlib.Path(__file__).parent.resolve()


def run_automation(automation):
    automation.build_condition()
    triggered = False
    print(f"{automation.name} condition:\n{automation.condition.cond_lambda}\n")
    # Evaluate
    while not triggered:
        triggered, msg = automation.evaluate()
        # Check if action is triggered
        if triggered:
            print(f"{Fore.MAGENTA}{automation.name}: {triggered}{Style.RESET_ALL}")
            # If automation triggered run its actions
            automation.trigger()
        else:
            print(f"{automation.name}: {triggered}")


def interpret_model_from_path(model_path: str, max_workers: int = 10):
    # Initialize full metamodel
    metamodel = metamodel_from_file(
        CURRENT_FPATH.joinpath('lang/smauto.tx'),
        classes=[Entity, Attribute, IntAttribute, FloatAttribute,
                 StringAttribute, BoolAttribute, ListAttribute,
                 DictAttribute, Broker, MQTTBroker, AMQPBroker,
                 RedisBroker, BrokerAuthPlain, Automation, Action,
                 IntAction, FloatAction, StringAction, BoolAction,
                 List, Dict]
    )

    # Parse model
    model = metamodel.model_from_file(model_path)

    # Build entities dictionary in model. Needed for evaluating conditions
    model.entities_dict = {entity.name: entity for entity in model.entities}

    # Evaluate automations, run applicable actions and print results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for automation in model.automations:
            executor.submit(run_automation, (automation))
    print('[*] All automations completed!!')
