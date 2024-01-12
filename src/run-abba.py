# core dependencies
import time

import abba

# in order to wait for a jvm shutdown
import jpype

if __name__ == '__main__':

    abba.start_imagej(headless=False)

    # Wait for the JVM to shut down
    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")
