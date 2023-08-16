#!/usr/bin/env python3

import traceback
from rich import print, pretty
from concurrent.futures import ThreadPoolExecutor, wait
from smauto.language import build_model
from textx import get_children_of_type

pretty.install()



class ModelExecutor:

    @staticmethod
    def get_system_clock_model(model):
        for m in model._tx_model_repository.all_models:
            ent = get_children_of_type('Entity', m)
            for e in ent:
                if e.name == 'system_clock':
                    return e

    @staticmethod
    def execute_automations_from_path(model_path: str, max_workers: int = 10):
        model = build_model(model_path)
        # Build entities dictionary in model. Needed for evaluating conditions
        model.entities_dict = {entity.name: entity for entity in model.entities}
        system_clock = ModelExecutor.get_system_clock_model(model)
        model.entities_dict.update({system_clock.name: system_clock})
        entities = [e for e in model.entities] + [system_clock]
        # Run the Entity instances
        for e in entities:
            e.start()

        automations = model.automations
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            works = []
            for automation in automations:
                automation.executor = ThreadPoolExecutor()
                work = executor.submit(
                    automation.start
                ).add_done_callback(ModelExecutor._worker_clb)
                works.append(work)
            # done, not_done = wait(works)
        print('[bold magenta][*] All automations completed!![/bold magenta]')

    @staticmethod
    def _worker_clb(f):
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

