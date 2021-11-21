#!/usr/bin/env python3


import logging
import os
import time

from concurrent.futures import ThreadPoolExecutor

from colorama import Fore, Style, init
from commlib.endpoints import EndpointType, TransportType, endpoint_factory
from commlib.transports.mqtt import \
    ConnectionParameters as MQTT_ConnectionParameters
from commlib.transports.mqtt import Credentials as MQTT_Credentials
from textx import metamodel_from_file

from smauto.language import build_model


def print_auto(automation):
    print(f"[*] Automation <{automation.name}>, "
          f"Condition: {automation.condition.cond_lambda}")


def run_automation(automation):
    automation.build_condition()
    triggered = False
    print_auto(automation)
    # Evaluate
    while not triggered:
        triggered, msg = automation.evaluate()
        # Check if action is triggered
        if triggered:
            print(f"{Fore.YELLOW}[*] Automation <{automation.name}> "
                  f"Triggered!{Style.RESET_ALL}")
            # If automation triggered run its actions
            automation.trigger()
        else:
            pass
            # print(f"{automation.name}: {triggered}")
        time.sleep(1)


def interpret_model_from_path(model_path: str, max_workers: int = 10):
    model = build_model(model_path)

    # Build entities dictionary in model. Needed for evaluating conditions
    model.entities_dict = {entity.name: entity for entity in model.entities}

    # Evaluate automations, run applicable actions and print results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for automation in model.automations:
            executor.submit(run_automation, (automation))
    print('[*] All automations completed!!')
