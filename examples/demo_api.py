# examples/demo_gui.py
import jpype
import time
from abba_python.abba import Abba

def main():

    abba = Abba('Adult Mouse Brain - Allen Brain Atlas V3p1')
    abba.show_bdv_ui()

    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")


if __name__ == "__main__":
    main()
