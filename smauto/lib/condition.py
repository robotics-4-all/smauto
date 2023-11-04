from textx import textx_isinstance, get_metamodel
import statistics
from smauto.lib.types import List, Dict, Time, Date


# List of primitive types that can be directly printed
PRIMITIVES = (int, float, str, bool)

# Lambdas used to build expression strings based on their corresponding operators
OPERATORS = {
    # String operators
    '~': lambda left, right: f"({left} in {right})",
    '!~': lambda left, right: f"({left} not in {right})",
    'has': lambda left, right: f"({right} in {left})",
    'has not': lambda left, right: f"({right} not in {left})",

    # Shared operators
    '==': lambda left, right: f"({left} == {right})",
    '!=': lambda left, right: f"({left} != {right})",
    'is': lambda left, right: f"({left} == {right})",
    'is not': lambda left, right: f"({left} != {right})",
    'in': lambda left, right: f"({left} in {right})",
    'not in': lambda left, right: f"({left} not in {right})",

    # Numeric operators
    '>': lambda left, right: f"({left} > {right})",
    '>=': lambda left, right: f"({left} >= {right})",
    '<': lambda left, right: f"({left} < {right})",
    '<=': lambda left, right: f"({left} <= {right})",

    # Logical operators
    'AND': lambda left, right: f"({left} and {right})",
    'OR': lambda left, right: f"({left} or {right})",
    'NOT': lambda left, right: f"({left} is not {right})",
    'XOR': lambda left, right: f"({left} ^ {right})",
    'NOR': lambda left, right: f"(not ({left} or {right}))",
    'XNOR': lambda left, right: f"(({left} or {right}) and (not {left} or not {right}))",
    'NAND': lambda left, right: f"(not ({left} and {right}))",

    # Advanced
    'InRange': lambda attr, min, max: f"({attr} > {min} and {attr} < {max})",
}


class Condition(object):
    def __init__(self, parent):
        self.parent = parent
        self.cond_lambda = None
        self.cond_raw = None

    @staticmethod
    def transform_operand(node) -> str:
        # If node is a primitive type return as is (if string, add quotation marks)
        if type(node) in PRIMITIVES:
            if type(node) is str:
                return f"'{node}'"
            else:
                return node
        # If node is a List object just print it out. List has __repr()__ built in
        elif type(node) == List:
            return node
        # If node is a Dict object just print it out. List has __repr()__ built in
        elif type(node) == Dict:
            return node
        elif type(node) == Time:
            return node.to_int()
        # Node is an Attribute, print its full name including Entity
        elif textx_isinstance(
            node,
            get_metamodel(node).namespaces['condition']['AugmentedAttr']
            ):
            return Condition.transform_augmented_attr(node)
        elif textx_isinstance(
            node,
            get_metamodel(node).namespaces['condition']['SimpleTimeAttr']
            ):
                val = f"entities['{node.attribute.parent.name}']." + \
                        f"attributes_dict['{node.attribute.name}'].value.to_int()"
                return val
        else:
            val = f"entities['{node.parent.name}']." + \
                    f"attributes_dict['{node.name}'].value"
            return val

    @staticmethod
    def transform_augmented_attr(aattr) -> str:
        parent = aattr.parent
        val: str = ''
        if aattr.__class__.__name__ == 'SimpleNumericAttr':
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            if parent.__class__.__name__ in ('StdAttr', 'MeanAttr', 'VarAttr',
                                             'MinAttr', 'MaxAttr'):  # Have buffer
                entity_ref.init_attr_buffer(attr_ref.name, parent.size)
                val = f"entities['{entity_ref.name}']." + \
                    f"get_buffer('{attr_ref.name}')"
            else:
                val = f"entities['{entity_ref.name}']." + \
                        f"attributes_dict['{attr_ref.name}'].value"
        elif aattr.__class__.__name__ == 'SimpleBoolAttr':
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = f"entities['{entity_ref.name}']." + \
                    f"attributes_dict['{attr_ref.name}'].value"
        elif aattr.__class__.__name__ == 'SimpleStringAttr':
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = f"entities['{entity_ref.name}']." + \
                    f"attributes_dict['{attr_ref.name}'].value"
        elif aattr.__class__.__name__ == 'SimpleDictAttr':
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = f"entities['{entity_ref.name}']." + \
                    f"attributes_dict['{attr_ref.name}'].value"
        elif aattr.__class__.__name__ == 'SimpleListAttr':
            attr_ref = aattr.attribute
            entity_ref = aattr.attribute.parent
            val = f"entities['{entity_ref.name}']." + \
                    f"attributes_dict['{attr_ref.name}'].value"
        elif aattr.__class__.__name__ in 'StdAttr':
            val = f"std({Condition.transform_augmented_attr(aattr.attribute)})"
        elif aattr.__class__.__name__ == 'MeanAttr':
            val = f"mean({Condition.transform_augmented_attr(aattr.attribute)})"
        elif aattr.__class__.__name__ == 'VarAttr':
            val = f"var({Condition.transform_augmented_attr(aattr.attribute)})"
        elif aattr.__class__.__name__ == 'MaxAttr':
            val = f"max({Condition.transform_augmented_attr(aattr.attribute)})"
        elif aattr.__class__.__name__ == 'MinAttr':
            val = f"min({Condition.transform_augmented_attr(aattr.attribute)})"
        return val

    def build(self):
        self.process_node_condition(self)
        return self.cond_lambda

    # Post-Order traversal of Condition tree, generating the condition for each node
    @staticmethod
    def process_node_condition(cond_node):

        # Get the full metamodel
        metamodel = get_metamodel(cond_node.parent)

        # If we are in a ConditionGroup node, recursively visit the left and right sides
        if textx_isinstance(
            cond_node, metamodel.namespaces['condition']['ConditionGroup']):
            # Visit left node
            Condition.process_node_condition(cond_node.r1)
            # Visit right node
            Condition.process_node_condition(cond_node.r2)
            # Build lambda
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(
                cond_node.r1.cond_lambda, cond_node.r2.cond_lambda)
        else:
            operand1 = Condition.transform_operand(cond_node.operand1)
            operand2 = Condition.transform_operand(cond_node.operand2)
            cond_node.cond_lambda = (OPERATORS[cond_node.operator])(operand1,
                                                                    operand2)

    def evaluate(self):
        # Check if condition has been build using build_expression
        if self.cond_lambda not in (None, ''):
            # Evaluate condition providing the textX model as global context for evaluation
            try:
                entities = self.parent.parent.entities_dict
                # print(entities['system_clock'].attributes_dict['time'].value.to_int())
                if eval(
                    self.cond_lambda,
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
                    return True, f"{self.parent.name}: triggered."
                else:
                    return False, f"{self.parent.name}: not triggered."
            except Exception as e:
                print(e)
                return False, f"{self.parent.name}: not triggered."
        else:
            return False, f"{self.parent.name}: condition not built."


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

    def process_node_condition(self, cond_node):
        operand1 = self.transform_operand(cond_node.attribute)
        cond_lambda = (OPERATORS['InRange'])(operand1,
                                             cond_node.min,
                                             cond_node.max)
        cond_node.cond_lambda = cond_lambda


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
