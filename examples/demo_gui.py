# examples/demo_gui.py
import jpype
import time

from abba_python import abba


def main():
    # To enable Java debugging:

    attach_java_debugger = False

    import scyjava
    scyjava.config.add_option('-Xmx8g')

    if attach_java_debugger:
        scyjava.config.add_option('-Xint')
        scyjava.config.add_option('-Xdebug')
        scyjava.config.add_option('-Xnoagent')
        scyjava.config.add_option('-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:12999')

    # Configuration or setup code for the demo
    # Initialize the main class or GUI
    abba.start_imagej(headless=False)

    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")


if __name__ == "__main__":
    main()
