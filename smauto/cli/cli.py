import click

from smauto.interpreter import execute_model_from_path
from smauto.generator import generate_automation_graph_from_file
from smauto.language import build_model


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)


@cli.command(help='Validator')
@click.pass_context
@click.argument('model_path')
def validate(ctx, model_path):
    try:
        model = build_model(model_path)
        print('[*] Model validation success!!')
    except Exception as e:
        print('[*] Validation failed with error(s):')
        print(str(e))


@cli.command(help='Interpreter - Dynamically execute models')
@click.pass_context
@click.argument('model_path')
def interpret(ctx, model_path):
    execute_model_from_path(model_path)


@cli.command(help='Graph generator - Generate automation visualization graphs')
@click.pass_context
@click.argument('model_path')
def graph(ctx, model_path):
    generate_automation_graph_from_file(model_path)


def main():
    cli(prog_name='smauto')
