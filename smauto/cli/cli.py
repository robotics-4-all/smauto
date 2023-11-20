import click
import os
from rich import print, pretty

from smauto.interpreter import ModelExecutor
from smauto.generator import generate_automation_graph_from_file
from smauto.language import build_model
from smauto.transformations import model_to_vnodes, smauto_m2t
from smauto.transformations import model_to_vent

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
    model = build_model(model_path)
    print('[*] Model validation success!!')


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


@cli.command('gen',
             help='Generate in Python')
@click.pass_context
@click.argument('model_path')
def generate_py(ctx, model_path):
    pycode = smauto_m2t(model_path)
    model = build_model(model_path)
    filepath = f'{model.metadata.name}.py'
    with open(filepath, 'w') as fp:
        fp.write(pycode)
        make_executable(filepath)
    print(f'[CLI] Compiled Automations: [bold]{filepath}')


@cli.command('genv',
             help='Entities to Code - Generate executable virtual entities')
@click.pass_context
@click.argument('model_path')
@click.option('--merged', '-m', is_flag=True,
              help="Merge virtual entities into a single output file")
def generate_vent(ctx, model_path: str, merged: bool):
    model = build_model(model_path)
    if merged:
        vent_code = model_to_vent(model_path)
        filepath = f'{model.metadata.name.lower()}_entities.py'
        with open(filepath, 'w') as fp:
            fp.write(vent_code)
            make_executable(filepath)
            print(f'[CLI] Compiled virtual Entities: [bold]{filepath}')
    else:
        vnodes = model_to_vnodes(model_path)
        for vn in vnodes:
            filepath = f'{vn[0].name}.py'
            with open(filepath, 'w') as fp:
                fp.write(vn[1])
                make_executable(filepath)
            print(f'[CLI] Compiled virtual Entity: [bold]{filepath}')


def main():
    cli(prog_name='smauto')
