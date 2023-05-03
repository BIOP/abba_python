from scyjava import jimport
from jpype.types import JObject, JClass

import logging

PyCommandBuilder = jimport('org.scijava.command.PyCommandBuilder')
PyParameterBuilder = jimport('org.scijava.command.PyParameterBuilder')

# Decorator that registers a python CLASS containing a method named "run" as a Scijava Command
#
# This uses PyCommandBuilder which is in the java repo ch.epfl.biop:pyimagej-scijava-command
# PyCommandBuilder allows to build a Command fully programmatically without using any
# java annotation as java annotations are needed for 'easy' Scijava Commands definition
# but these are not completely supported in JPype:
# cf https://github.com/jpype-project/jpype/issues/940
#
# Example of registering a Scijava Command via the @ScijavaCommand decorator:
# ------------------------------------------
# @ScijavaCommand(context=ij.context(),  # ij context needed
#                 name='pyCommand.HelloCommand')
# @ScijavaInput('name', JString,
#               label='Name :', description='Please enter your name')
# @ScijavaInput('familiar', JBoolean,
#               label='Familiar :', description='Hi or Hello ?')
# @ScijavaOutput('greetings', JString)
# class HelloCommand:
#
#     def run(self):
#         if (self.familiar):
#             self.greetings = 'Hi ' + str(self.name) + '!'
#         else:
#             self.greetings = 'Hello my dear ' + str(self.name) + '.'
#         print(self.greetings)
# ------------------------------------------
#
# Note: this way of defining a command is probably not ideal if this has to be used from the python side also
#
# Because it's a preliminary work, this decorator prints a lot of stuff in the process
#
# TODO: functools ??

logger = logging.getLogger('ScijavaCommand')

def ScijavaCommand(name, context):
    logger.info("- Registering scijava command " + name)

    def registerCommand(func):

        # This class will be registered as a SciJava Command
        builder = PyCommandBuilder()  # Java PyCommandBuilder

        # The name of the command - to avoid name conflicts, consider a 'virtual' class name with its package
        builder = builder.name(name).label(name)

        # Register all inputs
        if hasattr(func, 'scijava_inputs'):
            logger.debug('- Inputs')
            for scijava_input_name, scijava_input_properties in func.scijava_inputs.items():
                logger.debug('\t'+ scijava_input_name+ ' : '+ str(scijava_input_properties['scijava_class']))
                builder = builder.input(scijava_input_name,
                                        scijava_input_properties['scijava_class'],
                                        scijava_input_properties['scijava_parameter'])
                setattr(func, scijava_input_name, None)  # declares empty input field
            logger.debug('Inputs registered')
        else:
            logger.debug('- No input')

        # Register all outputs
        if hasattr(func, 'scijava_outputs'):
            logger.debug('- Outputs')
            for scijava_output_name, scijava_output_properties in func.scijava_outputs.items():
                logger.debug('\t'+ scijava_output_name+ ' : '+ str(scijava_output_properties['scijava_class']))
                builder = builder.output(scijava_output_name,
                                         scijava_output_properties['scijava_class'],
                                         scijava_output_properties['scijava_parameter'])
                setattr(func, scijava_output_name, None)  # declares empty input field
            logger.debug('Outputs registered')
        else:
            logger.debug('- No Output')

        # Wraps the run function - takes kwargs as input, returns outputs
        def wrapped_run(inner_kwargs):
            inner_object = func()
            logger.debug('Settings inputs...')
            if hasattr(func, 'scijava_inputs'):
                for input_name in func.scijava_inputs.keys():
                    setattr(inner_object, input_name, inner_kwargs[input_name])
            logger.debug('Inputs set.')
            logger.debug('Running scijava command: ' + name)
            inner_object.run()
            logger.debug(name + ' command execution done.')
            logger.debug('Fetching outputs...')
            outputs = {}
            if hasattr(func, 'scijava_outputs'):
                for output_name in func.scijava_outputs.keys():
                    outputs[output_name] = getattr(inner_object, output_name)  # gets outputs
            logger.debug('Outputs set.')
            return JObject(outputs, JClass('java.util.Map'))  # Returns output as a java HashMap

        # Sets the function in PyCommandBuilder:
        # Function<Map<String, Object>, Map<String, Object>> command
        builder = builder.function(wrapped_run)

        # Effectively registers this command to the ij context
        builder.create(context)
        return func

    return registerCommand


def ScijavaInput(scijava_input_name, scijava_class, **kwargs):
    logger.debug("- Registering scijava input "+scijava_input_name)
    def registerInput(func):

        if not hasattr(func, 'scijava_inputs'):
            setattr(func, 'scijava_inputs', dict())

        if scijava_input_name in func.scijava_inputs:
            raise Exception("Error, two inputs have the same name " + str(scijava_input_name))

        scijava_parameter = PyParameterBuilder.input()

        for key, value in kwargs.items():
            getattr(scijava_parameter, key)(value) # builder pattern powa!

        func.scijava_inputs[scijava_input_name] = \
            {'scijava_class': scijava_class,
             'scijava_parameter': scijava_parameter.get()}

        return func

    return registerInput


def ScijavaOutput(scijava_output_name, scijava_class, **kwargs):
    logger.debug("- Registering scijava output "+scijava_output_name)

    def registerOutput(func):

        if not hasattr(func, 'scijava_outputs'):
            setattr(func, 'scijava_outputs', dict())

        if scijava_output_name in func.scijava_outputs:
            raise Exception("Error, two outputs have the same name " + str(scijava_output_name))

        scijava_parameter = PyParameterBuilder.output()

        for key, value in kwargs.items():
            getattr(scijava_parameter, key)(value) # builder pattern powa!

        func.scijava_outputs[scijava_output_name] = \
            {'scijava_class': scijava_class,
             'scijava_parameter': scijava_parameter.get()}

        return func

    return registerOutput
