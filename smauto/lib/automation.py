import time
from rich import print, pretty
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
    def __init__(
        self,
        parent,
        name,
        condition,
        actions,
        freq,
        enabled,
        continuous,
        checkOnce,
        delay,
        dependencies,
        triggers,
        terminates,
        description="",
    ):
        """
        Creates and returns an Automation object (ECA Rule).
        :param name: Automation name. e.g: 'open_lights'
        :param enabled: Whether the automation should be evaluated
            or not. e.g: True->Enabled, False->Disabled
        :param condition: A condition object evaluated to determine if
            the Automation's actions should be executed
        :param actions: List of SetAction objects to be executed upon
            successful condition evaluation
        :param continuous: Boolean variable indicating if the Automation
            should remain enabled after actions are run
        :param dependencies: List of Automations that must complete
            before this one starts
        :param triggers: List of Automations to enable after this
            one completes
        :param terminates: List of Automations to disable after this
            one completes
        """
        enabled = True if enabled is None else enabled
        continuous = True if continuous is None else continuous
        checkOnce = False if checkOnce is None else checkOnce
        freq = 1 if freq in (None, 0) else freq
        delay = 0 if not delay else delay
        self.parent = parent
        self.name = name
        self.condition = condition
        self.enabled = enabled
        self.continuous = continuous
        self.checkOnce = checkOnce
        self.freq = freq
        self.actions = actions
        self.dependencies = dependencies if dependencies else []
        self.triggers = triggers if triggers else []
        self.terminates = terminates if terminates else []
        self.time_between_activations = 5
        self.state = AutomationState.IDLE
        self.description = description if description else ""
        self.delay = delay

    # Evaluate the Automation's conditions and run the actions
    def evaluate_condition(self):
        if self.enabled:
            return self.condition.evaluate()
        else:
            return False, f"{self.name}: Automation disabled."

    # Run Automation's actions
    def trigger_actions(self):
        """
        Runs the Automation's actions, then triggers/terminates
        dependent automations.
        :return:
        """
        # If continuous is false, disable automation until it is manually re-enabled
        if not self.continuous:
            self.enabled = False
        # Dictionary that maps Entities to the data that should be sent to them
        messages = {}
        # Iterate over actions to form messages for each Entity
        for action in self.actions:
            # All actions are SetActions (attribute assignments)
            # If value is List or Dict, cast them to python lists and dicts
            value = action.value
            if type(value) is Dict:
                value = value.to_dict()
            elif type(value) is List:
                value = value.print_item(value)
            # If entity of action already in messages,
            # update the message. Else insert it.
            entity = action.attribute.parent
            attr_name = action.attribute.name
            if entity in messages:
                messages[entity].update({attr_name: value})
            else:
                messages[entity] = {attr_name: value}

        # Iterate over Entities and their corresponding messages
        for entity, message in messages.items():
            # Send message via Entity's publisher
            entity.publisher.publish(message)

        # Trigger dependent automations (replaces StartAction)
        for auto in self.triggers:
            auto.enable()

        # Terminate dependent automations (replaces StopAction)
        for auto in self.terminates:
            auto.disable()

    def build_condition(self):
        """Builds Automation Condition into Python expression string
        so that it can later be evaluated using eval()
        """
        self.condition.build()

    def print(self):
        deps = "\n".join([f"      - {dep.name}" for dep in self.dependencies])
        trigs = "\n".join([f"      - {t.name}" for t in self.triggers])
        terms = "\n".join([f"      - {t.name}" for t in self.terminates])
        print(
            f"[*] Automation <{self.name}>\n"
            f"    Condition: {self.condition.cond_lambda}\n"
            f"    Frequency: {self.freq} Hz\n"
            f"    Continuous: {self.continuous}\n"
            f"    CheckOnce: {self.checkOnce}\n"
            f"    Dependencies:\n"
            f"      {deps}\n"
            f"    Triggers:\n"
            f"      {trigs}\n"
            f"    Terminates:\n"
            f"      {terms}\n"
        )

    def start(self):
        self.state = AutomationState.IDLE
        self.build_condition()
        self.print()
        print(f"[bold yellow][*] Executing Automation: {self.name}[/bold yellow]")
        while True:
            if len(self.dependencies) == 0:
                self.state = AutomationState.RUNNING
            # Wait for dependent automations to finish
            while self.state == AutomationState.IDLE:
                wait_for = [
                    dep.name
                    for dep in self.dependencies
                    if dep.state == AutomationState.RUNNING
                ]
                if len(wait_for) == 0:
                    self.state = AutomationState.RUNNING
                print(
                    f"[bold magenta][{self.name}] Waiting for dependend "
                    f"automations to finish:[/bold magenta] {wait_for}"
                )
                time.sleep(1)
            while self.state == AutomationState.RUNNING:
                try:
                    triggered, msg = self.evaluate_condition()
                    if triggered:
                        print(
                            f"[bold yellow][*] Automation <{self.name}> "
                            f"Triggered![/bold yellow]"
                        )
                        print(
                            f"[bold blue][*] Condition met: "
                            f"{self.condition.cond_lambda}"
                        )
                        # If automation triggered run its actions
                        self.trigger_actions()
                        self.state = AutomationState.EXITED_SUCCESS
                    if self.checkOnce:
                        self.disable()
                        self.state = AutomationState.EXITED_SUCCESS
                    time.sleep(1 / self.freq)
                except Exception as e:
                    print(f"[ERROR] {e}")
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
    def __init__(self, parent):
        self.parent = parent


class SetAction(Action):
    def __init__(self, parent, attribute, value):
        super(SetAction, self).__init__(parent)
        self.attribute = attribute
        self.value = value


class IntSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(IntSetAction, self).__init__(parent, attribute, value)


class FloatSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(FloatSetAction, self).__init__(parent, attribute, value)


class StringSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(StringSetAction, self).__init__(parent, attribute, value)


class BoolSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(BoolSetAction, self).__init__(parent, attribute, value)


class ListSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(ListSetAction, self).__init__(parent, attribute, value)


class DictSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super(DictSetAction, self).__init__(parent, attribute, value)
