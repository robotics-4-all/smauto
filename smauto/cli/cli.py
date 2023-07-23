import click
import os
from rich import print

from smauto.interpreter import execute_model_from_path
from smauto.generator import generate_automation_graph_from_file
from smauto.language import build_model
from smauto.transformations import model_to_vnodes


def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2    # copy R bits to X
    os.chmod(path, mode)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)


@cli.command('validate', help='Model Validation')
@click.pass_context
@click.argument('model_path')
def validate(ctx, model_path):
    try:
        model = build_model(model_path)
        print('[*] Model validation success!!')
    except Exception as e:
        print('[*] Validation failed with error(s):')
        print(str(e))


@cli.command('interpret',
             help='Interpreter - Dynamically execute models')
@click.pass_context
@click.argument('model_path')
def interpret(ctx, model_path):
    execute_model_from_path(model_path)


@cli.command(help='Graph generator - Generate automation visualization graphs')
@click.pass_context
@click.argument('model_path')
def graph(ctx, model_path):
    generate_automation_graph_from_file(model_path)


@cli.command('generate',
             help='Entities to Code - Generate executable virtual entities')
@click.pass_context
@click.argument('model_path')
def generate(ctx, model_path):
    vnodes = model_to_vnodes(model_path)
    # return
    for vn in vnodes:
        filepath = f'{vn[0].name}.py'
        with open(filepath, 'w') as fp:
            fp.write(vn[1])
            make_executable(filepath)
        print(f'[*] Compiled virtual Entity: [bold]{filepath}')


def main():
    cli(prog_name='smauto')
