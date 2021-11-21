# NOTE: If you want to run visualize directly, since it is considered part of the lib package, you can execute
# "python -m lib.visualize". The -m tells Python to load it as a module, not as the top-level script.
# Example call: python -m lib.visualize visualize lang\smauto.tx config\example.smauto gpsAutomation --out gpsAutomation.pu

import click

from textx import textx_isinstance, metamodel_from_file

from .automation import Automation, List, Dict, Action, IntAction, FloatAction, StringAction, BoolAction
from .broker import Broker, MQTTBroker, AMQPBroker, RedisBroker, BrokerAuthPlain
from .entity import Attribute, IntAttribute, FloatAttribute, StringAttribute, BoolAttribute, ListAttribute, \
    DictAttribute

# List of primitive types that can be directly printed
primitives = (int, float, str, bool)
# Custom classes with a __repr__ function so that returning them will print them out. E.g: List class -> python list
custom_classes = (Dict, List)


def print_operand(node):
    """
    Returns how a node from the Automation Condition abstract syntax tree should be printed during the construction of
    the condition's python expression. If it's a primitive, a dictionary or a list, it is simply printed out as a
    literal. If it is an Entity Attribute, it is printed out as "entity_name.attribute_name".
    :param node: A node from the Automation Condition abstract syntax tree.
    :return: The node printed out the correct way for building an Automation's Condition python expression.
    """
    if type(node) in primitives or type(node) in custom_classes:
        return node
    else:
        return node.parent.name + '.' + node.name


# Pre-Order traversal of Condition tree
def visit_node(node, depth, metamodel, file_writer):
    """
    Function called recursively to visit the Automation's Condition abstract syntax tree using pre-order traversal
    to create a PlantUML MindMap of the Automation's Condition.
    :param node: Node in the Abstract Syntax Tree
    :param depth: Current tree level depth
    :param metamodel: The metamodel used to parse the model and it's Automations
    :param file_writer: File writer used to write to the PlantUML MindMap
    :return:
    """
    # Increase depth
    depth += 1

    # Print node operator
    file_writer.write(f"{'-' * depth} {node.operator}\n")

    # If we are in a ConditionGroup node, recursively visit the left and right sides
    # TODO: Probably passing around metamodel as an argument just for accessing the ConditionGroup class is not best
    if textx_isinstance(node, metamodel.namespaces['automation']['ConditionGroup']):

        # Visit left node
        visit_node(node.r1, depth, metamodel, file_writer)
        # Visit right node
        visit_node(node.r2, depth, metamodel, file_writer)

    # If we are in a primitive condition node, print it out
    else:
        operand1 = print_operand(node.operand1)
        operand2 = print_operand(node.operand2)
        file_writer.write(f"{'-' * (depth + 1)} {operand1}\n")
        file_writer.write(f"{'-' * (depth + 1)} {operand2}\n")


# Visualizes Automation Conditions and Actions using PlantUML
def visualize_automation(metamodel, automation, out_dir=""):
    """
    Creates a PlantUML MindMap visualization of the desired Automation.
    :param metamodel: Metamodel used to parse the Automation
    :param automation: The Automation to be visualized
    :param out_dir: File directory for saving the Automation visualization. e.g: 'visualization/automation.pu'
        (optional)
    :return:
    """
    # Initial MindMap depth
    depth = 1

    # Set default output file directory
    if out_dir == "":
        out_dir = f"automation_{automation.name}.pu"

    # Open output file and write
    with open(out_dir, 'w') as f:
        # Write MindMap model start
        f.write('@startmindmap\n')
        # Write center node
        f.write("+ Then\n")
        # Write Actions
        for action in automation.actions:
            f.write(f"++ {print_operand(action.attribute)} = {action.value}\n")
        # Write Conditions
        visit_node(automation.condition, depth, metamodel, f)
        # Write MindMap model end
        f.write("@endmindmap")
        # Close file writer
        f.close()


# Main CLI Command Group
@click.group()
def cli():
    pass


# Visualization
@click.command()
@click.argument('metamodel_in')
@click.argument('model_in')
@click.argument('automation_name')
@click.option('--out', default="", help="output file")
def visualize(metamodel_in, model_in, automation_name, out):
    """
    Function used to implement the visualization's tool standalone Command Line Utility. Calls visualize_automation().
    :param metamodel_in: Metamodel used to parse the model.
    :param model_in: Model containing the Automation to be visualized.
    :param automation_name: Automation's name.
    :param out: File directory for saving the Automation visualization. e.g: 'visualization/automation.pu'
    :return:
    """
    # Print message
    click.echo(
        f"Using {metamodel_in} metamodel to visualize {automation_name} automation in {model_in} model. Saving to: {out}")

    # Initialize full metamodel. Custom Entity class is not needed and wouldn't allow for offline execution
    # because the constructor starts a broker publisher and subscriber
    metamodel = metamodel_from_file(metamodel_in, classes=[Attribute, IntAttribute, FloatAttribute,
                                                           StringAttribute, BoolAttribute, ListAttribute,
                                                           DictAttribute, Broker, MQTTBroker, AMQPBroker,
                                                           RedisBroker, BrokerAuthPlain, Automation, Action,
                                                           IntAction, FloatAction, StringAction, BoolAction,
                                                           List, Dict])

    # Initialize full model
    model = metamodel.model_from_file(model_in)

    # Build entities dictionary in model. Needed for evaluating conditions
    model.entities_dict = {entity.name: entity for entity in model.entities}

    # Build entities dictionary in model. Needed for browsing automations
    model.automations_dict = {automation.name: automation for automation in model.automations}

    # Build Conditions for all Automations
    for automation in model.automations:
        automation.build_condition()
        print(f"{automation.name} condition:\n{automation.condition.cond_lambda}\n")

    # Call visualize_automation() to visualize selected automation
    visualize_automation(metamodel=metamodel, automation=model.automations_dict[automation_name], out_dir=out)


# Add visualize command to
cli.add_command(visualize)

# CLI Utility Entry Point
if __name__ == '__main__':
    cli()
