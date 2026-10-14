"""
Generates src/abba_python/commands.py: AbbaCommands, one method per ABBA command, inherited by Abba

The methods follow the SciJava commands of the jars pinned in get_java_dependencies(): run this
script again after bumping them. The commands are described by scijava-introspect, from their
@Plugin and @Parameter annotations and from the field values of a new instance (the defaults).

Usage: python scripts/generate_commands.py
"""

import json
import keyword
import re
import textwrap
from pathlib import Path
from typing import Any

import imagej
import scyjava

from abba_python.abba import configure_java, get_java_dependencies

PACKAGE_DIR = Path(__file__).resolve().parent.parent / 'src' / 'abba_python'
COMMAND_PACKAGE = 'ch.epfl.biop.atlas.aligner.command'
SESSION_TYPE = 'MultiSlicePositioner'  # inputs of this type are set to self.mp

# Commands without a method
SKIPPED_COMMANDS = {
    'ABBAStartCommand': 'creates the session, see Abba.__init__',
    'DisplaySettingsCommand': 'display settings widget: needs a callback and an open viewer',
}

PYTHON_TYPES = {
    'String': 'str', 'char': 'str', 'Character': 'str',
    'double': 'float', 'Double': 'float', 'float': 'float', 'Float': 'float',
    'int': 'int', 'Integer': 'int', 'long': 'int', 'Long': 'int', 'short': 'int', 'Short': 'int',
    'boolean': 'bool', 'Boolean': 'bool',
    'File': 'str | os.PathLike[str]',
    'File[]': 'Sequence[str | os.PathLike[str]]',
}
# Primitive fields are never null: when scijava-introspect reports no default, the value was NaN,
# which ABBA commands use for 'not set, computed by the command'
PRIMITIVE_NUMBERS = {'double', 'float', 'int', 'long', 'short'}
# Output types converted to Python values
OUTPUT_CONVERSIONS = {'Boolean': 'bool', 'boolean': 'bool', 'String': 'str'}

INDENT = '    '


def pythonize(class_name: str) -> str:
    """
    Method name of a command class,
    e.g. RegisterSlicesDeepSliceApposeCommand -> register_slices_deepslice_appose
    """
    if class_name.startswith('ABBA'):
        class_name = class_name[4:]
    for acronym, word in (('BDV', 'Bdv'), ('ImageJ', 'Imagej'), ('QuPath', 'Qupath'), ('QuickNII', 'Quicknii'),
                          ('BigWarp', 'Bigwarp'), ('ABBA', 'Abba'), ('DeepSlice', 'Deepslice'), ('OMERO', 'Omero'),
                          ('ZENODO', 'Zenodo'), ('BenchMark', 'Benchmark')):
        class_name = class_name.replace(acronym, word)
    parts = [part for part in re.split(r'(?=[A-Z])', class_name) if part]
    if parts[-1] == 'Command':
        parts = parts[:-1]
    return '_'.join(part.lower() for part in parts)


def describe(introspector: Any, package: str) -> dict[str, dict[str, Any]]:
    """Commands of a package, not of its sub-packages, keyed by simple class name"""
    described = json.loads(str(introspector.describePackage(package, True)))
    errors = {name: command['error'] for name, command in described.items() if 'error' in command}
    if errors:
        raise RuntimeError(f'Commands that could not be described: {errors}')
    return {name.rsplit('.', 1)[1]: command for name, command in sorted(described.items())
            if name.rsplit('.', 1)[0] == package}


class Parameter:
    """How an input of a command becomes a parameter of its method"""

    def __init__(self, item: dict[str, Any]):
        self.item = item
        self.name = item['name']
        self.python_name = self.name.lower() + ('_' if keyword.iskeyword(self.name.lower()) else '')
        java_type = item['type']
        python_type = PYTHON_TYPES.get(java_type, 'Any')
        if item.get('choices') and python_type == 'str':
            python_type = 'Literal[' + ', '.join(repr(choice) for choice in item['choices']) + ']'
        self.optional = False  # None means: not passed, the command computes the value
        self.default: str | None = None  # Python literal
        if 'default' in item:
            value = item['default']
            # A number field with no initializer reads 0, exactly like '= 0': zero is not trusted as a
            # default, the caller has to give the value
            if not (isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0):
                if python_type == 'float':
                    value = float(value)
                self.default = repr(value)
        elif java_type in PRIMITIVE_NUMBERS or item.get('required') is False:
            self.optional = True
        if self.optional:
            python_type = f'{python_type} | None' if python_type != 'Any' else 'Any'
            self.default = 'None'
        self.annotation = python_type
        self.value = self.python_name
        if java_type == 'File[]':
            self.value = f'_java_files({self.python_name})'

    def signature(self) -> str:
        default = '' if self.default is None else f' = {self.default}'
        return f'{self.python_name}: {self.annotation}{default}'

    def doc(self) -> str:
        label, description = self.item.get('label', ''), self.item.get('description', '')
        text = label + ('. ' if label and description else '') + description
        if self.optional:
            text += ' If None, the command computes the value.'
        wrapped = textwrap.indent(textwrap.fill(text or self.name, 96), INDENT)
        return f'{self.python_name} : {self.annotation}\n' + wrapped


def title(command: dict[str, Any]) -> str:
    return str(command.get('label') or command.get('menuPath', command['name']).rsplit('>', 1)[-1])


def method_code(simple_name: str, command: dict[str, Any]) -> str:
    inputs = [item for item in command['input'] if item['type'] != SESSION_TYPE]
    session = [item['name'] for item in command['input'] if item['type'] == SESSION_TYPE]
    parameters = [Parameter(item) for item in inputs]
    # Required parameters first, each group in alphabetical order
    parameters.sort(key=lambda p: (p.default is not None, p.python_name))
    outputs = command.get('output', [])

    lines = [f'def {pythonize(simple_name)}(self' + (', *' if parameters else '')]
    if parameters:
        lines[0] += ','
        lines += [f'{INDENT * 2}{p.signature()},' for p in parameters]
        lines[-1] = lines[-1][:-1]
    return_type = 'Any'
    if len(outputs) == 1:
        return_type = {'bool': 'bool | None', 'str': 'str | None'}.get(
            OUTPUT_CONVERSIONS.get(outputs[0]['type'], ''), 'Any')
    lines[-1] += f') -> {return_type}:'

    doc = [title(command), '']
    if command.get('description'):
        doc += [textwrap.fill(command['description'], 100), '']
    if command.get('messages'):
        doc += [textwrap.fill('Dialog message: ' + ' '.join(command['messages']), 100), '']
    if command.get('hasInitializer') or command.get('dynamic'):
        doc += [textwrap.fill('Some defaults or choices are computed from the session when the command opens.',
                              100), '']
    if parameters:
        doc += ['Parameters', '----------'] + [p.doc() for p in parameters] + ['']
    doc += ['Returns', '-------']
    if len(outputs) == 1:
        output = outputs[0]
        doc += [f'{return_type}', INDENT + (output.get('label') or output['name'])
                + ('. ' + output['description'] if output.get('description') else '')]
    else:
        doc += ['Any', INDENT + 'The command module, once the command has run']
    doc_text = '\n'.join(doc).rstrip().replace('\\', '\\\\')  # no escape sequences in docstrings
    lines.append(textwrap.indent('"""\n' + doc_text + '\n"""', INDENT))

    entries = [f"'{name}': self.mp" for name in session] + [f"'{p.name}': {p.value}" for p in parameters]
    output_argument = ''
    if len(outputs) == 1:
        output_argument = f", output='{outputs[0]['name']}'"
        conversion = OUTPUT_CONVERSIONS.get(outputs[0]['type'])
        if conversion:
            output_argument += f', convert={conversion}'
    # _run_command returns Any: a typed result goes through a typed variable
    target = 'return ' if return_type == 'Any' else f'result: {return_type} = '
    call = f"{target}self._run_command('{command['name']}', {{"
    if entries:
        lines.append(INDENT + call)
        lines += [INDENT * 2 + entry + ',' for entry in entries]
        lines.append(INDENT + '}' + output_argument + ')')
    else:
        lines.append(INDENT + call + '}' + output_argument + ')')
    if return_type != 'Any':
        lines.append(INDENT + 'return result')
    return textwrap.indent('\n'.join(lines), INDENT)


COMMANDS_HEADER = '''"""
ABBA commands as methods: each one runs a SciJava command of {package}

GENERATED by scripts/generate_commands.py from the jars of get_java_dependencies(): do not edit,
run the script again instead.
"""

import os
from collections.abc import Callable, Sequence
from typing import Any, Literal

from scyjava import jimport


def _java_files(paths: Sequence[str | os.PathLike[str]]) -> Any:
    """java.io.File[] from paths"""
    from jpype.types import JArray

    File = jimport('java.io.File')
    return JArray(File)([File(os.fspath(path)) for path in paths])


class AbbaCommands:
    """
    Methods running ABBA commands on the ABBA session self.mp, through the ImageJ instance self.ij

    Parameters are keyword-only. A parameter without default must be given: a missing input would
    make ABBA ask for it in a dialog. A None default means the command computes the value.
    """

    ij: Any
    mp: Any

    def _run_command(self, class_name: str, inputs: dict[str, Any], output: str | None = None,
                     convert: Callable[[Any], Any] | None = None) -> Any:
        """
        Runs a command and waits for it to finish

        :param inputs: None values are not passed, the command computes them
        :param output: name of the output to return, otherwise the module is returned
        :param convert: conversion of the output to a Python value, unless it is None
        """
        arguments: list[Any] = []
        for name, value in inputs.items():
            if value is not None:
                arguments += [name, os.fspath(value) if isinstance(value, os.PathLike) else value]
        info = self.ij.command().getCommand(jimport(class_name))
        if info is None:
            raise ValueError(f'{class_name} is not a registered SciJava command')
        # Not CommandService.run: it returns no future for DynamicCommands (they extend Module)
        module = self.ij.module().run(info, True, *arguments).get()
        if output is None:
            return module
        value = module.getOutput(output)
        return value if value is None or convert is None else convert(value)
'''


def main() -> None:
    configure_java()
    imagej.init(get_java_dependencies())
    introspector = scyjava.jimport('ch.unige.biochem.scijava.introspect.CommandIntrospector')

    commands = describe(introspector, COMMAND_PACKAGE)

    methods = []
    for simple_name, command in commands.items():
        if simple_name in SKIPPED_COMMANDS:
            continue
        command['method'] = pythonize(simple_name)
        methods.append(method_code(simple_name, command))
    names = [command['method'] for command in commands.values() if 'method' in command]
    if len(set(names)) != len(names):
        raise RuntimeError(f'Two commands give the same method name: {sorted(names)}')

    code = COMMANDS_HEADER.replace('{package}', COMMAND_PACKAGE) + '\n' + '\n\n'.join(methods) + '\n'
    (PACKAGE_DIR / 'commands.py').write_text(code, encoding='utf-8', newline='\n')

    print(f'{len(methods)} methods, {len(commands)} ABBA commands')


if __name__ == '__main__':
    main()
