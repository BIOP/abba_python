from IPython.core.magic import register_cell_magic
from jupyter_ui_poll import ui_events
from threading import Thread
from IPython.core.interactiveshell import InteractiveShell
import time


@register_cell_magic('cell_with_modal_ui')
def cell_with_modal_ui(line, cell):
    shell = InteractiveShell.instance()

    def f():
        shell.run_cell(cell)

    cell_runner = Thread(target=f)
    cell_runner.start()
    with ui_events() as poll:
        while cell_runner.is_alive():
            poll(10)  # React to UI events (upto 10 at a time)
            time.sleep(0.1)
