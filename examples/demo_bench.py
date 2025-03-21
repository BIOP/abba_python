# examples/demo_gui.py
import jpype
import time

from abba_python.abba import Abba


def main():

    # if you want to change the atlas that are using the ccfv3 convention
    # abba.atlases_using_allen_ccfv3_convention = []

    # To enable Java debugging:

    attach_java_debugger = False

    import scyjava
    scyjava.config.add_option('-Xmx8g')

    if attach_java_debugger:
        scyjava.config.add_option('-Xint')
        scyjava.config.add_option('-Xdebug')
        scyjava.config.add_option('-Xnoagent')
        scyjava.config.add_option('-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:12999')

    abba = Abba('allen_mouse_10um_java')

    # Configuration or setup code for the demo
    # Initialize the main class or GUI

    abba.benchmark(comment="Benchmark from PyimageJ",
                   demo_dataset="25 sections",
                   use_gui=True,
                   wait_betweem_each_step=True)

    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")


if __name__ == "__main__":
    main()
