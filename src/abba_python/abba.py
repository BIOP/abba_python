"""Main module."""

# Core
import os

# BrainGlobe
from bg_atlasapi import BrainGlobeAtlas
from bg_atlasapi.list_atlases import get_all_atlases_lastversions, get_downloaded_atlases, get_local_atlas_version
from bg_atlasapi.utils import check_internet_connection

# PyImageJ / Scyjava
from scyjava import jimport
import imagej

# JPype
from jpype.types import JString, JArray


def start_imagej(headless: bool = False):
    mode = "headless"
    if not headless:
        mode = "interactive"
    ij = imagej.init(get_java_dependencies(), mode=mode)
    add_brainglobe_atlases(ij)

    from scyjava import jimport
    from jpype.types import JString

    # loci.common.DebugTools.enableLogging("OFF");
    DebugTools = jimport('loci.common.DebugTools')
    # DebugTools.enableLogging('OFF')
    DebugTools.enableLogging("INFO")
    # DebugTools.enableLogging("DEBUG")

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
            atlasPath = str(directory)
            AtlasLocationHelper.defaultCacheDir = File(JString(atlasPath))
            print('ABBA Atlas cache directory set to ' + directory)
        except OSError:
            print('ERROR! Could not set ABBA Atlas cache dir')
            # directory already exists ?
            pass
    else:
        print('ERROR! ' + platform.system() + ' OS not supported yet.')
    pass

    if not headless:
        ij.ui().showUI()


def get_java_dependencies():
    """
    Returns the jar files that need to be included into the classpath
    of an imagej object in order to have a functional ABBA app
    these jars should be available in https://maven.scijava.org/
    :return:
    """
    imagej_core_dep = 'net.imagej:imagej:2.14.0'
    imagej_legacy_dep = 'net.imagej:imagej-legacy:1.2.1'
    abba_dep = 'ch.epfl.biop:ImageToAtlasRegister:0.7.1'
    return [imagej_core_dep, imagej_legacy_dep, abba_dep]


def add_brainglobe_atlases(ij):
    # TODO : check connection available or not
    try:
        check_internet_connection()
        available_atlases = get_all_atlases_lastversions()
    except ConnectionError:
        available_atlases_nodict = get_downloaded_atlases()
        available_atlases = dict()
        for atlas in available_atlases_nodict:
            print(atlas)
            available_atlases[atlas] = get_local_atlas_version(atlas)

    AtlasChooserCommand = jimport('ch.epfl.biop.atlas.scijava.AtlasChooserCommand')
    try:
        from abba_python.abba_private.AbbaAtlas import AbbaAtlas  # delayed import because the jvm should be set first
    except:
        try:
            from .abba_private.AbbaAtlas import \
                AbbaAtlas  # delayed import because the jvm should be set first
        except:
            print("Could not import AbbaAtlas because the dev do not understand python modules and submodules.")

    from jpype import JImplements, JOverride
    Supplier = jimport('java.util.function.Supplier')

    # initialized

    @JImplements(Supplier)
    class AtlasSupplier(object):

        def __init__(self, atlas_name, ij):
            self.atlas_name = atlas_name
            self.ij = ij

        @JOverride
        def get(self):
            bg_atlas = BrainGlobeAtlas(self.atlas_name)
            current_atlas = AbbaAtlas(bg_atlas, self.ij)
            current_atlas.initialize(None, None)
            Abba.opened_atlases[self.atlas_name] = current_atlas
            return current_atlas

    for atlas_name in available_atlases.keys():
        AtlasChooserCommand.registerAtlas(atlas_name, AtlasSupplier(atlas_name, ij))


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

    slicing_mode :
        should be 'coronal', 'sagittal' or 'horizontal'
        TO IMPROVE : test how well this matches with the BrainGlobe API

    """

    opened_atlases: dict = {}

    def __init__(
        self,
        atlas_name: str = 'Adult Mouse Brain - Allen Brain Atlas V3',
        ij=None,
        slicing_mode: str = 'coronal',  # or sagittal or horizontal
        headless: bool = False
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
            else:
                bg_atlas = BrainGlobeAtlas(atlas_name)

                try:
                    from abba_python.abba_private.AbbaAtlas import \
                        AbbaAtlas  # delayed import because the jvm should be set first
                except:
                    try:
                        from .abba_private.AbbaAtlas import \
                            AbbaAtlas  # delayed import because the jvm should be set first
                    except:
                        print("Could not import AbbaAtlas")

                # initialized
                atlas = AbbaAtlas(bg_atlas, ij)
                atlas.initialize(None, None)
                Abba.opened_atlases[atlas_name] = atlas
                ij.object().addObject(atlas, atlas_name)  # store it in java's object service

        self.atlas = Abba.opened_atlases[atlas_name]
        self.slicing_mode = slicing_mode
        self.atlas_name = atlas_name

        # .. but before : logger, please shut up
        DebugTools = jimport('loci.common.DebugTools')
        DebugTools.enableLogging('OFF')

        # Ok, let's create abba_python's model: mp = multipositioner

        ABBAStartCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStartCommand')  # Command import

        self.mp = ij.command().run(ABBAStartCommand, True,
                                   'slicing_mode', self.slicing_mode,
                                   'ba', self.atlas
                                   ).get().getOutput('mp')

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
            BdvMultislicePositionerView = jimport('ch.epfl.biop.atlas.aligner.gui.bdv.BdvMultislicePositionerView')
            DefaultBdvSupplier = jimport('sc.fiji.bdvpg.bdv.supplier.DefaultBdvSupplier')
            SerializableBdvOptions = jimport('sc.fiji.bdvpg.bdv.supplier.SerializableBdvOptions')
            bdvh = DefaultBdvSupplier(SerializableBdvOptions()).get()
            self.bdv_view = BdvMultislicePositionerView(self.mp, bdvh)
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

    # ------------------------ REGISTRATION

    def register_slices_deep_slice(self,
                                   affine_transform: bool,
                                   allow_change_slicing_position: bool,
                                   allow_slicing_angle_change: bool,
                                   channels: str,
                                   maintain_slices_order: bool,
                                   model: str,
                                   run_mode: str):
        """

        @param affine_transform:
        @param allow_change_slicing_position:
        @param allow_slicing_angle_change:
        @param channels:
        @param maintain_slices_order:
        @param model: rat or mouse
        @param run_mode:
        @return:
        """
        RegisterSlicesDeepSliceCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceCommand, True,
                                     'mp', self.mp,
                                     'affine_transform', affine_transform,
                                     'allow_change_slicing_position', allow_change_slicing_position,
                                     'allow_slicing_angle_change', allow_slicing_angle_change,
                                     'channels', channels,
                                     'maintain_slices_order', maintain_slices_order,
                                     'model', model,
                                     'run_mode', run_mode).get()

    def change_display_settings(self, channel_index: int, range_min: float, range_max: float):
        for abba_slice in self.mp.getSlices():
            if abba_slice.isSelected():
                abba_slice.setDisplayRange(channel_index, range_min, range_max)

    def wait_for_end_of_tasks(self):
        self.mp.waitForTasks()

    # ---------------------- AUTOGENERATED CODE
    def close(self):
        ABBACloseCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACloseCommand')
        return self.ij.command().run(ABBACloseCommand, True,
                                     'mp', self.mp).get()

    def documentation(self):
        ABBADocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBADocumentationCommand')
        return self.ij.command().run(ABBADocumentationCommand, True)

    def forum_help(self):
        ABBAForumHelpCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAForumHelpCommand')
        return self.ij.command().run(ABBAForumHelpCommand, True)

    def open_atlas(self,
                   atlastype: str):
        ABBAOpenAtlasCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAOpenAtlasCommand')
        return self.ij.command().run(ABBAOpenAtlasCommand, True,
                                     'atlasType', atlastype).get()

    def set_bdv_preferences(self):
        ABBASetBDVPreferencesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBASetBDVPreferencesCommand')
        return self.ij.command().run(ABBASetBDVPreferencesCommand, True)

    def state_load(self,
                   state_file):
        ABBAStateLoadCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateLoadCommand')
        return self.ij.command().run(ABBAStateLoadCommand, True,
                                     'mp', self.mp,
                                     'state_file', state_file).get().getOutput('success')

    def state_save(self,
                   state_file):
        ABBAStateSaveCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateSaveCommand')
        return self.ij.command().run(ABBAStateSaveCommand, True,
                                     'mp', self.mp,
                                     'state_file', state_file).get().getOutput('success')

    def user_feedback(self):
        ABBAUserFeedbackCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAUserFeedbackCommand')
        return self.ij.command().run(ABBAUserFeedbackCommand, True)

    def deep_slice_documentation(self):
        DeepSliceDocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.DeepSliceDocumentationCommand')
        return self.ij.command().run(DeepSliceDocumentationCommand, True)

    def export_atlas_to_imagej(self,
                               atlas_channels: str,
                               image_name: str,
                               interpolate: bool,
                               px_size_micron: float):
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
        ExportDeformationFieldToImageJCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportDeformationFieldToImageJCommand')
        return self.ij.command().run(ExportDeformationFieldToImageJCommand, True,
                                     'mp', self.mp,
                                     'downsampling', downsampling,
                                     'max_number_of_iterations', max_number_of_iterations,
                                     'resolution_level', resolution_level).get()

    def export_registration_to_qupath(self,
                                      erase_previous_file: bool):
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
        ExportSlicesOriginalDataToImageJCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportSlicesOriginalDataToImageJCommand')
        return self.ij.command().run(ExportSlicesOriginalDataToImageJCommand, True,
                                     'mp', self.mp,
                                     'channels', channels,
                                     'resolution_level', resolution_level,
                                     'verbose', verbose).get()

    def export_slices_to_bdv(self,
                             tag: str):
        ExportSlicesToBDVCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVCommand')
        return self.ij.command().run(ExportSlicesToBDVCommand, True,
                                     'mp', self.mp,
                                     'tag', tag).get()

    def export_slices_to_bdv_json_dataset(self,
                                          file,
                                          tag: str):
        ExportSlicesToBDVJsonDatasetCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVJsonDatasetCommand')
        return self.ij.command().run(ExportSlicesToBDVJsonDatasetCommand, True,
                                     'mp', self.mp,
                                     'file', file,
                                     'tag', tag).get()

    def export_slices_to_imagej(self,
                                channels: str,
                                image_name: str,
                                interpolate: bool,
                                px_size_micron: float):
        ExportSlicesToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToImageJCommand')
        return self.ij.command().run(ExportSlicesToImageJCommand, True,
                                     'mp', self.mp,
                                     'channels', channels,
                                     'image_name', image_name,
                                     'interpolate', interpolate,
                                     'px_size_micron', px_size_micron).get()

    def export_slices_to_quicknii_dataset(self,
                                          channels: str,
                                          convert_to_8_bits: bool,
                                          convert_to_jpg: bool,
                                          dataset_folder,
                                          image_name: str,
                                          interpolate: bool,
                                          px_size_micron: float):
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

    def import_slice_from_image_plus(self,
                                     image,
                                     slice_axis_mm: float):
        ImportSliceFromImagePlusCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSliceFromImagePlusCommand')
        return self.ij.command().run(ImportSliceFromImagePlusCommand, True,
                                     'mp', self.mp,
                                     'image', image,
                                     'slice_axis_mm', slice_axis_mm).get()

    def import_slices_from_files(self,
                                 datasetname: str,
                                 files,
                                 increment_between_slices_mm: float,
                                 slice_axis_initial_mm: float,
                                 split_rgb_channels: bool):
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
        ImportSlicesFromQuPathCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromQuPathCommand')
        return self.ij.command().run(ImportSlicesFromQuPathCommand, True,
                                     'mp', self.mp,
                                     'increment_between_slices_mm', increment_between_slices_mm,
                                     'qupath_project', qupath_project,
                                     'slice_axis_initial_mm', slice_axis_initial_mm).get()

    def register_slices_bigwarp(self,
                                channel_atlas: int,
                                channel_slice: int):
        RegisterSlicesBigWarpCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesBigWarpCommand')
        return self.ij.command().run(RegisterSlicesBigWarpCommand, True,
                                     'mp', self.mp,
                                     'channel_atlas', channel_atlas,
                                     'channel_slice', channel_slice).get()

    def register_slices_edit_last(self,
                                  atlas_channels_csv: str,
                                  reuse_original_channels: bool,
                                  slices_channels_csv: str):
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
                                       background_offset_value_moving: float = 0,
                                       show_imageplus_registration_result: bool = False):
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
                                       background_offset_value_moving: float = 0,
                                       show_imageplus_registration_result: bool = False):
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
        RegisterSlicesRemoveLastCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesRemoveLastCommand')
        return self.ij.command().run(RegisterSlicesRemoveLastCommand, True,
                                     'mp', self.mp).get()

    def rotate_slices(self,
                      angle_degrees: float,
                      axis_string: str):
        RotateSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.RotateSlicesCommand')
        return self.ij.command().run(RotateSlicesCommand, True,
                                     'mp', self.mp,
                                     'angle_degrees', angle_degrees,
                                     'axis_string', axis_string).get()

    def set_slices_display_range(self,
                                 channels_csv: str,
                                 display_max: float,
                                 display_min: float):
        """

        Parameters
        ----------
        channels_csv
            ch
        display_max
        display_min

        Returns
        -------

        """
        SetSlicesDisplayRangeCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesDisplayRangeCommand')
        return self.ij.command().run(SetSlicesDisplayRangeCommand, True,
                                     'mp', self.mp,
                                     'channels_csv', channels_csv,
                                     'display_max', display_max,
                                     'display_min', display_min).get()

    def set_slices_thickness(self,
                             thickness_in_micrometer: float):
        SetSlicesThicknessCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessCommand')
        return self.ij.command().run(SetSlicesThicknessCommand, True,
                                     'mp', self.mp,
                                     'thickness_in_micrometer', thickness_in_micrometer).get()

    def set_slices_thickness_match_neighbors(self):
        SetSlicesThicknessMatchNeighborsCommand = jimport(
            'ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessMatchNeighborsCommand')
        return self.ij.command().run(SetSlicesThicknessMatchNeighborsCommand, True,
                                     'mp', self.mp).get()
