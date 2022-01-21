from textx import textx_isinstance, get_metamodel

# List of primitive types that can be directly printed
primitives = (int, float, str, bool)

# Lambdas used to build expression strings based on their corresponding operators
operators = {
    # String operators
    '~': lambda left, right: f"({left} in {right})",
    '!~': lambda left, right: f"({left} not in {right})",

    # Shared operators
    '==': lambda left, right: f"({left} == {right})",
    '!=': lambda left, right: f"({left} != {right})",

    # Numeric operators
    '>': lambda left, right: f"({left} > {right})",
    '<': lambda left, right: f"({left} < {right})",

    # Boolean operators
    'AND': lambda left, right: f"({left} and {right})",
    'OR': lambda left, right: f"({left} or {right})",
    'NOT': lambda left, right: f"({left} is not {right})",
    'XOR': lambda left, right: f"({left} ^ {right})",
    'NOR': lambda left, right: f"(not ({left} or {right}))",
    'XNOR': lambda left, right: f"(({left} or {right}) and (not {left} or not {right}))",
    'NAND': lambda left, right: f"(not ({left} and {right}))"
}


# Returns printed version of operand if operand is a primitive.
# Else if attribute returns code pointing to the Attribute.
def print_operand(node):
    # If node is a primitive type return as is (if string, add quotation marks)
    if type(node) in primitives:
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
    # Node is an Attribute, print its full name including Entity
    else:
        return f"model.entities_dict['{node.parent.name}'].attributes_dict['{node.name}'].value"


# A class representing an Automation
class Automation:
    """
    The Automation class represents an automation that evaluates a condition to execute an action.
    ...

    Attributes
    ----------
        name: str
            Automation name. e.g: 'open_lights'
        enabled: bool
            Whether the automation should be evaluated or not. e.g: True->Enabled, False->Disabled
        condition: object
            A condition type object evaluated to determine if the Automation's actions should be executed
        actions: list
            A list of Action objects to be executed upon successful condition evaluation
        continuous: bool
            Indicates if the Automation should remain enabled after actions are run. e.g: True->Remain Enabled.
    Methods
    -------
        evaluate(self): Evaluates the Automation's conditions and runs the actions. Meant to be run by the
            update_state() function in the Entities listed in condition_entities upon them updating their states.
    """

    def __init__(self, parent, name, condition, actions, enabled, continuous):
        """
        Creates and returns an Automation object
        :param name: Automation name. e.g: 'open_lights'
        :param enabled: Whether the automation should be evaluated or not. e.g: True->Enabled, False->Disabled
        :param condition: A condition object evaluated to determine if the Automation's actions should be executed
        :param actions: List of Action objects to be executed upon successful condition evaluation
        :param continuous: Boolean variable indicating if the Automation should remain enabled after actions are run
        """
        # TextX parent attribute. Required to use Automation as a custom class during metamodel instantiation
        self.parent = parent
        # Automation name
        self.name = name
        # Automation Condition
        self.condition = condition
        # Boolean variable indicating if the Automation is enabled and should be evaluated
        self.enabled = enabled
        # Boolean variable indicating if the Automation should remain enabled after execution and not require manual
        # reactivation
        self.continuous = continuous
        # Action function
        self.actions = actions

    # Evaluate the Automation's conditions and run the actions
    def evaluate(self):
        """
            Evaluates the Automation's conditions if enabled is True and returns the result and the activation message.
        :return: (Boolean showing the evaluation's success, A string message regarding evaluation's status)
        """
        # Check if condition has been build using build_expression
        if self.enabled:
            if hasattr(self.condition, 'cond_lambda'):
                # Evaluate condition providing the textX model as global context for evaluation
                if eval(self.condition.cond_lambda, {'model': self.parent}):
                    return True, f"{self.name}: triggered."
                else:
                    return False, f"{self.name}: not triggered."
            else:
                return False, f"{self.name}: condition not built. Please build using build_expression."
        else:
            return False, f"{self.name}: Automation disabled."

    # Run Automation's actions
    def trigger(self):
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

    # Post-Order traversal of Condition tree, generating the condition for each node
    def process_node_condition(self, cond_node):

        # Get the full metamodel
        metamodel = get_metamodel(self.parent)

        # If we are in a ConditionGroup node, recursively visit the left and right sides
        if textx_isinstance(cond_node, metamodel.namespaces['automation']['ConditionGroup']):

            # Visit left node
            self.process_node_condition(cond_node.r1)
            # Visit right node
            self.process_node_condition(cond_node.r2)
            # Build lambda
            cond_node.cond_lambda = (operators[cond_node.operator])(cond_node.r1.cond_lambda, cond_node.r2.cond_lambda)

        # If we are in a primitive condition node, form conditions using operands
        else:
            operand1 = print_operand(cond_node.operand1)
            operand2 = print_operand(cond_node.operand2)
            cond_node.cond_lambda = (operators[cond_node.operator])(operand1, operand2)

    # Builds Automation Condition into Python expression string so that it can later be evaluated using eval()
    def build_condition(self):
        self.process_node_condition(self.condition)


# List class for List type
class List:
    """
        Attributes
    ----------
        items: list
            Python list of items included in the List. Can be primitives or other List items
        parent: obj
            Reference to the parent element in the parsed textX hierarchy

    Methods
    -------
        __repr__():
            Used to print out a string of the List with subList items also being printed out as strings
        print_item():
            Static method used by __repr__() and called recursively to return a python list of sub-items.
    """

    def __init__(self, parent, items):
        self.parent = parent
        self.items = items

    # String representation of List class that opens up subLists as strings
    def __repr__(self):
        return str(self.print_item(self))

    # List representation to bring out subLists instead of List items
    @staticmethod
    def print_item(item):
        """
        Static method used by __repr__() and called recursively to return a python list of sub-items.
        :param item: List or primitive item to open up
        :return: Python list of primitives or python lists (previously sub-List items)
        """
        # If item is a list return list of items printed out including sublists
        if type(item) == List:
            return [item.print_item(x) for x in item.items]
        # else if just a primitive, return it as is
        else:
            return item


class Dict:

    def __init__(self, parent, items):
        self.parent = parent
        self.items = items

    # String representation of Dict class that prints subitems as strings
    def __repr__(self):
        final_str = "{"
        for index, item in enumerate(self.items):
            final_str = final_str + f"'{item.name}'" + ":" + str(self.print_item(item.value))
            if index != (len(self.items) - 1):
                final_str = final_str + ','
        final_str = final_str + '}'
        return final_str

    # List representation to bring out subLists instead of List items
    # TODO: This is a copy of the same method in the List class. Maybe unify them? Might change though with nested
    # Dicts support.
    @staticmethod
    def print_item(item):
        """
        Static method used by __repr__() and called recursively to return a python list of sub-items.
        :param item: List or primitive item to open up
        :return: Python list of primitives or python lists (previously sub-List items)
        """
        # If item is a list return list of items printed out including sublists
        if type(item) == List:
            return [item.print_item(x) for x in item.items]
        # else if just a primitive, return it as is
        else:
            return item

    def to_dict(self):
        return {item.name: item.value for item in self.items}


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
