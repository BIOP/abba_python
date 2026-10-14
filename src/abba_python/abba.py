"""Main module."""

import os
import time
from collections.abc import Iterable, Sequence
from typing import Any, ClassVar, Literal

import imagej
import scyjava
from jpype.types import JArray, JString
from scyjava import jimport

from .commands import AbbaCommands

LogLevel = Literal['OFF', 'DEBUG', 'INFO']


def get_java_dependencies() -> list[str]:
    """
    Returns the jar files that need to be included into the classpath
    of an imagej object in order to have a functional ABBA app
    these jars should be available in https://maven.scijava.org/
    :return:
    """
    return ['ch.epfl.biop:ijl-utilities-wrappers:0.12.1',
            'ch.epfl.biop:ImageToAtlasRegister:0.25.0',
            'ch.epfl.biop:bigdataviewer-biop-tools:0.24.2',
            'ch.unige.biochem:scijava-introspect:0.2.0',
            'sc.fiji:bigdataviewer-playground:0.23.1',
            'sc.fiji.bigdataviewer:bigdataviewer-playground-display:0.23.1',
            'com.formdev:flatlaf:3.5.1',
            'ch.epfl.biop:bigdataviewer-image-loaders:0.23.4',
            'ch.epfl.biop:atlas:0.23.4'
            ]


# Java version the jars of get_java_dependencies() are compiled for
JAVA_VERSION = '21'


def configure_java() -> None:
    """
    Makes scyjava start the JVM with the Java version required by ABBA's jars
    (scyjava fetches Java 11 by default). Has no effect once the JVM is started.
    """
    if scyjava.jvm_started():
        # e.g. a scyjava.jimport call before creating Abba starts a JVM without ABBA's jars,
        # and imagej.init then fails with "'NoneType' object is not callable"
        raise RuntimeError('The JVM is already started, without the ABBA dependencies: create '
                           'Abba (or call start_imagej) before any scyjava.jimport, or pass an '
                           'existing ij instance to Abba')
    scyjava.config.set_java_constraints(version=JAVA_VERSION)


def start_imagej(headless: bool = False,
                 log_level: LogLevel = 'INFO') -> Any:
    """
    Starts Fiji with the full ABBA GUI (the ABBA commands in the menus), instead of an Abba object

    :param headless: starts without any window
    :param log_level: logging level of Bio-Formats
    :return: the ImageJ instance, which can be passed to Abba to share its JVM
    """
    mode = "headless"
    if not headless:
        mode = "interactive"
    configure_java()
    ij = imagej.init(get_java_dependencies(), mode=mode)

    from jpype.types import JString
    from scyjava import jimport

    DebugTools = jimport('loci.common.DebugTools')
    DebugTools.enableLogging(JString(log_level))

    import platform
    if platform.system() == 'Windows':
        File = jimport('java.io.File')
        # Now let's set the atlas folder location in a folder with all users access

        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        directory = os.path.join(os.environ['ProgramData'], 'abba-atlas')

        # create the directory with write access for all users
        try:
            print('Attempt to set ABBA Atlas cache directory to ' + directory)
            os.makedirs(directory, exist_ok=True)
            AtlasLocationHelper.defaultCacheDir = File(JString(str(directory)))
            print('ABBA Atlas cache directory set to ' + directory)
        except OSError:
            print('ERROR! Could not set ABBA Atlas cache dir')
            # directory already exists ?
            pass
    else:
        print('[WARNING] Support for third-party brain atlases through BrainGlobe is primarily tested on Windows. '
              'If you encounter any OS-specific issues on ' + platform.system() + ', please report them to the '
              'developers: https://github.com/BIOP/abba_python/issues')
    pass

    if not headless:
        ij.ui().showUI()

    # Adds Python information to ABBA help command
    ABBAForumHelpCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAForumHelpCommand')
    from abba_python import __version__
    python_info = 'ABBA Python ' + str(__version__)
    ABBAForumHelpCommand.pythonInformation = JString(python_info)
    return ij


class Abba(AbbaCommands):
    """Abba object which can be used to register sections to a BrainGlobe atlas object

    Parameters
    ----------
    atlas_name :
        Name of the atlas to be used, should be either:
         - available in BrainGlobe
         - or be available in https://github.com/BIOP/ijp-atlas:
            'Adult Mouse Brain - Allen Brain Atlas V3' (default)
            'Rat - Waxholm Sprague Dawley V4'
    ij :
        ImageJ instance, should be reused if you need to open several ABBA instances
        non setting this variable will create an ij instance with minimal dependencies
        If you want to provide your ij instance, make sure that it contains the dependencies
        declared in abba_python.Abba.get_java_dependencies (and all the transitive ones)

        abba_python.ij() returns the current ij instance, which can also be reused in another
        abba_python instance
    x_axis :
        See https://github.com/BIOP/ijp-imagetoatlas/blob/master/src/main/java/ch/epfl/biop/atlas/aligner/command/ABBAStartCommand.java
        should be 'AP', 'PA', 'LR', 'RL', 'DV', 'VD'
    y_axis :
        should be 'AP', 'PA', 'LR', 'RL', 'DV', 'VD'
    z_axis :
        should be 'AP', 'PA', 'LR', 'RL', 'DV', 'VD'
    log_level :
        should be taken within LogLevel literal

    """

    opened_atlases: ClassVar[dict[str, Any]] = {}

    def __init__(
            self,
            atlas_name: str = 'Adult Mouse Brain - Allen Brain Atlas V3p1',
            ij: Any = None,
            x_axis: str = 'RL',
            y_axis: str = 'SI',
            z_axis: str = 'AP',
            headless: bool = False,
            print_config: bool = True,
            log_level: LogLevel = 'INFO'
    ) -> None:
        if ij is None:
            configure_java()
            if headless:
                ij = imagej.init(get_java_dependencies())
            else:
                ij = imagej.init(get_java_dependencies(), mode='interactive')
                ij.ui().showUI()
            self.ij = ij
        else:
            print('ij was provided, headless argument ignored')
            self.ij = ij

        # Look in object service to see if the atlas is not already opened by any chance
        # in java TODO
        # return
        # or in python
        if atlas_name not in Abba.opened_atlases:
            if atlas_name == 'Adult Mouse Brain - Allen Brain Atlas V3':
                atlas_name = 'Adult Mouse Brain - Allen Brain Atlas V3p1'
            if atlas_name == 'Rat - Waxholm Sprague Dawley V4':
                atlas_name = 'Rat - Waxholm Sprague Dawley V4p2'
            if atlas_name == 'Rat - Waxholm Sprague Dawley V4p1':
                atlas_name = 'Rat - Waxholm Sprague Dawley V4p2'
            if atlas_name == 'Adult Mouse Brain - Allen Brain Atlas V3p1':
                AllenBrainAdultMouseAtlasCCF2017Command = jimport(
                    'ch.epfl.biop.atlas.mouse.allen.ccfv3p1.command.AllenBrainAdultMouseAtlasCCF2017v3p1Command')
                atlas = ij.command().run(AllenBrainAdultMouseAtlasCCF2017Command, True).get().getOutput("ba")
                Abba.opened_atlases[atlas_name] = atlas
            elif atlas_name == 'Rat - Waxholm Sprague Dawley V4p2':
                WaxholmSpragueDawleyRatV4Command = jimport(
                    'ch.epfl.biop.atlas.rat.waxholm.spraguedawley.v4p2.command.WaxholmSpragueDawleyRatV4p2Command')
                atlas = ij.command().run(WaxholmSpragueDawleyRatV4Command, True).get().getOutput("ba")
                Abba.opened_atlases[atlas_name] = atlas
            elif atlas_name == 'allen_mouse_10um_java':
                AllenBrainAdultMouseAtlasCCF2017v3p1ASRCommand = jimport(
                    'ch.epfl.biop.atlas.mouse.allen.ccfv3p1asr.command.AllenBrainAdultMouseAtlasCCF2017v3p1ASRCommand')
                atlas = ij.command().run(AllenBrainAdultMouseAtlasCCF2017v3p1ASRCommand, True).get().getOutput("ba")
                Abba.opened_atlases[atlas_name] = atlas
            else:
                # Any other name is delegated to the BrainGlobe atlas loader on the
                # Java side, which manages its own Python environment (via Appose)
                # to download and parse the atlas.
                # BrainGlobeAtlas.initialize() resolves the SciJava context through
                # AtlasLocationHelper.getContext() (to build the atlas sources). That
                # context is normally set by the GUI's AtlasChooserCommand; since we
                # bypass it here, we set it ourselves to avoid a NullPointerException.
                AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
                AtlasLocationHelper.setContext(ij.context())
                BrainGlobeAtlas = jimport('ch.epfl.biop.atlas.brainglobe.BrainGlobeAtlas')
                atlas = BrainGlobeAtlas(atlas_name)
                atlas.initialize(None, None)
                Abba.opened_atlases[atlas_name] = atlas
                ij.object().addObject(atlas, atlas_name)  # store it in java's object service

        self.atlas = Abba.opened_atlases[atlas_name]
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.z_axis = z_axis
        self.atlas_name = atlas_name

        # Setting logging options
        DebugTools = jimport('loci.common.DebugTools')
        DebugTools.enableLogging(JString(log_level))

        # Ok, let's create abba_python's model: mp = multipositioner

        ABBAStartCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStartCommand')  # Command import

        if print_config:
            self.print_config()

        self.mp = ij.command().run(ABBAStartCommand, True,
                                   'x_axis', self.x_axis,
                                   'y_axis', self.y_axis,
                                   'z_axis', self.z_axis,
                                   'ba', self.atlas
                                   ).get().getOutput('mp')

    def print_config(self) -> None:
        """Prints the Java dependencies and the atlas cache folder"""
        print('- Main Java Dependencies:')
        print(get_java_dependencies())
        print('- Atlas cache folder:')
        print(self.get_atlas_cache_dir())

    def set_atlas_cache_dir(self, atlas_dir: str) -> None:
        """Sets the folder where atlases are downloaded and cached"""
        File = jimport('java.io.File')
        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        AtlasLocationHelper.defaultCacheDir = File(JString(atlas_dir))

    def get_atlas_cache_dir(self) -> str:
        """Folder where atlases are downloaded and cached"""
        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        return str(AtlasLocationHelper.getAtlasCacheDir())

    def get_ij(self) -> Any:
        """
        Provides the ImageJ instance that can be reused to create another Abba instance
        :return:
            the ImageJ instance used by this Abba instance
        """
        return self.ij

    def show_bdv_ui(self, blocking_messages: bool = True) -> None:
        """
        Creates and show a BigDataViewer view over this Abba instance

        :param blocking_messages:
            if False, errors and warnings are shown in the non-blocking BigDataViewer
            overlay instead of modal dialogs, which otherwise block the calling script
            until a user clicks OK (requires a recent ImageToAtlasRegister)
        """
        self.ij.ui().showUI()
        if not hasattr(self, 'bdv_view'):
            # no bdv view properties : creates a new one
            SwingUtilities = jimport('javax.swing.SwingUtilities')
            Runnable = jimport('java.lang.Runnable')

            from jpype import JImplements, JOverride

            # We need to create the view in the Java UI thread
            @JImplements(Runnable)
            class BdvViewGetter:
                def __init__(self, mp: Any) -> None:
                    self.bdv_view: Any = None
                    self.mp = mp

                @JOverride  # type: ignore[untyped-decorator]  # jpype has no types
                def run(self) -> None:
                    DefaultBdvSupplier = jimport('sc.fiji.bdvpg.viewer.bdv.supplier.DefaultBdvSupplier')
                    SerializableBdvOptions = jimport('sc.fiji.bdvpg.viewer.bdv.supplier.SerializableBdvOptions')
                    BdvMultislicePositionerView = jimport(
                        'ch.epfl.biop.atlas.aligner.gui.bdv.BdvMultislicePositionerView')
                    # The theme is normally set by ABBABdvStartCommand, which is bypassed here:
                    # without it, the view overlay fails on every repaint ('null Stroke')
                    ABBABdvViewPrefs = jimport('ch.epfl.biop.atlas.aligner.gui.bdv.ABBABdvViewPrefs')
                    if ABBABdvViewPrefs.line_between_selected_slices_stroke is None:
                        ABBATheme = jimport('ch.epfl.biop.atlas.aligner.gui.bdv.ABBATheme')
                        ABBATheme.setTheme(ABBATheme.createDarkTheme())
                    bdvh = DefaultBdvSupplier(SerializableBdvOptions()).get()
                    self.bdv_view = BdvMultislicePositionerView(self.mp, bdvh)

                def get_bdv_view(self) -> Any:
                    return self.bdv_view

            bdv_view_getter = BdvViewGetter(self.mp)
            SwingUtilities.invokeLater(bdv_view_getter)
            while bdv_view_getter.get_bdv_view() is None:
                time.sleep(0.2)
            self.bdv_view = bdv_view_getter.get_bdv_view()
            if hasattr(self.bdv_view, 'setBlockingMessages'):
                self.bdv_view.setBlockingMessages(blocking_messages)
        else:
            # TODO: make sure it is visible
            pass

    def get_bdv_view(self) -> Any:
        """The BigDataViewer view of this session, once show_bdv_ui has been called"""
        return self.bdv_view

    # ------------------------ IMPORT
    def import_from_files(self, filepaths: Sequence[str | os.PathLike[str]], z_location: float = 0,
                          z_increment: float = 0.02, split_rgb: bool = False) -> Any:
        """

        :param z_location:
            initial location in mm along the atlas cutting axis, as the Z shown in the slice information
            (0 = front of the atlas)
        :param z_increment:
            step in mm between each imported image
        :param split_rgb:
            whether rgb channels should be split in 3 independent RGB channels
            necessary for 16 bits per component RGB images
        :param filepaths:
            file paths of the image to import. Each file should be readable by bio-formats
        :return:
            the import command module, once the command has run
        """
        # Let's import the files using Bio-Formats.
        # The list of all commands is accessible here:
        # https://github.com/BIOP/ijp-imagetoatlas/tree/master/src/main/java/ch/epfl/biop/atlas/aligner/command
        ImportSlicesFromFilesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromFilesCommand')
        File = jimport('java.io.File')

        # Here we want to import images: check
        # https://github.com/BIOP/ijp-imagetoatlas/blob/master/src/main/java/ch/epfl/biop/atlas/aligner/command/ImportImageCommand.java

        FileArray = JArray(File)
        files = FileArray(len(filepaths))
        i = 0
        for filepath in filepaths:
            file = File(os.fspath(filepath))
            files[i] = file
            i = i + 1

        # Any missing input parameter will lead to a popup window asking the missing argument to the user
        return self.ij.command().run(ImportSlicesFromFilesCommand, True,
                                     "mp", self.mp,
                                     "datasetname", JString('dataset'),
                                     "files", files,
                                     "split_rgb_channels", split_rgb,
                                     "first_slice_position_mm", z_location,
                                     "slice_spacing_mm", z_increment
                                     ).get()

    # ------------------------ SLICE SELECTION
    def select_all_slices(self) -> None:
        """Selects all slices"""
        self.mp.selectSlice(self.mp.getSlices())  # select all

    def deselect_all_slices(self) -> None:
        """Deselects all slices"""
        self.mp.deselectSlice(self.mp.getSlices())

    def get_n_slices(self) -> int:
        """Number of slices in the session"""
        return int(self.mp.getSlices().size())

    def select_slices(self, indices: Iterable[int]) -> None:
        """Selects the slices at these indices (0-based, in slice order), in addition to the selected ones"""
        for index in indices:
            self.mp.selectSlice(self.mp.getSlices().get(index))

    def change_display_settings(self, channel_index: int, range_min: float, range_max: float) -> None:
        """Sets the display range of a channel of the selected slices"""
        for abba_slice in self.mp.getSlices():
            if abba_slice.isSelected():
                abba_slice.setDisplayRange(channel_index, range_min, range_max)

    def wait_for_end_of_tasks(self) -> None:
        """Waits until the tasks queued on the slices (registrations...) are done"""
        self.mp.waitForTasks()
