import click
import os
from rich import print, pretty

from smauto.interpreter import ModelExecutor
from smauto.generator import generate_automation_graph_from_file
from smauto.language import build_model
from smauto.transformations import model_to_vnodes

pretty.install()

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
    ModelExecutor.execute_automations_from_path(model_path)


@cli.command('graph',
             help='Graph generator - Generate automation visualization graphs')
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
        print(f'[CLI] Compiled virtual Entity: [bold]{filepath}')


@cli.command('server',
             help='Run the REST Api Server')
@click.pass_context
def api_server(ctx):
    from smauto.api.api import api
    print('[CLI] DEPRECATED!!!')
    print('[CLI] Run the api using uvicorn!')
    print('[CLI] uvicorn smauto.api:api --host 0.0.0.0 --port 8080')


def main():
    cli(prog_name='smauto')
