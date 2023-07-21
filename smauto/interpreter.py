#!/usr/bin/env python3

import traceback
import time
from rich import print, pretty, inspect
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style
from smauto.language import build_model

pretty.install()


def print_auto(automation):
    print(f"[*] Automation <{automation.name}>\n"
          f"    Condition: {automation.condition.cond_lambda}")
    # inspect(automation, methods=False)


def run_automation(automation):
    automation.build_condition()
    print_auto(automation)
    triggered = False
    # Evaluate
    while not triggered:
        try:
            triggered, _ = automation.evaluate()
        except Exception as e:
            print(e)
        # Check if action is triggered
        if triggered:
            print(f"[bold yellow][*] Automation <{automation.name}> "
                  f"Triggered![/bold magenta]")
            # If automation triggered run its actions
            automation.trigger()
        time.sleep(1)


def automation_worker_clb(f):
    e = f.exception()

    if e is None:
        return

    trace = []
    tb = e.__traceback__
    while tb is not None:
        trace.append({
            "filename": tb.tb_frame.f_code.co_filename,
            "name": tb.tb_frame.f_code.co_name,
            "lineno": tb.tb_lineno
        })
        tb = tb.tb_next
    print(str({
        'type': type(e).__name__,
        'message': str(e),
        'trace': trace
    }))


def execute_model_from_path(model_path: str, max_workers: int = 10):
    model = build_model(model_path)

    # Build entities dictionary in model. Needed for evaluating conditions
    model.entities_dict = {entity.name: entity for entity in model.entities}
    entities = [e for e in model.entities]

    for e in entities:
        e.start()

    automations = model.automations
    # Evaluate automations, run applicable actions and print results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        works = []
        for automation in automations:
            work = executor.submit(
                run_automation,
                (automation)
            ).add_done_callback(automation_worker_clb)
            works.append(work)
    print('[bold magenta][*] All automations completed!![/bold magenta]')
