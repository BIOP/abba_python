import threading
import ipywidgets as widgets
from IPython.display import display
from scyjava import jimport
from jpype import JImplements, JOverride
from jpype.types import JString, JBoolean, JDouble, JInt, JFloat

from ipyfilechooser import FileChooser
import logging

logger = logging.getLogger('ScijavaJupyterUI')

Consumer = jimport('java.util.function.Consumer')
Supplier = jimport('java.util.function.Supplier')
JFile = jimport('java.io.File')
PyPreprocessor = jimport('org.scijava.processor.PyPreprocessor')


def enable_jupyter_ui():
    PyPreprocessor = jimport('org.scijava.processor.PyPreprocessor')
    PyPreprocessor.register(IPyWidgetCommandPreprocessorSupplier())
    print('Scijava jupyter ui enabled')


@JImplements(Consumer)
class IPyWidgetCommandPreprocessor(object):

    @JOverride
    def accept(self, module):
        self.module = module
        inputs = module.getInputs()
        self.all_widgets = dict()
        logger.debug('Jupyter pre-processing, module ' + str(module))
        for input_key in inputs.keySet():
            if not module.isInputResolved(input_key):
                logger.debug('Unresolved input: ' + str(input_key))
                current_widget = get_jupyter_widget(module, input_key)
                if current_widget is not None:
                    logger.debug('Widget acquired for input ' + str(input_key))
                    self.all_widgets[input_key] = current_widget
                else:
                    # maybe log something or put a warning
                    logger.debug('Widget not found for input ' + str(input_key))
                    pass

        if len(self.all_widgets) != 0:
            list_of_widgets = [x.get_widget() for key, x in self.all_widgets.items()]

            # Creates an OK button, and its associated event
            user_has_clicked = threading.Event()
            ok_button = widgets.Button(description='OK')
            ok_button.on_click(lambda _: user_has_clicked.set())
            list_of_widgets.append(ok_button)
            logger.debug('Display widgets module ' + str(module))
            display(widgets.VBox(list_of_widgets))
            logger.debug('Waiting for click')

            # Wait for button click
            user_has_clicked.wait()
            logger.debug('button clicked')

            # the user has clicked
            # retrieve contents of all widgets:
            for key, w in self.all_widgets.items():
                logger.debug('Resolving input ' + str(key))
                module.setInput(key, w.get_value())
                module.resolveInput(key)
                logger.debug('Input ' + str(key) + " resolved")


@JImplements(Supplier)
class IPyWidgetCommandPreprocessorSupplier(object):
    @JOverride
    def get(self):
        return IPyWidgetCommandPreprocessor()


booleanClasses = ['class java.lang.Boolean', 'boolean']
intClasses = ['class java.lang.Integer', 'int']
floatClasses = ['class java.lang.Float', 'float']
doubleClasses = ['class java.lang.Double', 'double']


def getLabel(module, input_key):
    label = module.getInfo().getInput(input_key).getLabel()
    if (label is None) or (label == ''):
        label = str(input_key)
    else:
        label = str(label)
    return label


def get_jupyter_widget(module, input_key):
    if str(module.getInfo().getInput(input_key).getType()) == 'class java.lang.String':
        return JupyterTextWidget(module, input_key)

    if str(module.getInfo().getInput(input_key).getType()) in booleanClasses:
        return JupyterToggleWidget(module, input_key)

    if str(module.getInfo().getInput(input_key).getType()) in intClasses:
        return JupyterIntWidget(module, input_key)

    if str(module.getInfo().getInput(input_key).getType()) in floatClasses:
        return JupyterFloatWidget(module, input_key)

    if str(module.getInfo().getInput(input_key).getType()) in doubleClasses:
        return JupyterDoubleWidget(module, input_key)

    if str(module.getInfo().getInput(input_key).getType()) == 'class java.io.File':
        return JupyterFileWidget(module, input_key)

    print("Unsupported widget for type " + str(module.getInfo().getInput(input_key).getType()))

    return None


class JupyterInputWidget:
    def __init__(self, module, input_key):
        pass

    def get_widget(self):
        return self.widget

    def get_value(self):
        return None


class JupyterTextWidget(JupyterInputWidget):
    def __init__(self, module, input_key):
        self.widget = widgets.Text(
            value=str(module.getInput(input_key)),
            placeholder=str(module.getInfo().getInput(input_key).getDescription()),
            description=getLabel(module, input_key),
            disabled=False
        )

    def get_value(self):
        return JString(self.widget.value)


class JupyterToggleWidget(JupyterInputWidget):
    def __init__(self, module, input_key):
        self.widget = widgets.Checkbox(
            value=bool(module.getInput(input_key)),
            description=getLabel(module, input_key),
            disabled=False,
            indent=True
        )

    def get_value(self):
        return JBoolean(self.widget.value)


class JupyterIntWidget(JupyterInputWidget):
    def __init__(self, module, input_key):
        min_value = module.getInfo().getInput(input_key).getMinimumValue()
        max_value = module.getInfo().getInput(input_key).getMaximumValue()
        step_size = module.getInfo().getInput(input_key).getStepSize()

        if (min_value is not None) and (max_value is not None):

            if step_size is None:
                step_size = 1
            else:
                step_size = step_size.intValue()

            self.widget = widgets.BoundedIntText(
                value=int(module.getInput(input_key)),
                min=int(min_value),
                max=int(max_value),
                step=int(step_size),
                description=getLabel(module, input_key),
                disabled=False
            )
        else:
            self.widget = widgets.IntText(
                value=int(module.getInput(input_key)),
                description=getLabel(module, input_key),
                disabled=False
            )

    def get_value(self):
        return JInt(self.widget.value)


class JupyterFloatWidget(JupyterInputWidget):
    def __init__(self, module, input_key):

        min_value = module.getInfo().getInput(input_key).getMinimumValue()
        max_value = module.getInfo().getInput(input_key).getMaximumValue()
        step_size = module.getInfo().getInput(input_key).getStepSize()

        if (min_value is not None) and (max_value is not None):
            if step_size is None:
                step_size = 1
            else:
                step_size = step_size.intValue()

            self.widget = widgets.FloatText(
                value=float(module.getInput(input_key)),
                min=float(min_value),
                max=float(max_value),
                step=float(step_size),
                description=getLabel(module, input_key),
                disabled=False
            )
        else:
            self.widget = widgets.BoundedFloatText(
                value=float(module.getInput(input_key)),
                description=getLabel(module, input_key),
                disabled=False
            )

    def get_value(self):
        return JFloat(self.widget.value)


class JupyterDoubleWidget(JupyterFloatWidget):
    def __init__(self, module, input_key):
        JupyterFloatWidget.__init__(self, module, input_key)

    def get_value(self):
        return JDouble(self.widget.value)


class JupyterFileWidget(JupyterInputWidget):
    def __init__(self, module, input_key):

        styles = module.getInfo().getInput(input_key).getWidgetStyle().replace(" ", "").split(',')

        if 'save' in styles:
            self.save = True
            self.widget = widgets.Text(
                value=str(module.getInput(input_key)),
                placeholder=str(module.getInfo().getInput(input_key).getDescription()),
                description=getLabel(module, input_key),
                disabled=False
            )

        else:
            self.save = False

            # Create and display a FileChooser widget
            fc = FileChooser(select_default=True)
            # Change the title
            fc.title = getLabel(module, input_key)

            if 'directory' in styles:
                # Switch to folder-only mode
                fc.show_only_dirs = True
                if module.getInput(input_key) is not None:
                    fc.default_path = str(module.getInput(input_key))
                    fc.reset()
            else:
                if module.getInput(input_key) is not None:
                    fc.default_path = str(module.getInput(input_key).getParent())
                    fc.default_filename = str(module.getInput(input_key).getName())
                    fc.reset()

            matching_extensions = [s for s in styles if 'extensions:' in s]
            if len(matching_extensions) == 1:
                all_extensions = matching_extensions[0].split(":")[1].split("/")
                # Set multiple file filter patterns (uses https://docs.python.org/3/library/fnmatch.html)
                fc.filter_pattern = ['*.' + str(ext) for ext in all_extensions]

            self.widget = fc

    def get_value(self):
        if self.save:
            return JFile(JString(self.widget.value))
        else:
            return JFile(JString(self.widget.selected))  # TODO : fix casting
