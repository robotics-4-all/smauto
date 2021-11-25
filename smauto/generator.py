# Copyright (c) 2021, Panayiotou, Konstantinos <klpanagi@gmail.com>
# Author: Panayiotou, Konstantinos <klpanagi@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import subprocess
from textx import generator, textx_isinstance

from smauto.language import get_metamodel, build_model
from smauto.lib.automation import (Action, Automation, BoolAction, Dict,
                                   FloatAction, IntAction, List, StringAction)
from smauto.lib.broker import (AMQPBroker, Broker, BrokerAuthPlain, MQTTBroker,
                               RedisBroker)
from smauto.lib.entity import (Attribute, BoolAttribute, DictAttribute,
                               FloatAttribute, IntAttribute, ListAttribute,
                               StringAttribute)

# List of primitive types that can be directly printed
primitives = (int, float, str, bool)
# Custom classes with a __repr__ function so that returning them will print
# them out. E.g: List class -> python list
custom_classes = (Dict, List)


def print_operand(node):
    """
    Returns how a node from the Automation Condition abstract syntax tree
    should be printed during the construction of the condition's python
    expression. If it's a primitive, a dictionary or a list, it is simply
    printed out as a literal. If it is an Entity Attribute, it is printed out
    as "entity_name.attribute_name".

    :param node: A node from the Automation Condition abstract syntax tree.
    :return: The node printed out the correct way for building an Automation's
    Condition python expression.
    """
    if type(node) in primitives or type(node) in custom_classes:
        return node
    else:
        return node.parent.name + '.' + node.name


# Pre-Order traversal of Condition tree
def visit_node(node, depth, metamodel, file_writer):
    """
    Function called recursively to visit the Automation's Condition abstract
    syntax tree using pre-order traversal to create a PlantUML MindMap of the
    Automation's Condition.

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

    # If we are in a ConditionGroup node, recursively visit the left
    # and right sides
    # TODO: Probably passing around metamodel as an argument just for
    # accessing the ConditionGroup class is not best
    if textx_isinstance(node,
                        metamodel.namespaces['automation']['ConditionGroup']):

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


def pu_to_png_transformation(pu_file_path: str):
    subprocess.Popen(['plantuml', pu_file_path])


def generate_automation_graph(automation, dest=""):
    """
    Creates a PlantUML MindMap of the desired Automation.

    :param automation: The Automation to be visualized
    :param dest: File path for saving the Automation visualization.
        e.g: 'visualization/automation.pu'
        (optional)
    :return:
    """
    # Initial MindMap depth
    depth = 1

    # Set default output file directory
    if dest == "":
        dest = f"automation_{automation.name}.pu"

    metamodel = get_metamodel()

    # Open output file and write
    with open(dest, 'w') as f:
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
    return dest


def generate_automation_graph_from_file(model_path):
    model = build_model(model_path)
    # Build entities dictionary in model. Needed for evaluating conditions
    model.entities_dict = {entity.name: entity for entity in model.entities}
    for automation in model.automations:
        automation.build_condition()
        fpath = generate_automation_graph(automation)
        pu_to_png_transformation(fpath)


@generator('smauto', 'automation_graph')
def text_automation_graph_generator(metamodel, model, output_path,
                                    overwrite, debug, **custom_args):
    for automation in model.automations:
        automation.build_condition()
        print(f"{automation.name} condition:{automation.condition.cond_lambda}")
        generate_automation_graph(automation)
