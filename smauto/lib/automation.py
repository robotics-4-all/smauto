import time
from rich import print, pretty
from smauto.lib.types import List, Dict

pretty.install()


# Returns printed version of operand if operand is a primitive.
# Else if attribute returns code pointing to the Attribute.
class Automation(object):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    FINISHED = "FINISHED"
    TERMINATED = "TERMINATED"

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
        triggers,
        terminates,
        description="",
    ):
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
        self.triggers = triggers if triggers else []
        self.terminates = terminates if terminates else []
        self.status = Automation.IDLE
        self.description = description if description else ""
        self.delay = delay

    def evaluate_condition(self):
        if self.enabled:
            return self.condition.evaluate()
        else:
            return False, f"{self.name}: Automation disabled."

    def trigger_actions(self):
        if not self.continuous:
            self.enabled = False
        messages = {}
        for action in self.actions:
            value = action.value
            if type(value) is Dict:
                value = value.to_dict()
            elif type(value) is List:
                value = value.print_item(value)
            entity = action.attribute.parent
            attr_name = action.attribute.name
            if entity in messages:
                messages[entity].update({attr_name: value})
            else:
                messages[entity] = {attr_name: value}

        for entity, message in messages.items():
            entity.publisher.publish(message)

        for auto in self.triggers:
            auto.enable()

        for auto in self.terminates:
            auto.terminate()

    def build_condition(self):
        self.condition.build()

    def print_info(self):
        trigs = "\n".join([f"      - {t.name}" for t in self.triggers])
        terms = "\n".join([f"      - {t.name}" for t in self.terminates])
        print(
            f"[*] Automation <{self.name}>\n"
            f"    Condition: {self.condition.cond_lambda}\n"
            f"    Frequency: {self.freq} Hz\n"
            f"    Continuous: {self.continuous}\n"
            f"    CheckOnce: {self.checkOnce}\n"
            f"    Status: {self.status}\n"
            f"    Triggers:\n"
            f"      {trigs}\n"
            f"    Terminates:\n"
            f"      {terms}\n"
        )

    def start(self):
        self.status = Automation.IDLE
        self.build_condition()
        self.print_info()
        print(f"[bold yellow][*] Executing Automation: {self.name}[/bold yellow]")
        while True:
            self.status = Automation.RUNNING
            try:
                triggered, msg = self.evaluate_condition()
                if triggered:
                    print(f"[bold yellow][*] Automation <{self.name}> Triggered![/bold yellow]")
                    print(f"[bold blue][*] Condition met: {self.condition.cond_lambda}")
                    if self.delay > 0:
                        print(f"[bold cyan][*] Delaying actions by {self.delay}s[/bold cyan]")
                        time.sleep(self.delay)
                    self.trigger_actions()
                    self.status = Automation.SUCCESS
                if self.checkOnce:
                    self.disable()
                    self.status = Automation.FINISHED
                time.sleep(1 / self.freq)
            except Exception as e:
                print(f"[ERROR] {e}")
                self.status = Automation.FAILED
                return
            if self.status in (Automation.SUCCESS, Automation.FINISHED):
                self.status = Automation.IDLE

    def enable(self):
        self.enabled = True
        print(f"[bold yellow][*] Enabled Automation: {self.name}[/bold yellow]")

    def disable(self):
        self.enabled = False
        print(f"[bold yellow][*] Disabled Automation: {self.name}[/bold yellow]")

    def terminate(self):
        self.enabled = False
        self.status = Automation.TERMINATED
        print(f"[bold yellow][*] Terminated Automation: {self.name}[/bold yellow]")


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
