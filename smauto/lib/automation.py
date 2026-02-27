import time
import urllib.request
import urllib.error
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
        elseActions,
        freq,
        enabled,
        continuous,
        checkOnce,
        delay,
        cooldown,
        triggers,
        terminates,
        description="",
    ):
        enabled = True if enabled is None else enabled
        continuous = True if continuous is None else continuous
        checkOnce = False if checkOnce is None else checkOnce
        freq = 1 if freq in (None, 0) else freq
        delay = 0 if not delay else delay
        cooldown = 0 if not cooldown else cooldown
        self.parent = parent
        self.name = name
        self.condition = condition
        self.enabled = enabled
        self.continuous = continuous
        self.checkOnce = checkOnce
        self.freq = freq
        self.actions = actions
        self.elseActions = elseActions if elseActions else []
        self.triggers = triggers if triggers else []
        self.terminates = terminates if terminates else []
        self.status = Automation.IDLE
        self.description = description if description else ""
        self.delay = delay
        self.cooldown = cooldown

    def evaluate_condition(self):
        if self.enabled:
            return self.condition.evaluate()
        else:
            return False, f"{self.name}: Automation disabled."

    def _execute_actions(self, action_list):
        """Build and publish messages for a list of actions, with wait support."""
        messages = {}
        for action in action_list:
            if isinstance(action, HttpAction):
                self._execute_http_action(action)
                continue
            if isinstance(action, LogAction):
                print(f"[bold blue][LOG:{action.level}] {action.message}[/bold blue]")
                continue
            if isinstance(action, WaitAction):
                for entity, message in messages.items():
                    entity.publisher.publish(message)
                messages = {}
                print(f"[bold cyan][*] Waiting {action.duration}s[/bold cyan]")
                time.sleep(action.duration)
                continue
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

    @staticmethod
    def _execute_http_action(action):
        """Execute an HTTP webhook action."""
        headers = {h.key: h.value for h in action.headers}
        data = action.body.encode("utf-8") if action.body else None
        req = urllib.request.Request(
            action.url,
            data=data,
            headers=headers,
            method=action.method,
        )
        try:
            with urllib.request.urlopen(req, timeout=action.timeout) as resp:
                print(
                    f"[bold green][HTTP] {action.method} {action.url} "
                    f"-> {resp.status}[/bold green]"
                )
        except urllib.error.URLError as e:
            print(f"[bold red][HTTP] {action.method} {action.url} FAILED: {e}[/bold red]")

    def trigger_actions(self):
        if not self.continuous:
            self.enabled = False
        self._execute_actions(self.actions)

        for auto in self.triggers:
            auto.enable()

        for auto in self.terminates:
            auto.terminate()

    def trigger_else_actions(self):
        """Execute the else branch actions (no trigger/terminate side-effects)."""
        if self.elseActions:
            self._execute_actions(self.elseActions)

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
        _last_trigger_time = 0
        while True:
            self.status = Automation.RUNNING
            try:
                triggered, msg = self.evaluate_condition()
                if triggered:
                    # Cooldown check: skip if triggered too recently
                    if self.cooldown > 0:
                        elapsed = time.time() - _last_trigger_time
                        if elapsed < self.cooldown:
                            time.sleep(1 / self.freq)
                            continue
                    print(f"[bold yellow][*] Automation <{self.name}> Triggered![/bold yellow]")
                    print(f"[bold blue][*] Condition met: {self.condition.cond_lambda}")
                    if self.delay > 0:
                        print(f"[bold cyan][*] Delaying actions by {self.delay}s[/bold cyan]")
                        time.sleep(self.delay)
                    self.trigger_actions()
                    self.status = Automation.SUCCESS
                    _last_trigger_time = time.time()
                else:
                    self.trigger_else_actions()
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


class WaitAction(Action):
    def __init__(self, parent, duration):
        super().__init__(parent)
        self.duration = duration


class LogAction(Action):
    def __init__(self, parent, message, level):
        super().__init__(parent)
        self.message = message
        self.level = level if level else "INFO"


class ApplySceneAction(Action):
    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name


class HttpAction(Action):
    def __init__(self, parent, method, url, headers, body, timeout):
        super().__init__(parent)
        self.method = method if method else "GET"
        self.url = url
        self.headers = headers if headers else []
        self.body = body if body else ""
        self.timeout = timeout if timeout else 10


class HttpHeader:
    def __init__(self, parent, key, value):
        self.parent = parent
        self.key = key
        self.value = value


class GroupSetAction(Action):
    def __init__(self, parent, group, attr, value):
        super().__init__(parent)
        self.group = group
        self.attr = attr
        self.value = value


class SceneDef:
    def __init__(self, parent, name, actions):
        self.parent = parent
        self.name = name
        self.actions = actions if actions else []


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


class ConstSetAction(SetAction):
    def __init__(self, parent, attribute, value):
        super().__init__(parent, attribute, value)


class ExprSetAction(Action):
    """Action with a computed expression value (e.g., entity.attr <- expr(other.val * 0.8))."""

    def __init__(self, parent, attribute, expr):
        super().__init__(parent)
        self.attribute = attribute
        self.expr = expr
        self._expr_str = None

    @property
    def value(self):
        """For backward compat with codegen that reads action.value."""
        return self._expr_str

    def build_expr(self):
        """Walk the ActionExpr tree and produce a Python expression string."""
        self._expr_str = self._build_node(self.expr)
        return self._expr_str

    @staticmethod
    def _build_node(node):
        cls = node.__class__.__name__
        if cls == "ActionExpr":
            return ExprSetAction._build_op_list(node.op)
        elif cls == "ActionTerm":
            return ExprSetAction._build_op_list(node.op)
        elif cls == "ActionFactor":
            return ExprSetAction._build_node(node.op)
        elif cls == "NumberOperand":
            return str(node.val)
        elif cls == "AttrRefOperand":
            entity_name = node.ref.parent.name
            attr_name = node.ref.name
            return f"entities['{entity_name}'].attributes_dict['{attr_name}']"
        elif isinstance(node, str):
            # Operator string (+, -, *, /)
            return node
        else:
            return str(node)

    @staticmethod
    def _build_op_list(op_list):
        """Build expression from flat [operand, op, operand, op, ...] list."""
        if not isinstance(op_list, list):
            return ExprSetAction._build_node(op_list)
        parts = [ExprSetAction._build_node(item) for item in op_list]
        return "(" + " ".join(parts) + ")"
