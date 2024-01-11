# core dependencies
import time
# from abba_python import abba # works in CLI
# from abba_python.abba import add_brainglobe_atlases # works in CLI
# in order to wait for a jvm shutdown
import jpype
import imagej

import os

import abba

# THIS FILE SETS MANY PATHS EXPLICITLY WHEN ABBA IS INSTALLED FROM THE INSTALLER!
# IF YOU WANT TO RUN ABBA FROM PYTHON, TRY run-abba.py first!

if __name__ == '__main__':
    os.path.dirname(os.getcwd())

    # In ABBA PYthon, Fiji.app is in the parent directory of this script
    # fiji_app_path = str(os.path.join(os.path.dirname(os.getcwd()), 'Fiji.app'))
    ij = imagej.init(abba.get_java_dependencies(), mode="interactive")

    abba.add_brainglobe_atlases(ij)

    # Set Elastix Path:
    # File ch.epfl.biop.wrappers.elastix.Elastix exePath
    # File ch.epfl.biop.wrappers.transformix.Transformix exePath

    #Todo: set deepslice env path
    from scyjava import jimport
    from jpype.types import JString

    # Java class imports

    DebugTools = jimport('loci.common.DebugTools')
    File = jimport('java.io.File')
    # DebugTools.enableLogging('OFF')
    # DebugTools.enableLogging("INFO");
    # DebugTools.enableLogging("DEBUG");

    # Sets DeepSlice env path

    deepslice_env_path = str(os.path.join(os.path.dirname(os.getcwd()), 'envs', 'deepslice'))
    deepslice_version = JString(str('1.1.5'))
    DeepSlice = jimport('ch.epfl.biop.wrappers.deepslice.DeepSlice')
    DeepSlice.setEnvDirPath(File(deepslice_env_path))
    DeepSlice.setVersion(deepslice_version)  # not autodetected. Do not matter for 1.1.5, but may matter later

    import platform
    if platform.system() == 'Windows':
        elastixPath = str(os.path.join(os.path.dirname(os.getcwd()), 'win', 'elastix-5.0.1-win64', 'elastix.exe'))
        transformixPath = str(os.path.join(os.path.dirname(os.getcwd()), 'win', 'elastix-5.0.1-win64', 'transformix.exe'))

        Elastix = jimport('ch.epfl.biop.wrappers.elastix.Elastix')
        Elastix.exePath = JString(str(elastixPath))
        Elastix.setExePath(File(JString(str(elastixPath))))
        Transformix = jimport('ch.epfl.biop.wrappers.transformix.Transformix')
        Transformix.exePath = JString(str(transformixPath))
        Transformix.setExePath(File(JString(str(transformixPath))))

        # Now let's set the atlas folder location in a folder that all users can access

        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        directory = os.path.join(os.environ['ProgramData'], 'abba-atlas')

        # create the directory with write access for all users
        try:
            print('Attempt to set ABBA Atlas cache directory to ' + directory)
            # //os.mkdir(directory)
            os.makedirs(directory, exist_ok=True)
            atlasPath = str(directory)
            AtlasLocationHelper.defaultCacheDir = File(JString(atlasPath))
            print('ABBA Atlas cache directory set to ' + directory)
        except OSError:
            print('ERROR! Could not set ABBA Atlas cache dir')
            # directory already exists ?
            pass

        # TODO: Set DeepSlice conda env
    else:
        print('ERROR! '+platform.system()+' OS not supported yet.')

    # --


    ij.ui().showUI() # add at the end ?

    # Wait for the JVM to shut down
    while jpype.isJVMStarted():
        time.sleep(1)

    print("JVM has shut down")
