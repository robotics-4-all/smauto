#!/usr/bin/env python

import time
import random
from typing import Optional, Dict
from pydantic import BaseModel
from collections import deque
import statistics
from concurrent.futures import ThreadPoolExecutor, wait

from rich import print, console, pretty
from commlib.msg import PubSubMessage
from commlib.utils import Rate
from commlib.node import Node

pretty.install()
console = console.Console()


class Time(BaseModel):
    hour: int = 0
    minute: int = 0
    second: int = 0
    time_str: str = ''

    def to_int(self):
        val = self.second + int(self.minute<<8) + int(self.hour<<16)
        return val


class ClockMsg(PubSubMessage):
    time: Time = Time()


class Attribute:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value


class BedroomLampMsg(PubSubMessage):
        power: bool = False


class MotionDetectorMsg(PubSubMessage):
        detected: bool = False
        posX: int = 0
        posY: int = 0
        mode: str = ''


class SystemClockMsg(PubSubMessage):
        time: Optional[Time] = Time()



class Entity(Node):
    def __init__(self, name, topic, conn_params,
                 attributes, msg_type, attr_buff=[],
                 *args, **kwargs):
        self.name = name
        self.camel_name = self.to_camel_case(name)
        self.topic = topic
        self.conn_params = conn_params
        self.attributes = attributes
        self.msg_type = msg_type
        self.attributes_dict = {key: val for key, val in self.attributes.items()}
        self.attributes_buff = {key: [] for key, _ in self.attributes.items()}
        self.dstate = self.msg_type()
        self._attr_buff = attr_buff

        for attr in self._attr_buff:
            self.init_attr_buffer(attr[0], attr[1])

        super().__init__(
            node_name=self.camel_name,
            connection_params=self.conn_params,
            *args, **kwargs
        )

    def get_buffer(self, attr_name):
        if len(self.attributes_buff[attr_name]) != \
            self.attributes_buff[attr_name].maxlen:
            return [0] * self.attributes_buff[attr_name].maxlen
        else:
            return self.attributes_buff[attr_name]

    def init_attr_buffer(self, attr_name, size):
        self.attributes_buff[attr_name] = deque(maxlen=size)
        # self.attributes_buff[attr_name].extend([0] * size)

    def to_camel_case(self, snake_str):
        return "".join(x.capitalize() for x in snake_str.lower().split("_"))

    def update_state(self, new_state):
        """
        Function for updating Entity state. Meant to be used as a callback function by the Entity's subscriber object
        (commlib-py).
        :param new_state: Dictionary containing the Entity's state
        :return:
        """
        # Update state
        self.dstate = new_state
        print(f'[*] Entity {self.name} state change: {self.dstate} -> {new_state}')
        # Update attributes based on state
        self.update_attributes(new_state)
        self.update_buffers(new_state)

    def update_buffers(self, state_msg):
        """
        Recursive function used by update_state() mainly to updated
            dictionaries/objects and normal Attributes.
        """
        # Update attributes
        for attribute, value in state_msg.model_dump().items():
            if self.attributes_buff[attribute] is not None:
                self.attributes_buff[attribute].append(value)

    def update_attributes(self, state_msg):
        """
        Recursive function used by update_state() mainly to updated
            dictionaries/objects and normal Attributes.
        """
        # Fast hack for pydantic changes
        if hasattr(state_msg, 'time'):
            t = state_msg.time
            self.attributes_dict = state_msg.model_dump()
            self.attributes_dict['time'] = t
        else:
            self.attributes_dict = state_msg.model_dump()

    def start(self):
        # Create and start communications subscriber on Entity's topic
        self.state_sub = self.create_subscriber(
            topic=self.topic,
            msg_type=self.msg_type,
            on_message=self.update_state
        )
        self.state_sub.run()
        self.state_pub = self.create_publisher(
            topic=self.topic,
            msg_type=self.msg_type,
        )
        self.state_pub.run()

    def change_state(self, msg):
        self.state_pub.publish(msg)


class EntitySense(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class EntityAct(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



class AutomationState:
    IDLE = 0
    RUNNING = 1
    EXITED_SUCCESS = 2
    EXITED_FAILURE = 3


class Condition(object):
    def __init__(self, expression):
        self.expression = expression

    def evaluate(self, entities):
        try:
            if eval(
                self.expression,
                {
                    'entities': entities
                },
                {
                    'std': statistics.stdev,
                    'var': statistics.variance,
                    'mean': statistics.mean,
                    'min': min,
                    'max': max,
                }
            ):
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False


class RTMonitor:
    def __init__(self, comm_node, etopic, ltopic):
        self.node = comm_node
        epub = self.node.create_publisher(
            topic=etopic,
            msg_type=StateChangeMsg
        )
        lpub = self.node.create_publisher(
            topic=ltopic,
            msg_type=LogMsg
        )
        self._epub = epub
        self._lpub = lpub
        print(f'[RTMonitor]: events -> {etopic}, logs -> {ltopic}')

    def send_event(self, event):
        print(f'[RTMonitor] Sending StateChange Event: {event}')
        self._epub.publish(event)

    def send_log(self, log_msg):
        print(f'[RTMonitor] Sending Log: {log_msg}')
        self._lpub.publish(log_msg)


class Automation():
    def __init__(self, name, condition, actions, freq, enabled, continuous,
                 checkOnce, after, starts, stops, entities,
                 rtm: RTMonitor = None):
        enabled = True if enabled is None else enabled
        continuous = True if continuous is None else continuous
        checkOnce = False if checkOnce is None else checkOnce
        freq = 1 if freq in (None, 0) else freq
        self.name = name
        self.condition = condition
        self.enabled = enabled
        self.continuous = continuous
        self.checkOnce = checkOnce
        self.freq = freq
        self.actions = actions
        self.after = after
        self.starts = starts
        self.stops = stops
        self.time_between_activations = 5
        self.state = AutomationState.IDLE
        self.entities = entities
        self.autos_map = {}
        self.rtm = rtm

    def set_autos(self, autos_map):
        self.autos_map = autos_map

    def evaluate_condition(self):
        if self.enabled:
            return self.condition.evaluate(self.entities)
        else:
            return False

    def print(self):
        after = f'\n'.join(
            [f"  - {self.autos_map[dep].name}" for dep in self.after])
        starts = f'\n'.join(
            [f"  - {self.autos_map[dep].name}" for dep in self.starts])
        stops = f'\n'.join(
            [f"  - {self.autos_map[dep].name}" for dep in self.stops])
        print(
            f"Automation <{self.name}>\n"
            f"    Condition: {self.condition.expression}\n"
            f"    Frequency: {self.freq} Hz\n"
            f"    Continuoues: {self.continuous}\n"
            f"    CheckOnce: {self.checkOnce}\n"
            f"    Starts:\n"
            f"      {starts}\n"
            f"    Stops:\n"
            f"      {stops}\n"
            f"    After:\n"
            f"      {after}\n"
        )

    def trigger_actions(self):
        messages = {}
        # If continuous is false, disable automation until it is manually re-enabled
        if not self.continuous:
            self.enabled = False
        for action in self.actions:
            value = action.value
            entity = action.entity
            if entity in messages.keys():
                messages[entity].update({action.attribute: value})
            else:
                messages[entity] = entity.dstate
        for entity, message in messages.items():
            entity.change_state(message)

    def enable(self):
        self.enabled = True
        self.log(f"Enabled Automation: {self.name}")

    def disable(self):
        self.enabled = False
        self.log(f"Disabled Automation: {self.name}")

    def state_change(self, new_state: AutomationState, msg: str = ""):
        self.state = new_state
        msg = StateChangeMsg(state=new_state, msg=msg, automation=self.name)
        self.rtm.send_event(msg)

    def log(self, msg: str, level: str = 'INFO'):
        log_msg = LogMsg(msg=msg, level=level)
        self.rtm.send_log(log_msg)
        print(f'[Automation: {self.name}]: {msg}')

    def start(self):
        self.state_change(AutomationState.IDLE)
        self.print()
        self.log(f"Starting Automation: {self.name}")
        while True:
            if len(self.after) == 0:
                self.state_change(AutomationState.RUNNING)
            # Wait for dependend automations to finish
            while self.state == AutomationState.IDLE:
                wait_for = [
                    dep for dep in self.after
                    if self.autos_map[dep].state == AutomationState.RUNNING
                ]
                if len(wait_for) == 0:
                    self.state_change(AutomationState.RUNNING)
                self.log(
                    f'Waiting for dependend automations to finish: {wait_for}'
                )
                time.sleep(1)
            while self.state == AutomationState.RUNNING:
                try:
                    triggered = self.evaluate_condition()
                    if triggered:
                        self.log(f"Automation <{self.name}> Triggered!")
                        self.log(f"Condition met: {self.condition.expression}")
                        # If automation triggered run its actions
                        self.trigger_actions()
                        self.state_change(AutomationState.EXITED_SUCCESS)
                        for auto in self.starts:
                            self.autos_map[auto].enable()
                        for auto in self.stops:
                            self.autos_map[auto].disable()
                    if self.checkOnce:
                        self.disable()
                        self.state_change(AutomationState.EXITED_SUCCESS)
                    time.sleep(1 / self.freq)
                except Exception as e:
                    self.log(f'[ERROR] {str(e)}')
                    return
            # time.sleep(self.time_between_activations)
            self.state_change(AutomationState.IDLE)


class Action:
    def __init__(self, attribute, value, entity):
        self.attribute = attribute
        self.value = value
        self.entity = entity


class StateChangeMsg(PubSubMessage):
    state: int
    automation: str
    msg: str = ""


class LogMsg(PubSubMessage):
    msg: str
    level: str = "INFO"


class Executor(Node):
    def __init__(self, *args, **kwargs):
        self.name = 'SimpleHomeAutomation'
        self.namespace = ''
        self.event_topic = ''
        self.logs_topic = ''
        self._etopic = f'{self.namespace}.{self.event_topic}'
        self._ltopic = f'{self.namespace}.{self.logs_topic}'
        self._init_params()
        super().__init__(
            node_name=self.name,
            debug=True,
            connection_params=self.conn_params
        )
        self.rtm = RTMonitor(self, self._etopic, self._ltopic)
        self.run()

        self.entities = self.create_entities()
        self.entities_map = self.build_entities_map(self.entities)
        self.autos = self.create_automations(self.entities_map)
        self.autos_map = self.build_autos_map(self.autos)
        for auto in self.autos:
            auto.set_autos(self.autos_map)

    def _init_params(self):
        self.conn_params = conn_params

    def build_autos_map(self, autos):
        a_map = {auto.name: auto for auto in autos}
        return a_map

    def build_entities_map(self, entities):
        e_map = {ent.name: ent for ent in entities}
        return e_map

    def create_automations(self, entities):
        autos = []
        autos.append(Automation(
            name='motion_detected_1',
            condition=Condition(
                expression="((entities['motion_detector'].attributes_dict['posX'] == 5) and (entities['motion_detector'].attributes_dict['posY'] == 0))"
            ),
            actions=[
                Action('power', True, entities['bedroom_lamp']),
            ],
            freq=1,
            enabled=True,
            continuous=True,
            checkOnce=False,
            after=[
            ],
            starts=[
            ],
            stops=[
            ],
            entities=entities,
            rtm=self.rtm
        ))
        autos.append(Automation(
            name='motion_detected_2',
            condition=Condition(
                expression="(entities['motion_detector'].attributes_dict['detected'] == False)"
            ),
            actions=[
                Action('power', True, entities['bedroom_lamp']),
            ],
            freq=1,
            enabled=True,
            continuous=True,
            checkOnce=False,
            after=[
            ],
            starts=[
            ],
            stops=[
            ],
            entities=entities,
            rtm=self.rtm
        ))
        return autos

    def create_entity(self, sense, name, topic, conn_params,
                      attributes, msg_type, attr_buff=[]):
        if sense:
            entity = EntitySense(
                name=name,
                topic=topic,
                conn_params=conn_params,
                attributes=attributes,
                msg_type=msg_type,
                attr_buff=attr_buff
            )
        else:
            entity = EntityAct(
                name=name,
                topic=topic,
                conn_params=conn_params,
                attributes=attributes,
                msg_type=msg_type,
                attr_buff=attr_buff
            )
        return entity


    def create_entities(self):
        entities = []
        from commlib.transports.mqtt import ConnectionParameters
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        attrs = {
            'power': bool(),
        }
        entities.append(
            self.create_entity(
                False, 'bedroom_lamp', 'bedroom.lamp',
                conn_params, attrs, msg_type=BedroomLampMsg,
                attr_buff=[]
            )
        )
        from commlib.transports.mqtt import ConnectionParameters
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        attrs = {
            'detected': bool(),
            'posX': int(),
            'posY': int(),
            'mode': str(),
        }
        entities.append(
            self.create_entity(
                True, 'motion_detector', 'bedroom.motion_detector',
                conn_params, attrs, msg_type=MotionDetectorMsg,
                attr_buff=[]
            )
        )
        from commlib.transports.mqtt import ConnectionParameters
        conn_params = ConnectionParameters(
            host='localhost',
            port=1883,
            username='',
            password='',
        )
        attrs = {
            'time': Time(),
        }
        entities.append(
            self.create_entity(
                True, 'system_clock', 'system.clock',
                conn_params, attrs, msg_type=SystemClockMsg,
                attr_buff=[]
            )
        )
        return entities

    def start_entities(self):
        for e in self.entities:
            e.start()

    def start_automations(self, max_workers: int = 60):
        automations = self.autos
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            works = []
            for automation in automations:
                automation.executor = ThreadPoolExecutor()
                work = executor.submit(
                    automation.start
                ).add_done_callback(Executor._worker_clb)
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


if __name__ == '__main__':
    executor = Executor()
    executor.start_entities()
    executor.start_automations()