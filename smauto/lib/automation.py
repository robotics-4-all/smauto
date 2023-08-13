from textx import textx_isinstance, get_metamodel
import time
from rich import print, pretty
from concurrent.futures import ThreadPoolExecutor
from smauto.lib.types import List, Dict

pretty.install()


# Returns printed version of operand if operand is a primitive.
# Else if attribute returns code pointing to the Attribute.
class AutomationState:
    IDLE = 0
    RUNNING = 1
    EXITED_SUCCESS = 2
    EXITED_FAILURE = 3


# A class representing an Automation
class Automation(object):

    def __init__(self, parent, name, condition, actions,
                 enabled, continuous, checkOnce, after, starts, stops):
        """
        Creates and returns an Automation object
        :param name: Automation name. e.g: 'open_lights'
        :param enabled: Whether the automation should be evaluated
            or not. e.g: True->Enabled, False->Disabled
        :param condition: A condition object evaluated to determine if
            the Automation's actions should be executed
        :param actions: List of Action objects to be executed upon successful
            condition evaluation
        :param continuous: Boolean variable indicating if the Automation
            should remain enabled after actions are run
        """
        enabled = True if enabled is None else enabled
        continuous = True if continuous is None else continuous
        checkOnce = False if checkOnce is None else checkOnce
        self.parent = parent
        # Automation name
        self.name = name
        # Automation Condition
        self.condition = condition
        # Boolean variable indicating if the Automation is enabled and should be evaluated
        self.enabled = enabled
        self.continuous = continuous
        self.checkOnce = checkOnce
        # Action function
        self.actions = actions
        self.after = after
        self.starts = starts
        self.stops = stops
        self.time_between_activations = 5
        self.state = AutomationState.IDLE

    # Evaluate the Automation's conditions and run the actions
    def evaluate_condition(self):
        """
            Evaluates the Automation's conditions if enabled is
            True and returns the result and the activation message.

        :return: (Boolean showing the evaluation's success,
            A string message regarding evaluation's status)
        """
        # Check if condition has been build using build_expression
        if self.enabled:
            return self.condition.evaluate()
        else:
            return False, f"{self.name}: Automation disabled."

    # Run Automation's actions
    def trigger_actions(self):
        """
        Runs the Automation's actions.
        :return:
        """
        # If continuous is false, disable automation until it is manually re-enabled
        if not self.continuous:
            self.enabled = False
        # Dictionary that maps Entities to the data that should be sent to them
        messages = {}
        # Iterate over actions to form messages for each Entity
        for action in self.actions:
            # If value is List or Dict, cast them to python lists and dicts
            value = action.value
            if type(value) is Dict:
                value = value.to_dict()
            elif type(value) is List:
                value = value.print_item(value)
            # If entity of action already in messages, update the message. Else insert it.
            if action.attribute.parent in messages.keys():
                messages[action.attribute.parent].update({action.attribute.name: value})
            else:
                messages[action.attribute.parent] = {action.attribute.name: value}

        # Iterate over Entities and their corresponding messages
        for entity, message in messages.items():
            # Send message via Entity's publisher
            entity.publisher.publish(message)

    def build_condition(self):
        """Builds Automation Condition into Python expression string
            so that it can later be evaluated using eval()
        """
        self.condition.build()

    def print(self):
        after = f'\n'.join(
            [f"      - {dep.name}" for dep in self.after])
        print(
            f"[*] Automation <{self.name}>\n"
            f"    Condition: {self.condition.cond_lambda}\n"
            f"    After:\n"
            f"      {after}"
        )

    def start(self):
        self.state = AutomationState.IDLE
        self.build_condition()
        self.print()
        print(f"[bold yellow][*] Executing Automation: {self.name}[/bold yellow]")
        while True:
            if len(self.after) == 0:
                self.state = AutomationState.RUNNING
            # Wait for dependend automations to finish
            while self.state == AutomationState.IDLE:
                wait_for = [
                    dep.name for dep in self.after
                    if dep.state == AutomationState.RUNNING
                ]
                if len(wait_for) == 0:
                    self.state = AutomationState.RUNNING
                print(
                    f'[bold magenta]\[{self.name}] Waiting for dependend '
                    f'automations to finish:[/bold magenta] {wait_for}'
                )
                time.sleep(1)
            while self.state == AutomationState.RUNNING:
                try:
                    triggered, msg = self.evaluate_condition()
                    if triggered:
                        print(f"[bold yellow][*] Automation <{self.name}> "
                            f"Triggered![/bold yellow]"
                        )
                        print(f"[bold blue][*] Condition met: "
                            f"{self.condition.cond_lambda}"
                        )
                        # If automation triggered run its actions
                        self.trigger_actions()
                        self.state = AutomationState.EXITED_SUCCESS
                        for automation in self.starts:
                            automation.enable()
                        for automation in self.stops:
                            automation.disable()
                    if self.checkOnce:
                        self.disable()
                        self.state = AutomationState.EXITED_SUCCESS
                    time.sleep(1)
                except Exception as e:
                    print(f'[ERROR] {e}')
                    return
            # time.sleep(self.time_between_activations)
            self.state = AutomationState.IDLE

    def enable(self):
        self.enabled = True
        print(f"[bold yellow][*] Enabled Automation: {self.name}[/bold yellow]")

    def disable(self):
        self.enabled = False
        print(f"[bold yellow][*] Disabled Automation: {self.name}[/bold yellow]")


class Action:
    def __init__(self, parent, attribute, value):
        self.parent = parent
        self.attribute = attribute
        self.value = value


class IntAction(Action):
    def __init__(self, parent, attribute, value):
        super(IntAction, self).__init__(parent, attribute, value)


class FloatAction(Action):
    def __init__(self, parent, attribute, value):
        super(FloatAction, self).__init__(parent, attribute, value)


class StringAction(Action):
    def __init__(self, parent, attribute, value):
        super(StringAction, self).__init__(parent, attribute, value)


class BoolAction(Action):
    def __init__(self, parent, attribute, value):
        super(BoolAction, self).__init__(parent, attribute, value)
