from textx import textx_isinstance, get_metamodel
import statistics
from smauto.lib.types import List, Dict, Time


# List of primitive types that can be directly printed
PRIMITIVES = (int, float, str, bool)

# Lambdas used to build expression strings based on their corresponding operators
OPERATORS = {
    # String operators
    "~": lambda left, right: f"({left} in {right})",
    "!~": lambda left, right: f"({left} not in {right})",
    "has": lambda left, right: f"({right} in {left})",
    "has not": lambda left, right: f"({right} not in {left})",
    # Shared operators
    "==": lambda left, right: f"({left} == {right})",
    "!=": lambda left, right: f"({left} != {right})",
    "is": lambda left, right: f"({left} == {right})",
    "is not": lambda left, right: f"({left} != {right})",
    "in": lambda left, right: f"({left} in {right})",
    "not in": lambda left, right: f"({left} not in {right})",
    # Numeric operators
    ">": lambda left, right: f"({left} > {right})",
    ">=": lambda left, right: f"({left} >= {right})",
    "<": lambda left, right: f"({left} < {right})",
    "<=": lambda left, right: f"({left} <= {right})",
    # Logical operators
    "AND": lambda left, right: f"({left} and {right})",
    "OR": lambda left, right: f"({left} or {right})",
    "NOT": lambda left, right: f"({left} is not {right})",
    "XOR": lambda left, right: f"({left} ^ {right})",
    "NOR": lambda left, right: f"(not ({left} or {right}))",
    "XNOR": lambda left, right: f"(({left} and {right}) or (not {left} and not {right}))",
    "NAND": lambda left, right: f"(not ({left} and {right}))",
    # Advanced
    "InRange": lambda attr, min, max: f"({attr} > {min} and {attr} < {max})",
}


class Condition(object):
    def __init__(self, parent):
        self.parent = parent
        self.cond_lambda = None
        self.cond_raw = None
        self._compiled = None

    @staticmethod
    def transform_operand(node) -> str:
        # If node is a primitive type return as is (if string, add quotation marks)
        if type(node) in PRIMITIVES:
            if type(node) is str:
                return f"'{node}'"
            else:
                return node
        # If node is a List object just print it out. List has __repr()__ built in
        elif type(node) is List:
            return node
        # If node is a Dict object just print it out. List has __repr()__ built in
        elif type(node) is Dict:
            return node
        elif type(node) is Time:
            return node.to_int()
        # Node is an Attribute, print its full name including Entity
        elif textx_isinstance(node, get_metamodel(node).namespaces["condition"]["AugmentedAttr"]):
            return Condition.transform_augmented_attr(node)
        elif textx_isinstance(node, get_metamodel(node).namespaces["condition"]["SimpleTimeAttr"]):
            val = (
                f"entities['{node.attribute.parent.name}']."
                + f"attributes_dict['{node.attribute.name}'].value.to_int()"
            )
            return val
        else:
            val = f"entities['{node.parent.name}']." + f"attributes_dict['{node.name}'].value"
            return val

    _BUFFERED_PARENTS = frozenset(("StdAttr", "MeanAttr", "VarAttr", "MinAttr", "MaxAttr"))
    _SIMPLE_ATTR_TYPES = frozenset(
        (
            "SimpleBoolAttr",
            "SimpleStringAttr",
            "SimpleDictAttr",
            "SimpleListAttr",
        )
    )
    _AGG_FUNCS = {
        "StdAttr": "std",
        "MeanAttr": "mean",
        "VarAttr": "var",
        "MaxAttr": "max",
        "MinAttr": "min",
    }

    @staticmethod
    def _attr_value_expr(entity_name, attr_name):
        return f"entities['{entity_name}'].attributes_dict['{attr_name}'].value"

    @staticmethod
    def _buffer_expr(entity_name, attr_name):
        return f"entities['{entity_name}'].get_buffer('{attr_name}')"

    @staticmethod
    def transform_augmented_attr(aattr) -> str:
        cls_name = aattr.__class__.__name__
        parent = aattr.parent

        if cls_name == "SimpleNumericAttr":
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            if parent.__class__.__name__ in Condition._BUFFERED_PARENTS:
                entity_ref.init_attr_buffer(attr_ref.name, parent.size)
                entity_ref.attr_buffs.append((attr_ref.name, parent.size))
                return Condition._buffer_expr(entity_ref.name, attr_ref.name)
            return Condition._attr_value_expr(entity_ref.name, attr_ref.name)

        if cls_name in Condition._SIMPLE_ATTR_TYPES:
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            return Condition._attr_value_expr(entity_ref.name, attr_ref.name)

        if cls_name in Condition._AGG_FUNCS:
            func = Condition._AGG_FUNCS[cls_name]
            return f"{func}({Condition.transform_augmented_attr(aattr.attribute)})"

        return ""

    def build(self):
        Condition.process_node_condition(self)
        if self.cond_lambda:
            self._compiled = compile(self.cond_lambda, "<smauto-condition>", "eval")
        return self.cond_lambda

    # Post-Order traversal of Condition tree, generating the condition for each node
    @staticmethod
    def process_node_condition(cond_node):
        # Get the full metamodel
        metamodel = get_metamodel(cond_node.parent)

        # If we are in a ConditionGroup node, recursively visit the left and right sides
        if textx_isinstance(cond_node, metamodel.namespaces["condition"]["ConditionGroup"]):
            # Visit left node
            Condition.process_node_condition(cond_node.r1)
            # Visit right node
            Condition.process_node_condition(cond_node.r2)
            # Build lambda
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(
                cond_node.r1.cond_lambda, cond_node.r2.cond_lambda
            )
        elif textx_isinstance(cond_node, metamodel.namespaces["condition"]["InRangeCondition"]):
            cond_node.process_node_condition()
        elif textx_isinstance(cond_node, metamodel.namespaces["condition"]["TimeRangeCondition"]):
            cond_node.process_node_condition()
        elif textx_isinstance(
            cond_node, metamodel.namespaces["condition"]["AutomationStatusCondition"]
        ):
            auto_name = cond_node.operand1.automation
            status_val = cond_node.operand2
            op = OPERATORS[cond_node.operator]
            cond_node.cond_lambda = op(f"automations['{auto_name}'].status", f"'{status_val}'")
        else:
            operand1 = Condition.transform_operand(cond_node.operand1)
            operand2 = Condition.transform_operand(cond_node.operand2)
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(operand1, operand2)

    # Restricted builtins whitelist — no __import__, exec, open, etc.
    _SAFE_BUILTINS = {
        "True": True,
        "False": False,
        "None": None,
        "abs": abs,
        "round": round,
        "int": int,
        "float": float,
        "bool": bool,
        "len": len,
    }

    def evaluate(self):
        code = self._compiled if self._compiled is not None else self.cond_lambda
        if code is None or (isinstance(code, str) and code == ""):
            return False, f"{self.parent.name}: condition not built."
        try:
            model = self.parent.parent
            entities = model.entities_dict
            automations = getattr(model, "automations_dict", {})
            result = eval(
                code,
                {
                    "__builtins__": Condition._SAFE_BUILTINS,
                    "entities": entities,
                    "automations": automations,
                },
                {
                    "std": statistics.stdev,
                    "var": statistics.variance,
                    "mean": statistics.mean,
                    "min": min,
                    "max": max,
                },
            )
            if result:
                return True, f"{self.parent.name}: triggered."
            else:
                return False, f"{self.parent.name}: not triggered."
        except Exception as e:
            print(e)
            return False, f"{self.parent.name}: not triggered."


class ConditionGroup(Condition):
    def __init__(self, parent, r1, operator, r2):
        self.r1 = r1
        self.r2 = r2
        self.operator = operator
        super().__init__(parent)


class PrimitiveCondition(Condition):
    def __init__(self, parent):
        super().__init__(parent)


class AdvancedCondition(Condition):
    def __init__(self, parent):
        super().__init__(parent)


class InRangeCondition(AdvancedCondition):
    def __init__(self, parent, attribute, min, max):
        self.attribute = attribute
        self.min = min
        self.max = max
        super().__init__(parent)

    def process_node_condition(self):
        operand1 = self.transform_operand(self.attribute)
        cond_lambda = (OPERATORS["InRange"])(operand1, self.min, self.max)
        self.cond_lambda = cond_lambda


class TimeRangeCondition(AdvancedCondition):
    """Time range condition with midnight wrap support.

    If min <= max (e.g., [08:00, 22:00]): attr >= min AND attr <= max
    If min > max  (e.g., [22:00, 06:00]): attr >= min OR  attr <= max  (wraps midnight)
    """

    def __init__(self, parent, attribute, min, max):
        self.attribute = attribute
        self.min = min
        self.max = max
        super().__init__(parent)

    def process_node_condition(self):
        operand1 = self.transform_operand(self.attribute)
        min_int = self.min.to_int()
        max_int = self.max.to_int()
        if min_int <= max_int:
            # Normal range: attr >= min AND attr <= max
            self.cond_lambda = f"({operand1} >= {min_int} and {operand1} <= {max_int})"
        else:
            # Midnight wrap: attr >= min OR attr <= max
            self.cond_lambda = f"({operand1} >= {min_int} or {operand1} <= {max_int})"


class NumericCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class BoolCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class StringCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class ListCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class DictCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class TimeCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operand2 = operand2
        self.operator = operator
        super().__init__(parent)


class AutomationStatusRef:
    def __init__(self, parent, automation):
        self.parent = parent
        self.automation = automation


class AutomationStatusCondition(PrimitiveCondition):
    def __init__(self, parent, operand1, operator, operand2):
        self.operand1 = operand1
        self.operator = operator
        self.operand2 = operand2
        super().__init__(parent)
