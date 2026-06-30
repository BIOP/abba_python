# examples/demo_brainglobe.py
# Minimal smoke test: start ABBA directly with a BrainGlobe atlas.
# The atlas is downloaded and parsed entirely on the Java side (via Appose),
# so no Python-side brainglobe-atlasapi install is required.
import jpype
import time

from abba_python.abba import Abba


def main():

    import scyjava
    scyjava.config.add_option('-Xmx8g')

    # 'example_mouse_100um' is the small BrainGlobe demo atlas: quick to
    # download, ideal to check that BrainGlobe atlas loading works end to end.
    # Any BrainGlobe atlas name works here (e.g. 'allen_mouse_25um').
    abba = Abba('example_mouse_100um')
    abba.show_bdv_ui()

    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")


if __name__ == "__main__":
    main()
