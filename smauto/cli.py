import sys
import click

from smauto.interpreter import interpret_model_from_path


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)


@cli.command(help='Interpreter')
@click.pass_context
@click.argument('model_path')
def interpret(ctx, model_path):
    interpret_model_from_path(model_path)


def main():
    cli(obj={})
