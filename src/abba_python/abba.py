"""Main module."""

# Core
import os
import time

# PyImageJ / Scyjava
from scyjava import jimport
import imagej

# JPype
from jpype.types import JString, JArray
#
from typing import Literal

LogLevel = Literal['OFF', 'DEBUG', 'INFO']


def get_java_dependencies():
    """
    Returns the jar files that need to be included into the classpath
    of an imagej object in order to have a functional ABBA app
    these jars should be available in https://maven.scijava.org/
    :return:
    """
    return ['ch.epfl.biop:ijl-utilities-wrappers:0.12.1',
            'ch.epfl.biop:ImageToAtlasRegister:0.20.0',
            'ch.epfl.biop:bigdataviewer-biop-tools:0.21.0',
            'sc.fiji:bigdataviewer-playground:0.21.0',
            'sc.fiji.bigdataviewer:bigdataviewer-playground-display:0.20.1',
            'com.formdev:flatlaf:3.5.1',
            'ch.epfl.biop:bigdataviewer-image-loaders:0.21.1',
            'ch.epfl.biop:atlas:0.4.0'
            ]



def start_imagej(headless: bool = False,
                 log_level: LogLevel = 'INFO'):
    mode = "headless"
    if not headless:
        mode = "interactive"
    ij = imagej.init(get_java_dependencies(), mode=mode)

    from scyjava import jimport
    from jpype.types import JString

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
        print('ERROR! ' + platform.system() + ' OS not tested.')
    pass

    if not headless:
        ij.ui().showUI()

    # Adds Python information to ABBA help command
    ABBAForumHelpCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAForumHelpCommand')
    from abba_python import __version__
    python_info = 'ABBA Python ' + str(__version__)
    ABBAForumHelpCommand.pythonInformation = JString(python_info)


class Abba:
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

    opened_atlases: dict = {}

    def __init__(
            self,
            atlas_name: str = 'Adult Mouse Brain - Allen Brain Atlas V3p1',
            ij=None,
            x_axis: str = 'RL',
            y_axis: str = 'SI',
            z_axis: str = 'AP',
            headless: bool = False,
            print_config: bool = True,
            log_level: LogLevel = 'INFO'
    ):
        if ij is None:
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

    def print_config(self):
        # Displays some config information
        print('- Main Java Dependencies:')
        print(get_java_dependencies())
        print('- Atlas cache folder:')
        print(self.get_atlas_cache_dir())

    def set_atlas_cache_dir(self, atlas_dir: str):
        File = jimport('java.io.File')
        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        AtlasLocationHelper.defaultCacheDir = File(JString(atlas_dir))

    def get_atlas_cache_dir(self) -> str:
        AtlasLocationHelper = jimport('ch.epfl.biop.atlas.AtlasLocationHelper')
        return str(AtlasLocationHelper.getAtlasCacheDir())

    def get_ij(self):
        """
        Provides the ImageJ instance that can be reused to create another Abba instance
        :return:
            the ImageJ instance used by this Abba instance
        """
        return self.ij

    def show_bdv_ui(self):
        self.ij.ui().showUI()
        """
        Creates and show a BigDataViewer view over this Abba instance
        """
        if not hasattr(self, 'bdv_view'):
            # no bdv view properties : creates a new one
            SwingUtilities = jimport('javax.swing.SwingUtilities')
            Runnable = jimport('java.lang.Runnable')

            from jpype import JImplements, JOverride

            # We need to create the view in the Java UI thread
            @JImplements(Runnable)
            class BdvViewGetter:
                def __init__(self, mp):
                    self.bdv_view = None
                    self.mp = mp

                @JOverride
                def run(self):
                    DefaultBdvSupplier = jimport('sc.fiji.bdvpg.viewer.bdv.supplier.DefaultBdvSupplier')
                    SerializableBdvOptions = jimport('sc.fiji.bdvpg.viewer.bdv.supplier.SerializableBdvOptions')
                    BdvMultislicePositionerView = jimport(
                        'ch.epfl.biop.atlas.aligner.gui.bdv.BdvMultislicePositionerView')
                    bdvh = DefaultBdvSupplier(SerializableBdvOptions()).get()
                    self.bdv_view = BdvMultislicePositionerView(self.mp, bdvh)

                def get_bdv_view(self):
                    return self.bdv_view

            bdv_view_getter = BdvViewGetter(self.mp)
            SwingUtilities.invokeLater(bdv_view_getter)
            while bdv_view_getter.get_bdv_view() is None:
                time.sleep(0.2)
            self.bdv_view = bdv_view_getter.get_bdv_view()
        else:
            # TODO: make sure it is visible
            pass

    def get_bdv_view(self):
        return self.bdv_view

    # ------------------------ IMPORT
    def import_from_files(self, filepaths, z_location=0, z_increment=0.02, split_rgb=False):
        """

        :param z_location:
            initial location in mm along the atlas cutting axis
        :param z_increment:
            step in mm between each imported image
        :param split_rgb:
            whether rgb channels should be split in 3 independent RGB channels
            necessary for 16 bits per component RGB images
        :param filepaths:
            file paths of the image to import. Each file should be readable by bio-formats
        :return:
            a Future object: if you call .get(), the request will wait to be finished. If not, the import
            files command is executed asynchronously
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
            file = File(filepath)
            files[i] = file
            i = i + 1

        # Any missing input parameter will lead to a popup window asking the missing argument to the user
        return self.ij.command().run(ImportSlicesFromFilesCommand, True,
                                     "mp", self.mp,
                                     "datasetname", JString('dataset'),
                                     "files", files,
                                     "split_rgb_channels", split_rgb,
                                     "slice_axis_initial_mm", z_location,
                                     "increment_between_slices_mm", z_increment
                                     ).get()

    # ------------------------ SLICE SELECTION
    def select_all_slices(self):
        self.mp.selectSlice(self.mp.getSlices())  # select all

    def deselect_all_slices(self):
        self.mp.deselectSlice(self.mp.getSlices())  # select all

    def get_n_slices(self):
        return self.mp.getSlices().size()

    def select_slices(self, indices):
        for index in indices:
            self.mp.selectSlice(self.mp.getSlices().get(index))  # select the last slice

    def change_display_settings(self, channel_index: int, range_min: float, range_max: float):
        for abba_slice in self.mp.getSlices():
            if abba_slice.isSelected():
                abba_slice.setDisplayRange(channel_index, range_min, range_max)

    def wait_for_end_of_tasks(self):
        self.mp.waitForTasks()

    # ---------------------- AUTOGENERATED CODE with the main method from ScijavaCommandToPython
    def benchmark(self,
                   comment: str,
                   demo_dataset: str,
                   use_gui: bool,
                   wait_between_each_step: bool):
        """
        Complete ABBA process in a benchmark

        Parameters:
        comment (str):
        demo_dataset (str):
        use_gui (bool): Use graphical user interface
        wait_between_each_step (bool):
        """
        ABBABenchMarkCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBABenchMarkCommand')
        return self.ij.command().run(ABBABenchMarkCommand, True,
                                     'comment', comment,
                                     'demo_dataset', demo_dataset,
                                     'use_gui', use_gui,
                                     'wait_between_each_step', wait_between_each_step).get()

    def check_for_update(self):
        """
        Check for updates

        """
        ABBACheckForUpdateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACheckForUpdateCommand')
        return self.ij.command().run(ABBACheckForUpdateCommand, True)

    def cite_info(self):
        """
        How to cite

        """
        ABBACiteInfoCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACiteInfoCommand')
        return self.ij.command().run(ABBACiteInfoCommand, True)

    def close(self):
        """
        Close ABBA session

        """
        ABBACloseCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACloseCommand')
        return self.ij.command().run(ABBACloseCommand, True,
                                     'mp', self.mp).get()

    def documentation(self):
        """
        Open ABBA documentation webpage.

        """
        ABBADocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBADocumentationCommand')
        return self.ij.command().run(ABBADocumentationCommand, True)

    def forum_help(self):
        """
        Open a new post in the image.sc forum with current install information

        """
        ABBAForumHelpCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAForumHelpCommand')
        return self.ij.command().run(ABBAForumHelpCommand, True)


    def generate_methods_prompt(self):
        """
        Outputs a summary of methods used for the registration. Can be copy pasted in the llm of your choice.

        """
        ABBAGenerateMethodsPrompt = jimport('ch.epfl.biop.atlas.aligner.command.ABBAGenerateMethodsPrompt')
        return self.ij.command().run(ABBAGenerateMethodsPrompt, True,
                                     'mp', self.mp).get()


    def set_bdv_preferences(self):
        """
        Sets actions linked to key / mouse event in ABBA (not functional)

        """
        ABBASetBDVPreferencesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBASetBDVPreferencesCommand')
        return self.ij.command().run(ABBASetBDVPreferencesCommand, True)


    def start_log(self):
        """
        Close ABBA session

        """
        ABBAStartLogCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStartLogCommand')
        return self.ij.command().run(ABBAStartLogCommand, True,
                                     'mp', self.mp).get()


    def state_load(self,
                   state_file):
        """
        Loads a previous registration state into ABBA

        Parameters:
        state_file :
        """
        ABBAStateLoadCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateLoadCommand')
        return self.ij.command().run(ABBAStateLoadCommand, True,
                                     'mp', self.mp,
                                     'state_file', state_file).get().getOutput('success')

    def state_save(self,
                   state_file):
        """
        Saves the current registration state

        Parameters:
        state_file :
        """
        ABBAStateSaveCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateSaveCommand')
        return self.ij.command().run(ABBAStateSaveCommand, True,
                                     'mp', self.mp,
                                     'state_file', state_file).get().getOutput('success')

    def user_feedback(self):
        """
        Open an ABBA feedback form

        """
        ABBAUserFeedbackCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAUserFeedbackCommand')
        return self.ij.command().run(ABBAUserFeedbackCommand, True)

    def deepslice_documentation(self):
        """
        Open deep slice reference webpage.

        """
        DeepSliceDocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.DeepSliceDocumentationCommand')
        return self.ij.command().run(DeepSliceDocumentationCommand, True)

    def export_atlas_to_imagej(self,
                               atlas_channels: str,
                               image_name: str,
                               interpolate: bool,
                               px_size_micron: float):
        """
        Export atlas properties as an ImageJ stack (for each selected slice).

        Parameters:
        atlas_channels (str): Channels to export, '*' for all channels
        image_name (str): Exported image name
        interpolate (bool):
        px_size_micron (float): Pixel Size in micron
        """
        ExportAtlasToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportAtlasToImageJCommand')
        return self.ij.command().run(ExportAtlasToImageJCommand, True,
                                     'mp', self.mp,
                                     'atlas_channels', atlas_channels,
                                     'image_name', image_name,
                                     'interpolate', interpolate,
                                     'px_size_micron', px_size_micron).get()

    def export_deformation_field_to_imagej(self,
                                           downsampling: int,
                                           max_number_of_iterations: int,
                                           resolution_level: int):
        """
        Exports physical coordinates of the atlas in a 3 channel (x,y,z) image that matches pixels of the initial unregistered slice (for each selected slice). Resolution levels can be specified.

        Parameters:
        downsampling (int): Extra DownSampling
        max_number_of_iterations (int): Max iterations in invertible transform computation (default 200)
        resolution_level (int): Resolution level (0 = max resolution)
        """
        ExportDeformationFieldToImageJCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportDeformationFieldToImageJCommand')
        return self.ij.command().run(ExportDeformationFieldToImageJCommand, True,
                                     'mp', self.mp,
                                     'downsampling', downsampling,
                                     'max_number_of_iterations', max_number_of_iterations,
                                     'resolution_level', resolution_level).get()

    def export_registration_to_qupath(self,
                                      erase_previous_file: bool):
        """
        Export atlas regions and transformations to QuPath project (for each selected slice)

        Parameters:
        erase_previous_file (bool): Erase Previous ROIs
        """
        ExportRegistrationToQuPathCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportRegistrationToQuPathCommand')
        return self.ij.command().run(ExportRegistrationToQuPathCommand, True,
                                     'mp', self.mp,
                                     'erase_previous_file', erase_previous_file).get()

    def export_resampled_slices_to_bdv_source(self,
                                              block_size_x: int,
                                              block_size_y: int,
                                              block_size_z: int,
                                              channels: str,
                                              downsample_x: int,
                                              downsample_y: int,
                                              downsample_z: int,
                                              image_name: str,
                                              interpolate: bool,
                                              margin_z: float,
                                              n_threads: int,
                                              px_size_micron_x: float,
                                              px_size_micron_y: float,
                                              px_size_micron_z: float,
                                              resolution_levels: int):
        """
        Export registered (deformed) slices in the atlas coordinates. A pixel size should be specified to resample the registered images.

        Parameters:
        block_size_x (int): Block Size X
        block_size_y (int): Block Size Y
        block_size_z (int): Block Size Z
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        downsample_x (int): X downsampling
        downsample_y (int): Y downsampling
        downsample_z (int): Z downsampling
        image_name (str): Exported source name
        interpolate (bool):
        margin_z (float): Margin in Z in micron
        n_threads (int): Number of threads
        px_size_micron_x (float): Pixel Size in micron (X)
        px_size_micron_y (float): Pixel Size in micron (Y)
        px_size_micron_z (float): Pixel Size in micron (Z)
        resolution_levels (int): Number of resolution levels (min 1)
        """
        ExportResampledSlicesToBDVSourceCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportResampledSlicesToBDVSourceCommand')
        return self.ij.command().run(ExportResampledSlicesToBDVSourceCommand, True,
                                     'mp', self.mp,
                                     'block_size_x', block_size_x,
                                     'block_size_y', block_size_y,
                                     'block_size_z', block_size_z,
                                     'channels', channels,
                                     'downsample_x', downsample_x,
                                     'downsample_y', downsample_y,
                                     'downsample_z', downsample_z,
                                     'image_name', image_name,
                                     'interpolate', interpolate,
                                     'margin_z', margin_z,
                                     'n_threads', n_threads,
                                     'px_size_micron_x', px_size_micron_x,
                                     'px_size_micron_y', px_size_micron_y,
                                     'px_size_micron_z', px_size_micron_z,
                                     'resolution_levels', resolution_levels).get()

    def export_slices_original_data_to_imagej(self,
                                              channels: str,
                                              resolution_level: int,
                                              verbose: bool):
        """
        Export to ImageJ the original unregistered slice data (for each selected slice).If the image has more than 2GPixels, this will fail. Resolution levels can be specified.

        Parameters:
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        resolution_level (int): Resolution level (0 = max resolution)
        verbose (bool): verbose
        """
        ExportSlicesOriginalDataToImageJCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportSlicesOriginalDataToImageJCommand')
        return self.ij.command().run(ExportSlicesOriginalDataToImageJCommand, True,
                                     'mp', self.mp,
                                     'channels', channels,
                                     'resolution_level', resolution_level,
                                     'verbose', verbose).get()

    def export_slices_to_bdv(self,
                             tag: str):
        """
        Export registered slices to a BigDataViewer window.

        Parameters:
        tag (str): Enter a tag to identify the registered sources (metadata key = "ABBA")
        """
        ExportSlicesToBDVCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVCommand')
        return self.ij.command().run(ExportSlicesToBDVCommand, True,
                                     'mp', self.mp,
                                     'tag', tag).get()

    def export_slices_to_bdv_json_dataset(self,
                                          file,
                                          tag: str):
        """
        Export registered slices as a BigDataViewer json dataset (very experimental).

        Parameters:
        file : Please specify a json file to store the reconstructed data
        tag (str): Enter a tag to identify the registered sources (metadata key = "ABBA")
        """
        ExportSlicesToBDVJsonDatasetCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVJsonDatasetCommand')
        return self.ij.command().run(ExportSlicesToBDVJsonDatasetCommand, True,
                                     'mp', self.mp,
                                     'file', file,
                                     'tag', tag).get()

    def export_slices_to_quicknii_dataset(self,
                                          channels: str,
                                          convert_to_8_bits: bool,
                                          convert_to_jpg: bool,
                                          dataset_folder,
                                          image_name: str,
                                          interpolate: bool,
                                          px_size_micron: float):
        """


        Parameters:
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        convert_to_8_bits (bool): Convert to 8 bit image
        convert_to_jpg (bool): Convert to jpg (single channel recommended)
        dataset_folder : QuickNII dataset export folder
        image_name (str): Section Name Prefix
        interpolate (bool):
        px_size_micron (float): Pixel Size in micron
        """
        ExportSlicesToQuickNIIDatasetCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportSlicesToQuickNIIDatasetCommand')
        return self.ij.command().run(ExportSlicesToQuickNIIDatasetCommand, True,
                                     'mp', self.mp,
                                     'channels', channels,
                                     'convert_to_8_bits', convert_to_8_bits,
                                     'convert_to_jpg', convert_to_jpg,
                                     'dataset_folder', dataset_folder,
                                     'image_name', image_name,
                                     'interpolate', interpolate,
                                     'px_size_micron', px_size_micron).get()


    def export_std_zip_state(self,
                             ba,
                             channels: str,
                             coronal,
                             downscale_deformation_field: int,
                             experiment_information: str,
                             horizontal,
                             identifier: str,
                             sagittal,
                             save_path,
                             state_file,
                             target_resolution_micrometer: float,
                             x_axis: str,
                             y_axis: str,
                             z_axis: str):
        """
        Takes a full project and store a downscaled version of the dataset for sharing

        Parameters:
        ba :
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        coronal :
        downscale_deformation_field (int):
        experiment_information (str):
        horizontal :
        identifier (str):
        sagittal :
        save_path :
        state_file :
        target_resolution_micrometer (float):
        x_axis (str):
        y_axis (str):
        z_axis (str):
        """
        ExportStdZipStateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportStdZipStateCommand')
        return self.ij.command().run(ExportStdZipStateCommand, True,
                                     'ba', ba,
                                     'channels', channels,
                                     'coronal', coronal,
                                     'downscale_deformation_field', downscale_deformation_field,
                                     'experiment_information', experiment_information,
                                     'horizontal', horizontal,
                                     'identifier', identifier,
                                     'sagittal', sagittal,
                                     'save_path', save_path,
                                     'state_file', state_file,
                                     'target_resolution_micrometer', target_resolution_micrometer,
                                     'x_axis', x_axis,
                                     'y_axis', y_axis,
                                     'z_axis', z_axis).get()


    def export_transformed_atlas_to_imagej(self,
                                           atlas_channels: str,
                                           downsampling: int,
                                           max_number_of_iterations: int,
                                           resolution_level: int):
        """
        Exports physical coordinates of the atlas in a 3 channel (x,y,z) image that matches pixels of the initial unregistered slice (for each selected slice). Resolution levels can be specified.

        Parameters:
        atlas_channels (str): Channels to export, '*' for all channels
        downsampling (int): Extra DownSampling
        max_number_of_iterations (int): Max iterations in invertible transform computation (default 200)
        resolution_level (int): Resolution level (0 = max resolution)
        """
        ExportTransformedAtlasToImageJCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportTransformedAtlasToImageJCommand')
        return self.ij.command().run(ExportTransformedAtlasToImageJCommand, True,
                                     'mp', self.mp,
                                     'atlas_channels', atlas_channels,
                                     'downsampling', downsampling,
                                     'max_number_of_iterations', max_number_of_iterations,
                                     'resolution_level', resolution_level).get()


    def import_demo_slices_omero(self,
                                     demo_dataset: str,
                                     project_directory):
        """
        Open a set of demo brain sections

        Parameters:
        demo_dataset (str): Choose the number of sections to import
        project_directory : Target directory for QuPath project (not required)
        """
        ImportDemoSlicesOMEROCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportDemoSlicesOMEROCommand')
        return self.ij.command().run(ImportDemoSlicesOMEROCommand, True,
                                     'mp', self.mp,
                                     'demo_dataset', demo_dataset,
                                     'project_directory', project_directory).get()


    def import_demo_slices_zenodo(self,
                                       number_of_slides: int):
        """
        Open a set of demo brain sections

        Parameters:
        number_of_slides (int): Number of slides to use (7 max)
        """
        ImportDemoSlicesZENODOCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportDemoSlicesZENODOCommand')
        return self.ij.command().run(ImportDemoSlicesZENODOCommand, True,
                                     'mp', self.mp,
                                     'number_of_slides', number_of_slides).get()


    def import_slice_from_image_plus(self,
                                     image,
                                     slice_axis_mm: float):
        """
        Import the current ImageJ image as a slice into ABBA

        Parameters:
        image :
        slice_axis_mm (float): Initial axis position (0 = front, mm units)
        """
        ImportSliceFromImagePlusCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSliceFromImagePlusCommand')
        return self.ij.command().run(ImportSliceFromImagePlusCommand, True,
                                     'mp', self.mp,
                                     'image', image,
                                     'slice_axis_mm', slice_axis_mm).get()

    def import_slice_from_sources(self,
                                  slice_axis_mm: float,
                                  sources):
        """
        Import a list of sources as a slice into ABBA

        Parameters:
        slice_axis_mm (float): Initial axis position (0 = front, mm units)
        sources :
        """
        ImportSliceFromSourcesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSliceFromSourcesCommand')
        return self.ij.command().run(ImportSliceFromSourcesCommand, True,
                                     'mp', self.mp,
                                     'slice_axis_mm', slice_axis_mm,
                                     'sources', sources).get()

    def import_slices_from_files(self,
                                 datasetname: str,
                                 files,
                                 increment_between_slices_mm: float,
                                 slice_axis_initial_mm: float,
                                 split_rgb_channels: bool):
        """
        Import a Bio-Formats compatible file as brain slices

        Parameters:
        datasetname (str): Dataset Name
        files : Files to import
        increment_between_slices_mm (float): Axis increment between slices (mm, can be negative for reverse order)
        slice_axis_initial_mm (float): Initial axis position (0 = front, mm units)
        split_rgb_channels (bool): Split RGB channels
        """
        ImportSlicesFromFilesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromFilesCommand')
        return self.ij.command().run(ImportSlicesFromFilesCommand, True,
                                     'mp', self.mp,
                                     'datasetname', datasetname,
                                     'files', files,
                                     'increment_between_slices_mm', increment_between_slices_mm,
                                     'slice_axis_initial_mm', slice_axis_initial_mm,
                                     'split_rgb_channels', split_rgb_channels).get()

    def import_slices_from_qupath(self,
                                  increment_between_slices_mm: float,
                                  qupath_project,
                                  slice_axis_initial_mm: float):
        """
        Import images of a QuPath project as slices into ABBA

        Parameters:
        increment_between_slices_mm (float): Axis increment between slices (mm, can be negative for reverse order)
        qupath_project : QuPath project file (.qpproj)
        slice_axis_initial_mm (float): Initial axis position (0 = front, mm units)
        """
        ImportSlicesFromQuPathCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromQuPathCommand')
        return self.ij.command().run(ImportSlicesFromQuPathCommand, True,
                                     'mp', self.mp,
                                     'increment_between_slices_mm', increment_between_slices_mm,
                                     'qupath_project', qupath_project,
                                     'slice_axis_initial_mm', slice_axis_initial_mm).get()


    def import_slices_from_quicknii(self,
                                    quicknii_project,
                                    split_rgb_channels: bool):
        """
        Import images of a QuickNII Project as slices into ABBA

        Parameters:
        quicknii_project : QuickNII file (.json)
        split_rgb_channels (bool): Split RGB channels
        """
        ImportSlicesFromQuickNIICommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromQuickNIICommand')
        return self.ij.command().run(ImportSlicesFromQuickNIICommand, True,
                                     'mp', self.mp,
                                     'quicknii_project', quicknii_project,
                                     'split_rgb_channels', split_rgb_channels).get()


    def import_std_zip_state(self,
                             zip_file):
        """
        Opens a previously created zipped ABBA project.

        Parameters:
        zip_file :
        """
        ImportStdZipStateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportStdZipStateCommand')
        return self.ij.command().run(ImportStdZipStateCommand, True,
                                     'zip_file', zip_file).get()


    def mirror_do(self,
                  mirror_side: str):
        """
        Mirror a half section to create the other side.

        Parameters:
        mirror_side (str):
        """
        MirrorDoCommand = jimport('ch.epfl.biop.atlas.aligner.command.MirrorDoCommand')
        return self.ij.command().run(MirrorDoCommand, True,
                                     'mp', self.mp,
                                     'mirror_side', mirror_side).get()

    def mirror_undo(self):
        """
        Remove slice mirroring.

        """
        MirrorUndoCommand = jimport('ch.epfl.biop.atlas.aligner.command.MirrorUndoCommand')
        return self.ij.command().run(MirrorUndoCommand, True,
                                     'mp', self.mp).get()

    def raster_slices(self,
                      interpolate: bool,
                      pixel_size_micrometer: float):
        """
        Speed up the display of slices by precomputing and caching their pixel.

        Parameters:
        interpolate (bool): Interpolate
        pixel_size_micrometer (float): Pixel size (micrometer)
        """
        RasterSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.RasterSlicesCommand')
        return self.ij.command().run(RasterSlicesCommand, True,
                                     'mp', self.mp,
                                     'interpolate', interpolate,
                                     'pixel_size_micrometer', pixel_size_micrometer).get()

    def raster_slices_deformation(self,
                                  grid_spacing_in_micrometer: float):
        """
        Speed up the display of slices by precomputing and caching their deformation field (useful after spline registrations only!).

        Parameters:
        grid_spacing_in_micrometer (float): Deformation grid size (micrometer)
        """
        RasterSlicesDeformationCommand = jimport('ch.epfl.biop.atlas.aligner.command.RasterSlicesDeformationCommand')
        return self.ij.command().run(RasterSlicesDeformationCommand, True,
                                     'mp', self.mp,
                                     'grid_spacing_in_micrometer', grid_spacing_in_micrometer).get()

    def register_slices_bigwarp(self,
                                channels_atlas_csv: str,
                                channels_slice_csv: str):
        """
        Uses BigWarp for in plane registration of selected slices

        Parameters:
        channels_atlas_csv (str): Atlas channels (channels comma separated)
        channels_slice_csv (str): Slices channels (channels comma separated)
        """
        RegisterSlicesBigWarpCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesBigWarpCommand')
        return self.ij.command().run(RegisterSlicesBigWarpCommand, True,
                                     'mp', self.mp,
                                     'channels_atlas_csv', channels_atlas_csv,
                                     'channels_slice_csv', channels_slice_csv).get()

    def register_slices_copy_and_apply(self,
                                       model_slice_index: int,
                                       skip_pre_transform: bool):
        """
        Copy the registration sequence of a slice and apply it to selected slices

        Parameters:
        model_slice_index (int): Index of the slice registrations you'd like to copy
        skip_pre_transform (bool): Tick if you want to skip the pre-transform (probably not)
        """
        RegisterSlicesCopyAndApplyCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.RegisterSlicesCopyAndApplyCommand')
        return self.ij.command().run(RegisterSlicesCopyAndApplyCommand, True,
                                     'mp', self.mp,
                                     'model_slice_index', model_slice_index,
                                     'skip_pre_transform', skip_pre_transform).get()

    def register_slices_deepslice(self,
                                         allow_slicing_angle_change: bool,
                                         channels: str,
                                         ensemble: bool,
                                         model: str,
                                         post_processing: str,
                                         px_size_micron: float,
                                         slices_spacing_micrometer: float):
        """
        Uses Deepslice for affine in plane and axial registration of selected slices

        Parameters:
        allow_slicing_angle_change (bool): Allow change of atlas slicing angle
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        ensemble (bool): Average of several models (slower)
        model (str): ('mouse', 'rat') Mouse or Rat ?
        post_processing (str):
        px_size_micron (float): Resampling pixel size (10 for mouse, 40 for rat)
        slices_spacing_micrometer (float): Spacing (micrometer), used only when 'Keep order + set spacing' is selected
        """
        RegisterSlicesDeepSliceApposeCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceApposeCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceApposeCommand, True,
                                     'mp', self.mp,
                                     'allow_slicing_angle_change', allow_slicing_angle_change,
                                     'channels', channels,
                                     'ensemble', ensemble,
                                     'model', model,
                                     'post_processing', post_processing,
                                     'px_size_micron', px_size_micron,
                                     'slices_spacing_micrometer', slices_spacing_micrometer).get()

    def register_slices_deepslice_web(self,
                                      allow_slicing_angle_change: bool,
                                      channels: str,
                                      maintain_slices_order: bool,
                                      model: str,
                                      px_size_micron: float):
        """
        Uses Deepslice for affine in plane and axial registration of selected slices

        Parameters:
        allow_slicing_angle_change (bool): Allow change of atlas slicing angle
        channels (str): Slices channels, 0-based, comma separated, '*' for all channels
        maintain_slices_order (bool): Keep slices order
        model (str): ('mouse', 'rat') Mouse or Rat ?
        px_size_micron (float): Resampling pixel size (10 for mouse, 40 for rat)
        """
        RegisterSlicesDeepSliceWebCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceWebCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceWebCommand, True,
                                     'mp', self.mp,
                                     'allow_slicing_angle_change', allow_slicing_angle_change,
                                     'channels', channels,
                                     'maintain_slices_order', maintain_slices_order,
                                     'model', model,
                                     'px_size_micron', px_size_micron).get()

    def register_slices_edit_last(self,
                                  atlas_channels_csv: str,
                                  reuse_original_channels: bool,
                                  slices_channels_csv: str):
        """
        Edit the last registration of the current selected slices, if possible.

        Parameters:
        atlas_channels_csv (str): Atlas channels, 0-based, comma separated, '*' for all channels
        reuse_original_channels (bool): Reuse original channels of the registration
        slices_channels_csv (str): Slices channels, 0-based, comma separated, '*' for all channels
        """
        RegisterSlicesEditLastCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesEditLastCommand')
        return self.ij.command().run(RegisterSlicesEditLastCommand, True,
                                     'mp', self.mp,
                                     'atlas_channels_csv', atlas_channels_csv,
                                     'reuse_original_channels', reuse_original_channels,
                                     'slices_channels_csv', slices_channels_csv).get()

    def register_slices_elastix_affine(self,
                                       channels_atlas_csv: str,
                                       channels_slice_csv: str,
                                       pixel_size_micrometer: float,
                                       show_imageplus_registration_result: bool = False,
                                       background_offset_value_moving: float = 0, ):
        """
        Uses Elastix for affine in plane registration of selected slices

        Parameters:
        background_offset_value_moving (float): Background offset value
        channels_atlas_csv (str): Atlas channels (channels comma separated)
        channels_slice_csv (str): Slices channels (channels comma separated)
        pixel_size_micrometer (float): Registration re-sampling (micrometers)
        show_imageplus_registration_result (bool): Show registration results as ImagePlus
        """
        RegisterSlicesElastixAffineCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixAffineCommand')
        return self.ij.command().run(RegisterSlicesElastixAffineCommand, True,
                                     'mp', self.mp,
                                     'background_offset_value_moving', background_offset_value_moving,
                                     'channels_atlas_csv', channels_atlas_csv,
                                     'channels_slice_csv', channels_slice_csv,
                                     'pixel_size_micrometer', pixel_size_micrometer,
                                     'show_imageplus_registration_result', show_imageplus_registration_result).get()

    def register_slices_elastix_spline(self,
                                       channels_atlas_csv: str,
                                       channels_slice_csv: str,
                                       nb_control_points_x: int,
                                       pixel_size_micrometer: float,
                                       show_imageplus_registration_result: bool = False,
                                       background_offset_value_moving: float = 0, ):
        """
        Uses Elastix for spline in plane registration of selected slices

        Parameters:
        background_offset_value_moving (float): Background offset value
        channels_atlas_csv (str): Atlas channels (channels comma separated)
        channels_slice_csv (str): Slices channels (channels comma separated)
        nb_control_points_x (int): Number of control points along X, minimum 2.
        pixel_size_micrometer (float): Registration re-sampling (micrometers)
        show_imageplus_registration_result (bool): Show registration results as ImagePlus
        """
        RegisterSlicesElastixSplineCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixSplineCommand')
        return self.ij.command().run(RegisterSlicesElastixSplineCommand, True,
                                     'mp', self.mp,
                                     'background_offset_value_moving', background_offset_value_moving,
                                     'channels_atlas_csv', channels_atlas_csv,
                                     'channels_slice_csv', channels_slice_csv,
                                     'nb_control_points_x', nb_control_points_x,
                                     'pixel_size_micrometer', pixel_size_micrometer,
                                     'show_imageplus_registration_result', show_imageplus_registration_result).get()

    def register_slices_remove_last(self):
        """
        Remove the last registration of the current selected slices, if possible.

        """
        RegisterSlicesRemoveLastCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesRemoveLastCommand')
        return self.ij.command().run(RegisterSlicesRemoveLastCommand, True,
                                     'mp', self.mp).get()


    def reindex_slices(self,
                       new_indices: str):
        """
        Creates a new slice with reindexed channels.

        Parameters:
        new_indices (str): New indices in csv
        """
        ReindexSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ReindexSlicesCommand')
        return self.ij.command().run(ReindexSlicesCommand, True,
                                     'mp', self.mp,
                                     'new_indices', new_indices).get()


    def rotate_slices(self,
                      angle_degrees: float,
                      axis_string: str):
        """
        To use at the beginning of the registration process only! Rotates the original unregistered selected slices

        Parameters:
        angle_degrees (float): Angle (degrees)
        axis_string (str): Rotation axis
        """
        RotateSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.RotateSlicesCommand')
        return self.ij.command().run(RotateSlicesCommand, True,
                                     'mp', self.mp,
                                     'angle_degrees', angle_degrees,
                                     'axis_string', axis_string).get()


    def set_slices_background(self,
                              white_background_value: int):
        """
        Allow to work with white background images.

        Parameters:
        white_background_value (int): White value (8-bit or rgb: 255, 16-bit:65535)
        """
        SetSlicesBackgroundCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesBackgroundCommand')
        return self.ij.command().run(SetSlicesBackgroundCommand, True,
                                     'mp', self.mp,
                                     'white_background_value', white_background_value).get()


    def set_slices_deselected(self,
                              slices_csv: str):
        """
        Set the slices to deselect.

        Parameters:
        slices_csv (str): Slices to deselect, '*' for all slices, comma separated, 0-based
        """
        SetSlicesDeselectedCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesDeselectedCommand')
        return self.ij.command().run(SetSlicesDeselectedCommand, True,
                                     'mp', self.mp,
                                     'slices_csv', slices_csv).get()

    def set_slices_display_range(self,
                                 channels_csv: str,
                                 display_max: float,
                                 display_min: float):
        """
        Change min max displayed value (for each selected slice).

        Parameters:
        channels_csv (str): Channels to adjust, '*' for all channels, comma separated, 0-based
        display_max (float): Max displayed valued
        display_min (float): Min displayed valued
        """
        SetSlicesDisplayRangeCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesDisplayRangeCommand')
        return self.ij.command().run(SetSlicesDisplayRangeCommand, True,
                                     'mp', self.mp,
                                     'channels_csv', channels_csv,
                                     'display_max', display_max,
                                     'display_min', display_min).get()

    def set_slices_selected(self,
                            slices_csv: str):
        """
        Set the slices to select.

        Parameters:
        slices_csv (str): Slices to select, '*' for all slices, comma separated, 0-based
        """
        SetSlicesSelectedCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesSelectedCommand')
        return self.ij.command().run(SetSlicesSelectedCommand, True,
                                     'mp', self.mp,
                                     'slices_csv', slices_csv).get()

    def set_slices_thickness(self,
                             thickness_in_micrometer: float):
        """
        Set the selected slices thickness - useful for a fully reconstructed brain display.

        Parameters:
        thickness_in_micrometer (float): Slice thickness in micrometer
        """
        SetSlicesThicknessCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessCommand')
        return self.ij.command().run(SetSlicesThicknessCommand, True,
                                     'mp', self.mp,
                                     'thickness_in_micrometer', thickness_in_micrometer).get()

    def set_slices_thickness_match_neighbors(self):
        """
        Modifies the selected slices thickness in such a way that no space is left between slices. This is visible only in the reconstructed volume in BigDataViewer

        """
        SetSlicesThicknessMatchNeighborsCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessMatchNeighborsCommand')
        return self.ij.command().run(SetSlicesThicknessMatchNeighborsCommand, True,
                                     'mp', self.mp).get()
