# core dependencies
import time
from abba import start_imagej

# in order to wait for a jvm shutdown
import jpype


if __name__ == '__main__':
    # from DeepSlice import DSModel
    # model = DSModel("mouse")

    # model.predict(image_directory="C:/Users/nicol/AppData/Local/Temp/temp/deepslice", ensemble=False)
    # model.save_predictions("C:/Users/nicol/AppData/Local/Temp/temp/deepslice/results")
    # MAC ISSUE
    # https: // github.com / imagej / pyimagej / issues / 23
    # -- FOR DEBUGGING
    # import imagej.doctor
    # imagej.doctor.checkup()
    # imagej.doctor.debug_to_stderr()
    # -- Atlas
    # Any brainglobe atlas can be used
    # show_atlases()
    # abba_python = Abba("azba_zfish_4um", slicing_mode='sagittal', headless=True)  # or any other brainglobe atlas

    # -- HEADLESS
    # abba_python = Abba('Adult Mouse Brain - Allen Brain Atlas V3', headless=True)  # or any other brainglobe atlas
    # --

    # -- NOT HEADLESS
    # abba = Abba('Adult Mouse Brain - Allen Brain Atlas V3')
    # abba.show_bdv_ui()  # creates and show a bdv view

    start_imagej(headless=False)
    # Wait for the JVM to shut down
    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")
