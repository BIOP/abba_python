"""Main module."""

# Core
import json
import os
import time

# PyImageJ / Scyjava
import scyjava
from scyjava import jimport
import imagej

# JPype
from jpype.types import JString, JArray
#
from typing import Any, Literal, Optional, Sequence

LogLevel = Literal['OFF', 'DEBUG', 'INFO']


def get_java_dependencies():
    """
    Returns the jar files that need to be included into the classpath
    of an imagej object in order to have a functional ABBA app
    these jars should be available in https://maven.scijava.org/
    :return:
    """
    return ['ch.epfl.biop:ijl-utilities-wrappers:0.12.1',
            'ch.epfl.biop:ImageToAtlasRegister:0.23.1-SNAPSHOT',
            'ch.epfl.biop:bigdataviewer-biop-tools:0.24.0',
            'sc.fiji:bigdataviewer-playground:0.23.1',
            'sc.fiji.bigdataviewer:bigdataviewer-playground-display:0.23.1',
            'com.formdev:flatlaf:3.5.1',
            'ch.epfl.biop:bigdataviewer-image-loaders:0.23.2',
            'ch.epfl.biop:atlas:0.23.2'
            ]


# Java version the jars of get_java_dependencies() are compiled for
JAVA_VERSION = '21'


def configure_java():
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
                 log_level: LogLevel = 'INFO'):
    mode = "headless"
    if not headless:
        mode = "interactive"
    configure_java()
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
        print('[WARNING] Support for third-party brain atlases through BrainGlobe is primarily tested on Windows. If you encounter any OS-specific issues on ' + platform.system() + ', please report them to the developers: https://github.com/BIOP/abba_python/issues')
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

        # Collects ABBA's error, warning and info messages, see get_messages
        self._messages: list = []
        self._subscribe_to_messages()
        # userActionsSize() after each batch created by apply / delete_slices (see undo)
        self._undoable_batches: list = []
        self._redoable_batches: list = []

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

    def show_bdv_ui(self, blocking_messages: bool = True):
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
                def __init__(self, mp):
                    self.bdv_view = None
                    self.mp = mp

                @JOverride
                def run(self):
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

                def get_bdv_view(self):
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

    def get_bdv_view(self):
        return self.bdv_view

    # ------------------------ IMPORT
    def import_from_files(self, filepaths, z_location=0, z_increment=0.02, split_rgb=False):
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
                                     "first_slice_position_mm", z_location,
                                     "slice_spacing_mm", z_increment
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

    # ------------------------ AGENT API: read the state as text, act with actions, look at slices
    # Slices are addressed by their index, which follows the z order and changes when a slice
    # moves: re-read the state after each apply.

    def _subscribe_to_messages(self):
        from jpype import JImplements, JOverride

        messages = self._messages

        @JImplements('java.util.function.BiConsumer')
        class MessageCollector:
            def __init__(self, level):
                self.level = level

            @JOverride
            def accept(self, title, message):
                messages.append({'time': time.time(), 'level': self.level,
                                 'title': str(title), 'message': str(message)})

        # keep references, otherwise the proxies can be garbage collected
        self._message_collectors = [MessageCollector(level) for level in ('error', 'warning', 'info')]
        self.mp.subscribeToErrorMessages(self._message_collectors[0])
        self.mp.subscribeToWarningMessages(self._message_collectors[1])
        self.mp.subscribeToInfoMessages(self._message_collectors[2])

    def get_messages(self, clear: bool = True, levels: Sequence[str] = ('error', 'warning', 'info')) -> list:
        """
        Messages ABBA sent to the user since the last call (or since start)

        :param clear: forget the returned messages
        :param levels: subset of 'error', 'warning', 'info'
        :return: list of dicts with keys time, level, title, message
        """
        selected = [m for m in self._messages if m['level'] in levels]
        if clear:
            self._messages.clear()
        return selected

    def is_busy(self) -> bool:
        """True while ABBA still has tasks to run (registrations are queued asynchronously)"""
        return int(self.mp.getNumberOfTasks()) > 0

    def _get_slices(self, indices: Optional[Sequence[int]] = None) -> list:
        slices = list(self.mp.getSlices())
        if indices is None:
            return slices
        for index in indices:
            if not 0 <= index < len(slices):
                raise IndexError(f'No slice with index {index}: {len(slices)} slice(s)')
        return [slices[index] for index in indices]

    def describe_state(self, slices: Optional[Sequence[int]] = None, max_string_length: int = 500,
                       include_preprocess: bool = False) -> dict:
        """
        Current state as a dict, in the vocabulary of ABBA state files: atlas slicing angles and,
        for each slice, its index, name, slicing axis position (mm), selection, channels,
        pre-transform and the list of actions performed on it (moves, key slice, registrations...)

        :param slices: indices of the slices to describe, all slices if None
        :param max_string_length: longer strings (e.g. spline transforms) are elided, 0 keeps all
        :param include_preprocess: keep the fixed/moving_sources_preprocess of registrations
            (channel selection and z offset, about two thirds of the text). Image based
            registrations (Elastix...) written for apply only need the channel selection, e.g.
            {"type": "SourcesChannelsSelect", "channels_indices": [0, 1]}: recent
            ImageToAtlasRegister versions set the z offset of the target slice and the ROI
        """
        ArrayList = jimport('java.util.ArrayList')
        java_slices = ArrayList()
        for s in self._get_slices(slices):
            java_slices.add(s)
        state = json.loads(str(self.mp.serializeSlices(java_slices, max_string_length)))
        if not include_preprocess:
            for slice_state in state['slices_state_list']:
                for action in slice_state['actions']:
                    action.pop('fixed_sources_preprocess', None)
                    action.pop('moving_sources_preprocess', None)
        state['n_slices'] = int(self.mp.getSlices().size())
        state['busy'] = self.is_busy()
        return state

    def _run_batch(self, actions: list):
        """Runs actions as one undoable step, then waits for them to finish"""
        if not actions:
            return
        MarkActionSequenceBatchAction = jimport('ch.epfl.biop.atlas.aligner.action.MarkActionSequenceBatchAction')
        MarkActionSequenceBatchAction(self.mp).runRequest()
        for action in actions:
            action.runRequest()
        MarkActionSequenceBatchAction(self.mp).runRequest()
        self.mp.waitForTasks()
        self._undoable_batches.append(int(self.mp.userActionsSize()))
        self._redoable_batches.clear()

    def apply(self, actions_by_slice: dict) -> list:
        """
        Runs actions on slices, as a single undoable step, and waits for them to finish.

        Example::

            abba.apply({0: {'type': 'MoveSliceAction', 'location': 7.5},
                        3: [{'type': 'KeySliceOnAction'}]})

        All slice indices are resolved against the state before anything runs, so a move cannot
        retarget the next actions. All actions are parsed before anything runs, so an invalid
        action raises an exception and changes nothing.

        A registration is appended after the existing ones: an affine transform is relative to the
        current registered slice, in mm, in the aligner coordinates (those of the snapshot rulers).
        For instance, a translation of 0.5 mm along x::

            abba.apply({0: {'type': 'RegisterSliceAction',
                            'registration': {'type': 'AffineRegistration',
                                             'parameters': {'transform': '[1,0,0,0.5, 0,1,0,0, 0,0,1,0]'}}}})

        :param actions_by_slice: slice index -> action or list of actions, each as a dict or a JSON
            string, as found in describe_state()['slices_state_list'][i]['actions']
        :return: the class names of the actions that were run
        :raises RuntimeError: if an action failed while running (e.g. a registration error); the
            step is still undoable with undo()
        """
        slices = self._get_slices(list(actions_by_slice.keys()))
        java_actions = []
        for s, actions in zip(slices, actions_by_slice.values()):
            if isinstance(actions, (dict, str)):
                actions = [actions]
            payload = '[' + ','.join(a if isinstance(a, str) else json.dumps(a) for a in actions) + ']'
            java_actions.extend(self.mp.deserializeActions(s, payload))
        n_messages = len(self._messages)
        self._run_batch(java_actions)
        failed = [str(a.actionClassString()) for a in java_actions if not a.isValid()]
        errors = [f"{m['title']}: {m['message']}" for m in self._messages[n_messages:] if m['level'] == 'error']
        if failed or errors:
            raise RuntimeError(f'Failed actions: {failed}; errors: {errors}')
        return [str(a.actionClassString()) for a in java_actions]

    def delete_slices(self, indices: Sequence[int]) -> list:
        """
        Deletes slices, as a single undoable step

        :return: names of the deleted slices
        """
        DeleteSliceAction = jimport('ch.epfl.biop.atlas.aligner.DeleteSliceAction')
        slices = self._get_slices(indices)
        self._run_batch([DeleteSliceAction(self.mp, s) for s in slices])
        return [str(s.getName()) for s in slices]

    def undo(self) -> bool:
        """
        Undoes the last apply or delete_slices. Refuses (returns False) when something else was done
        since, e.g. in the user interface, or when the last step was not done through this API,
        such as the history restored by state_load.
        """
        if not self._undoable_batches or int(self.mp.userActionsSize()) != self._undoable_batches[-1]:
            return False
        self._undoable_batches.pop()
        self.mp.cancelLastAction()
        self.mp.waitForTasks()
        self._redoable_batches.append(int(self.mp.redoableUserActionsSize()))
        return True

    def redo(self) -> bool:
        """Redoes the last step undone by undo; returns False if that is not possible"""
        if not self._redoable_batches or int(self.mp.redoableUserActionsSize()) != self._redoable_batches[-1]:
            return False
        self._redoable_batches.pop()
        self.mp.redoAction()
        self.mp.waitForTasks()
        self._undoable_batches.append(int(self.mp.userActionsSize()))
        return True

    # Inputs of the Elastix register commands that the registration plugins set themselves
    _REGISTRATION_PLUGIN_INPUTS = {
        'sources_fixed', 'sources_moving', 'interpolate', 'min_image_size_pix', 'max_iteration_per_scale',
        'verbose', 'automatic_transform_initialization', 'tp_fixed', 'level_fixed_source', 'tp_moving',
        'level_moving_source'}

    def get_registration_parameters(self, registration_type: str) -> dict:
        """
        Parameters accepted in the 'parameters' of a registration written for apply, e.g.
        get_registration_parameters('Elastix2DAffineRegistration')

        Found by introspection of the SciJava command the registration runs
        (ch.epfl.biop.command.register.<type without 'Registration'>RegisterCommand). All
        values have to be passed as strings. px, py, sx and sy (the region of interest, in mm)
        default to the current ROI.

        :return: dict name -> {type, default, label, description}
        """
        if registration_type == 'AffineRegistration':
            return {'transform': {'type': 'String', 'default': '[1,0,0,0, 0,1,0,0, 0,0,1,0]',
                                  'label': 'Row-packed 3x4 affine matrix',
                                  'description': 'Applied to the registered slice positions, in mm, '
                                                 'see translate_slice'},
                    'pz': {'type': 'String', 'default': '0', 'label': 'z position', 'description': ''}}
        command_name = ('ch.epfl.biop.command.register.'
                        + registration_type.removesuffix('Registration') + 'RegisterCommand')
        info = self.ij.command().getCommand(command_name)
        if info is None:
            raise ValueError(f'No register command {command_name} for {registration_type}')
        module = info.createModule()  # not run: gives the initialized field values as defaults
        parameters = {}
        for item in info.inputs():
            name = str(item.getName())
            java_type = item.getType()
            if (name in self._REGISTRATION_PLUGIN_INPUTS or java_type.isInterface()
                    or 'scijava' in str(java_type.getName())):
                continue
            default = module.getInput(name)
            if name in ('px', 'py', 'sx', 'sy'):
                default = 'optional, current ROI'
            parameters[name] = {'type': str(java_type.getSimpleName()),
                                'default': None if default is None else str(default),
                                'label': str(item.getLabel() or ''),
                                'description': str(item.getDescription() or '')}
        return parameters

    # ABBA commands, as SciJava command classes
    _COMMAND_PACKAGE = 'ch.epfl.biop.atlas.aligner.command'

    def describe_commands(self) -> list:
        """
        The ABBA commands of this session, with what they do

        Each of them is also a method of this class (RegisterSlicesDeepSliceApposeCommand ->
        register_slices_deepslice_appose); get_command_parameters() gives the inputs of one.

        :return: list of dicts with keys name, title, description, sorted by name
        """
        commands = []
        for info in self.ij.command().getCommands():
            class_name = str(info.getDelegateClassName())
            if class_name.startswith(self._COMMAND_PACKAGE):
                commands.append({'name': class_name.rsplit('.', 1)[-1],
                                 'title': str(info.getTitle() or ''),
                                 'description': str(info.getDescription() or '')})
        return sorted(commands, key=lambda command: command['name'])

    def get_command_parameters(self, command_name: str) -> dict:
        """
        Inputs of an ABBA command, with their type, default value and, when the input is a list of
        choices (post_processing, naming_choice...), the exact strings it accepts

        :param command_name: class name, e.g. 'RegisterSlicesDeepSliceApposeCommand',
            see describe_commands()
        :return: dict name -> {type, default, required, label, description, choices}
        """
        info = self.ij.command().getCommand(self._COMMAND_PACKAGE + '.' + command_name)
        if info is None:
            raise ValueError(f'No ABBA command named {command_name}')
        module = info.createModule()  # not run: gives the initialized field values as defaults
        parameters = {}
        for item in info.inputs():
            name = str(item.getName())
            java_type = item.getType()
            if (name == 'mp' or str(item.getVisibility()) == 'MESSAGE'
                    or java_type.isInterface() or 'scijava' in str(java_type.getName())):
                continue  # the ABBA session, messages and the services, all set for the caller
            default = module.getInput(name)
            if default is None or str(default) == 'nan':
                default = None  # NaN means 'not set': the command computes its own default, see its description
            choices = item.getChoices()
            parameters[name] = {'type': str(java_type.getSimpleName()),
                                'default': None if default is None else str(default),
                                'required': bool(item.isRequired()),
                                'label': str(item.getLabel() or ''),
                                'description': str(item.getDescription() or ''),
                                'choices': None if choices is None else [str(choice) for choice in choices]}
        return parameters

    # ------------------------ Hand-made in-plane corrections
    # A registration is appended after the existing ones: a row-packed matrix [m00 m01 0 tx, m10 m11 0 ty,
    # 0 0 1 0] moves each point p of the registered slice to M p + t, in mm, in the aligner coordinates
    # of the snapshots (x to the right, y down). Rotation direction is easy to misjudge on images:
    # check a correction with compare(), which shows the slice before and after it.

    def get_tissue_centroid(self, index: int, pixel_size_mm: float = 0.1,
                            region_mm: Optional[Sequence[float]] = None) -> tuple:
        """
        Centroid (x, y in mm, aligner coordinates) of the registered tissue of a slice, from a
        coarse render thresholded with Otsu's method

        :param region_mm: [x, y, width, height] rendered; if None, the region of interest enlarged
            by half its size on each side, so that a moved or rotated slice is not clipped
        """
        import numpy as np
        if region_mm is None:
            x, y, w, h = [float(v) for v in self.mp.getROI()]
            region_mm = [x - w / 2, y - h / 2, 2 * w, 2 * h]
        roi = [float(v) for v in region_mm]
        SliceSnapshot, java_options = self._snapshot_options(dict(
            pixelSizeMm=pixel_size_mm, showHeader=False, showRulers=False, showRegionBorders=False,
            showRegionLabels=False, atlasChannel=-1, regionMm=roi))
        image = SliceSnapshot.render(self.mp, self._get_slices([index])[0], java_options)
        width, height = int(image.getWidth()), int(image.getHeight())
        argb = np.asarray(image.getRGB(0, 0, width, height, None, 0, width), dtype=np.int64)
        luminance = (0.299 * ((argb >> 16) & 255) + 0.587 * ((argb >> 8) & 255)
                     + 0.114 * (argb & 255)).reshape(height, width)
        histogram, edges = np.histogram(luminance, bins=256, range=(0, 256))
        weights = np.cumsum(histogram)
        means = np.cumsum(histogram * edges[:-1])
        between = (means[-1] * weights - means * weights[-1]) ** 2 / np.maximum(
            weights * (weights[-1] - weights), 1)
        mask = luminance > edges[int(np.argmax(between))]
        ys, xs = np.nonzero(mask)
        if xs.size == 0:
            return roi[0] + roi[2] / 2, roi[1] + roi[3] / 2
        # pixel centers, the render grid spans the region of interest
        return (float(roi[0] + (xs.mean() + 0.5) * roi[2] / width),
                float(roi[1] + (ys.mean() + 0.5) * roi[3] / height))

    def _apply_affine_2d(self, index: int, m00: float, m01: float, m10: float, m11: float,
                         center: Optional[Sequence[float]]) -> list:
        cx, cy = self.get_tissue_centroid(index) if center is None else center
        # p' = M (p - c) + c
        tx = cx - (m00 * cx + m01 * cy)
        ty = cy - (m10 * cx + m11 * cy)
        return self.apply_affine_matrix(index, [m00, m01, 0, tx, m10, m11, 0, ty, 0, 0, 1, 0])

    def apply_affine_matrix(self, index: int, row_packed_matrix: Sequence[float]) -> list:
        """Appends an affine registration given as a row-packed 3x4 matrix, see apply"""
        return self.apply({index: {'type': 'RegisterSliceAction',
                                   'registration': {'type': 'AffineRegistration',
                                                    'parameters': {'transform': json.dumps(
                                                        [float(v) for v in row_packed_matrix])}}}})

    def translate_slice(self, index: int, dx_mm: float, dy_mm: float) -> list:
        """Moves the registered slice by (dx, dy) mm (x to the right, y down), as one undoable step"""
        return self.apply_affine_matrix(index, [1, 0, 0, dx_mm, 0, 1, 0, dy_mm, 0, 0, 1, 0])

    def rotate_slice(self, index: int, degrees: float, center: Optional[Sequence[float]] = None) -> list:
        """
        Rotates the registered slice in plane, as one undoable step

        :param degrees: positive = clockwise as seen in snapshots (y points down)
        :param center: (x, y) in mm, the tissue centroid if None
        """
        import math
        c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
        return self._apply_affine_2d(index, c, -s, s, c, center)

    def scale_slice(self, index: int, sx: float, sy: Optional[float] = None,
                    center: Optional[Sequence[float]] = None) -> list:
        """
        Scales the registered slice in plane, as one undoable step

        :param sy: same as sx if None
        :param center: (x, y) in mm, the tissue centroid if None
        """
        return self._apply_affine_2d(index, sx, 0, 0, sx if sy is None else sy, center)

    def compare(self, index: int, path: str, **options: Any) -> str:
        """
        Saves a PNG with the slice before (left) and after (right) its last registration

        :param options: SliceSnapshot.Options fields, see snapshot
        :return: the saved file path
        """
        ArrayList = jimport('java.util.ArrayList')
        slice_ = self._get_slices([index])[0]
        steps_back = [1, 0] if int(slice_.getNumberOfRegistrations()) > 0 else [0]
        images = ArrayList()
        for step_back in steps_back:
            SliceSnapshot, java_options = self._snapshot_options(dict(options, registrationStepBack=step_back))
            images.add(SliceSnapshot.render(self.mp, slice_, java_options))
        return str(SliceSnapshot.save(SliceSnapshot.tile(images, len(steps_back)), path))

    def set_atlas_slicing_angles(self, x_degrees: float, y_degrees: float):
        """Sets the atlas slicing angles, in degrees (not undoable)"""
        resliced_atlas = self.mp.getReslicedAtlas()
        resliced_atlas.setRotateX(x_degrees / 180.0 * 3.141592653589793)
        resliced_atlas.setRotateY(y_degrees / 180.0 * 3.141592653589793)

    def _snapshot_options(self, options: dict):
        SliceSnapshot = jimport('ch.epfl.biop.atlas.aligner.inspect.SliceSnapshot')
        java_options = SliceSnapshot.Options()
        for key, value in options.items():
            if not hasattr(java_options, key):
                raise AttributeError(f'Unknown SliceSnapshot option {key}')
            setattr(java_options, key, value)
        return SliceSnapshot, java_options

    def snapshot(self, index: Optional[int], path: str, **options: Any) -> str:
        """
        Saves a PNG of a registered slice with the atlas regions and a header (index, z, number
        of registrations)

        :param index: slice index, or None to render the atlas only (set atlasSlicingAxisPositionMm)
        :param path: PNG file path
        :param options: fields of ch.epfl.biop.atlas.aligner.inspect.SliceSnapshot.Options, e.g.
            pixelSizeMm=0.025, atlasChannel=0, registrationStepBack=1, atlasSlicingAxisPositionMm=7.5
        :return: the saved file path
        """
        SliceSnapshot, java_options = self._snapshot_options(options)
        target = None if index is None else self._get_slices([index])[0]
        image = SliceSnapshot.render(self.mp, target, java_options)
        return str(SliceSnapshot.save(image, path))

    def atlas_sweep(self, path: str, z_positions_mm: Sequence[float], columns: int = 0,
                    atlas_channel: int = 0, **options: Any) -> str:
        """
        Saves a PNG with atlas-only renders at several slicing axis positions, to find which
        position matches a slice

        :param z_positions_mm: slicing axis positions to render
        :param atlas_channel: atlas structural channel shown
        :param options: other SliceSnapshot.Options fields, see snapshot
        """
        ArrayList = jimport('java.util.ArrayList')
        images = ArrayList()
        SliceSnapshot = None
        for z in z_positions_mm:
            SliceSnapshot, java_options = self._snapshot_options(
                dict(options, atlasSlicingAxisPositionMm=float(z), atlasChannel=atlas_channel))
            images.add(SliceSnapshot.render(self.mp, None, java_options))
        if SliceSnapshot is None:
            raise ValueError('No position to render')
        return str(SliceSnapshot.save(SliceSnapshot.tile(images, columns), path))

    def overview(self, path: str, slices: Optional[Sequence[int]] = None, columns: int = 0,
                 **options: Any) -> str:
        """
        Saves a PNG with a grid of slice snapshots, see snapshot

        :param slices: slice indices, all slices if None
        :param columns: number of columns, 0 for automatic
        """
        ArrayList = jimport('java.util.ArrayList')
        SliceSnapshot, java_options = self._snapshot_options(options)
        java_slices = ArrayList()
        for s in self._get_slices(slices):
            java_slices.add(s)
        image = SliceSnapshot.overview(self.mp, java_slices, java_options, columns)
        return str(SliceSnapshot.save(image, path))

    @staticmethod
    def _optional_input(name: str, value: Any) -> list:
        """
        [name, value] to append to the inputs of a command, or nothing if value is None: the command then
        uses its own default
        """
        return [] if value is None else [name, value]

    # ---------------------- AUTOGENERATED CODE with the main method from ScijavaCommandToPython
    def benchmark(self,
            comment: str,
            demo_dataset: str,
            use_gui: bool,
            wait_between_each_step: bool):
        """
        Runs a complete ABBA workflow on a demo dataset (mouse atlas, import, two DeepSlice runs, Elastix affine and spline registrations, QuPath export for the remote datasets) and reports the time and memory used by each step.

        Parameters:
        comment (str): Comment. Free text copied in the report, for instance to describe the machine.
        demo_dataset (str): Demo dataset. Remote datasets are streamed from a public OMERO server (needs the OMERO dependencies). Local datasets are downloaded once from Zenodo and cached (about 1 GB per slide).
        use_gui (bool): Use graphical user interface. If checked, the benchmark runs in an ABBA window; otherwise it runs without display.
        wait_between_each_step (bool): Time each registration step. If checked, each registration step waits for all sections to be done before the next one starts, so that each step is timed separately. Slower.
        """
        ABBABenchMarkCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBABenchMarkCommand')
        return self.ij.command().run(ABBABenchMarkCommand, True,
                                    'comment', comment,
                                    'demo_dataset', demo_dataset,
                                    'use_gui', use_gui,
                                    'wait_between_each_step', wait_between_each_step).get()

    def check_for_update(self):
        """
        Compares the installed ABBA version with the latest release on GitHub and shows the result in a dialog.

        """
        ABBACheckForUpdateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACheckForUpdateCommand')
        return self.ij.command().run(ABBACheckForUpdateCommand, True)

    def cite_info(self):
        """
        Shows how to cite ABBA and the tools it uses, in a window (requires an internet connection).

        """
        ABBACiteInfoCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACiteInfoCommand')
        return self.ij.command().run(ABBACiteInfoCommand, True)

    def close(self):
        """
        Closes an ABBA session and releases it. Unsaved work is lost.

        """
        ABBACloseCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBACloseCommand')
        return self.ij.command().run(ABBACloseCommand, True,
                                    'mp', self.mp).get()

    def documentation(self):
        """
        Opens the ABBA documentation website in a web browser.

        """
        ABBADocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBADocumentationCommand')
        return self.ij.command().run(ABBADocumentationCommand, True)

    def forum_help(self):
        """
        Opens a new post draft on the image.sc forum in a web browser, pre-filled with the versions of ABBA and its dependencies.

        """
        ABBAForumHelpCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAForumHelpCommand')
        return self.ij.command().run(ABBAForumHelpCommand, True)

    def generate_methods_prompt(self):
        """
        Generates a prompt describing how the selected slices were registered (atlas, slicing angles, positions, registration steps), to paste in a large language model to draft the methods section of a publication.

        """
        ABBAGenerateMethodsPrompt = jimport('ch.epfl.biop.atlas.aligner.command.ABBAGenerateMethodsPrompt')
        return self.ij.command().run(ABBAGenerateMethodsPrompt, True,
                                    'mp', self.mp).get()

    def set_bdv_preferences(self):
        """
        Not functional: meant to edit the keyboard and mouse bindings of the ABBA viewer.

        """
        ABBASetBDVPreferencesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBASetBDVPreferencesCommand')
        return self.ij.command().run(ABBASetBDVPreferencesCommand, True)

    def start_log(self):
        """
        Opens a debug window which logs the slice events of an ABBA session (creation, deletion, actions).

        """
        ABBAStartLogCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStartLogCommand')
        return self.ij.command().run(ABBAStartLogCommand, True,
                                    'mp', self.mp).get()

    def state_load(self,
            state_file):
        """
        Loads a saved ABBA state (.abba file): slices, their positions and registrations, and the atlas slicing angles. The slices are added to the current session. The image files must still be at the location where they were when the state was saved.

        Parameters:
        state_file : State file (.abba). ABBA state file to load. It must have been saved with the same atlas.
        """
        ABBAStateLoadCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateLoadCommand')
        return self.ij.command().run(ABBAStateLoadCommand, True,
                                    'mp', self.mp,
                                    'state_file', state_file).get().getOutput('success')

    def state_save(self,
            state_file):
        """
        Saves the current ABBA session (slices, positions, registrations, atlas slicing angles) in a .abba file. Images are not copied: the file references the original image files. Existing files are not overwritten.

        Parameters:
        state_file : State file (.abba). File to create. The '.abba' extension is added if there is none. The file must not exist already.
        """
        ABBAStateSaveCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAStateSaveCommand')
        return self.ij.command().run(ABBAStateSaveCommand, True,
                                    'mp', self.mp,
                                    'state_file', state_file).get().getOutput('success')

    def user_feedback(self):
        """
        Opens the ABBA user feedback form in a web browser.

        """
        ABBAUserFeedbackCommand = jimport('ch.epfl.biop.atlas.aligner.command.ABBAUserFeedbackCommand')
        return self.ij.command().run(ABBAUserFeedbackCommand, True)

    def deepslice_documentation(self):
        """
        Opens the DeepSlice guide website in a web browser.

        """
        DeepSliceDocumentationCommand = jimport('ch.epfl.biop.atlas.aligner.command.DeepSliceDocumentationCommand')
        return self.ij.command().run(DeepSliceDocumentationCommand, True)

    def export_atlas_to_imagej(self,
            atlas_channels_csv: str,
            image_name: str,
            interpolate: bool,
            pixel_size_um: float):
        """
        Exports the atlas section at the position of each selected slice as an ImageJ image, one plane per slice, within the current region of interest. Same geometry as 'Export Registered Slices to ImageJ' with the same pixel size, so both images can be overlaid.

        Parameters:
        atlas_channels_csv (str): Atlas channels. 0-based indices of the atlas channels to export, comma separated (e.g. '0,1'), or '*' for all channels. Depending on the atlas, channels include anatomical images, region borders, atlas coordinates, a left/right indicator and region labels.
        image_name (str): Image name. Title of the exported ImageJ image.
        interpolate (bool): Interpolate. If checked, pixels are linearly interpolated when resampled; otherwise the nearest pixel is used (keep it unchecked for label channels).
        pixel_size_um (float): Pixel size (micrometers). Pixel size of the exported image.
        """
        ExportAtlasToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportAtlasToImageJCommand')
        return self.ij.command().run(ExportAtlasToImageJCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'image_name', image_name,
                                    'interpolate', interpolate,
                                    'pixel_size_um', pixel_size_um).get()

    def export_deformation_field_to_imagej(self,
            downsampling: int,
            max_number_of_iterations: int,
            resolution_level: int):
        """
        For each selected slice, exports a 3-channel (x, y, z) 32-bit ImageJ image with the same pixels as the original unregistered slice image: each pixel holds its atlas coordinates, in mm. Waits for the registrations of the slices to be done.

        Parameters:
        downsampling (int): Additional downsampling factor. Integer factor to further downsample the exported image, on top of the resolution level. 1 = no downsampling.
        max_number_of_iterations (int): Max iterations for transform inversion. Maximum number of iterations used to numerically invert non-linear (spline) registrations. Increase it if the inversion does not converge. Default 200.
        resolution_level (int): Resolution level. Resolution level of the original image the exported image matches: 0 = full resolution, 1 = first downscaled level, etc. Must exist in the slice files.
        """
        ExportDeformationFieldToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportDeformationFieldToImageJCommand')
        return self.ij.command().run(ExportDeformationFieldToImageJCommand, True,
                                    'mp', self.mp,
                                    'downsampling', downsampling,
                                    'max_number_of_iterations', max_number_of_iterations,
                                    'resolution_level', resolution_level).get()

    def export_registration_to_qupath(self,
            erase_previous_file: bool):
        """
        For each selected slice imported from a QuPath project, saves its atlas regions and its registration (ABBA-RoiSet and ABBA-Transform files) in the QuPath project folder of the image. They are then imported in QuPath with the ABBA extension. Slices not imported from a QuPath project are not exported.

        Parameters:
        erase_previous_file (bool): Overwrite previous export. If checked, a previous ABBA export of the same image is replaced; otherwise an error is reported for this image.
        """
        ExportRegistrationToQuPathCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportRegistrationToQuPathCommand')
        return self.ij.command().run(ExportRegistrationToQuPathCommand, True,
                                    'mp', self.mp,
                                    'erase_previous_file', erase_previous_file).get()

    def export_resampled_slices_to_bdv_source(self,
            block_size_x: int,
            block_size_y: int,
            block_size_z: int,
            downsample_x: int,
            downsample_y: int,
            downsample_z: int,
            image_name: str,
            interpolate: bool,
            margin_z_um: float,
            n_threads: int,
            resolution_levels: int,
            slice_channels_csv: str,
            voxel_size_x_um: float,
            voxel_size_y_um: float,
            voxel_size_z_um: float):
        """
        Experimental: fuses the registered selected slices into a 3D volume in atlas coordinates, resampled at the given voxel size and within the current region of interest, as multiresolution BigDataViewer sources (one per channel), computed lazily and cached.

        Parameters:
        block_size_x (int): Cache block size X (pixels). Size along X of the blocks computed and cached at once.
        block_size_y (int): Cache block size Y (pixels). Size along Y of the blocks computed and cached at once.
        block_size_z (int): Cache block size Z (pixels). Size along Z of the blocks computed and cached at once.
        downsample_x (int): Downsampling between resolution levels X. Factor along X between two consecutive resolution levels of the output.
        downsample_y (int): Downsampling between resolution levels Y. Factor along Y between two consecutive resolution levels of the output.
        downsample_z (int): Downsampling between resolution levels Z. Factor along Z between two consecutive resolution levels of the output.
        image_name (str): Source name. Base name of the exported sources, '_ch<index>' is appended for each channel.
        interpolate (bool): Interpolate. If checked, pixels are linearly interpolated when resampled; otherwise the nearest pixel is used.
        margin_z_um (float): Z margin (micrometers). Extra space added before the first and after the last selected slice along the slicing axis.
        n_threads (int): Number of threads. Number of threads used to compute the blocks.
        resolution_levels (int): Number of resolution levels. Number of resolution levels of the output sources, at least 1.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to export, comma separated (e.g. '0,2'), or '*' for all channels.
        voxel_size_x_um (float): Voxel size X (micrometers). Size of the output voxels along the X axis of the sections.
        voxel_size_y_um (float): Voxel size Y (micrometers). Size of the output voxels along the Y axis of the sections.
        voxel_size_z_um (float): Voxel size Z (micrometers). Size of the output voxels along the slicing axis.
        """
        ExportResampledSlicesToBDVSourceCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportResampledSlicesToBDVSourceCommand')
        return self.ij.command().run(ExportResampledSlicesToBDVSourceCommand, True,
                                    'mp', self.mp,
                                    'block_size_x', block_size_x,
                                    'block_size_y', block_size_y,
                                    'block_size_z', block_size_z,
                                    'downsample_x', downsample_x,
                                    'downsample_y', downsample_y,
                                    'downsample_z', downsample_z,
                                    'image_name', image_name,
                                    'interpolate', interpolate,
                                    'margin_z_um', margin_z_um,
                                    'n_threads', n_threads,
                                    'resolution_levels', resolution_levels,
                                    'slice_channels_csv', slice_channels_csv,
                                    'voxel_size_x_um', voxel_size_x_um,
                                    'voxel_size_y_um', voxel_size_y_um,
                                    'voxel_size_z_um', voxel_size_z_um).get()

    def export_slices_original_data_to_imagej(self,
            resolution_level: int,
            slice_channels_csv: str,
            verbose: bool):
        """
        Opens in ImageJ the original, unregistered image of each selected slice, at the chosen resolution level. Fails for images larger than 2 billion pixels (use a lower resolution level). Useful together with the regions exported to the ROI Manager.

        Parameters:
        resolution_level (int): Resolution level. 0 = full resolution, 1 = first downscaled level, etc. Must exist in all selected slices.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to export, comma separated (e.g. '0,2'), or '*' for all channels.
        verbose (bool): Verbose. If checked, logs the progress of the image loading.
        """
        ExportSlicesOriginalDataToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesOriginalDataToImageJCommand')
        return self.ij.command().run(ExportSlicesOriginalDataToImageJCommand, True,
                                    'mp', self.mp,
                                    'resolution_level', resolution_level,
                                    'slice_channels_csv', slice_channels_csv,
                                    'verbose', verbose).get()

    def export_slices_to_bdv(self,
            tag: str):
        """
        Shows the registered selected slices, placed in atlas coordinates, in a new BigDataViewer window. The sources are also added to the BigDataViewer-Playground source tree. Waits for all ABBA tasks to be done.

        Parameters:
        tag (str): Tag. Text stored as the 'ABBA' metadata of each exported source, to identify them later in scripts.
        """
        ExportSlicesToBDVCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVCommand')
        return self.ij.command().run(ExportSlicesToBDVCommand, True,
                                    'mp', self.mp,
                                    'tag', tag).get()

    def export_slices_to_bdv_json_dataset(self,
            file,
            tag: str):
        """
        Very experimental: saves the registered selected slices, placed in atlas coordinates, as a BigDataViewer-Playground json file which references the original images. Waits for all ABBA tasks to be done.

        Parameters:
        file : Output file (.json). Json file to create.
        tag (str): Tag. Text stored as the 'ABBA' metadata of each exported source, to identify them later in scripts.
        """
        ExportSlicesToBDVJsonDatasetCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVJsonDatasetCommand')
        return self.ij.command().run(ExportSlicesToBDVJsonDatasetCommand, True,
                                    'mp', self.mp,
                                    'file', file,
                                    'tag', tag).get()

    def export_slices_to_quicknii_dataset(self,
            convert_to_8_bits: bool,
            convert_to_jpg: bool,
            dataset_folder,
            image_name: str,
            interpolate: bool,
            pixel_size_um: float,
            slice_channels_csv: str):
        """
        Exports the selected slices as a QuickNII dataset: registered (deformed) slice images resampled within the current region of interest, and a series JSON file with the position of each image in the atlas. The exported images already include all registrations. The folder is created if needed.

        Parameters:
        convert_to_8_bits (bool): Convert to 8-bit. If checked, images are converted to 8-bit before being saved.
        convert_to_jpg (bool): Save as JPEG. If checked, images are saved as JPEG, the format QuickNII reads; a single channel is recommended. Otherwise they are saved as TIFF.
        dataset_folder : Output folder. Folder where the images ('<prefix>_s000.jpg'...) and the '<prefix>.json' series file are written.
        image_name (str): File name prefix. Prefix of the exported image files and name of the JSON series file.
        interpolate (bool): Interpolate. If checked, pixels are linearly interpolated when resampled; otherwise the nearest pixel is used.
        pixel_size_um (float): Pixel size (micrometers). Pixel size at which the registered slices are resampled.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to export, comma separated (e.g. '0,2'), or '*' for all channels.
        """
        ExportSlicesToQuickNIIDatasetCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToQuickNIIDatasetCommand')
        return self.ij.command().run(ExportSlicesToQuickNIIDatasetCommand, True,
                                    'mp', self.mp,
                                    'convert_to_8_bits', convert_to_8_bits,
                                    'convert_to_jpg', convert_to_jpg,
                                    'dataset_folder', dataset_folder,
                                    'image_name', image_name,
                                    'interpolate', interpolate,
                                    'pixel_size_um', pixel_size_um,
                                    'slice_channels_csv', slice_channels_csv).get()

    def export_std_zip_state(self,
            downscale_deformation_field: int,
            experiment_information: str,
            identifier: str,
            output_folder,
            pixel_size_um: float,
            slice_channels_csv: str):
        """
        Creates a standardized, shareable zip of the current ABBA session: all slices downscaled to a given pixel size, their registrations, their deformation fields and metadata (atlas, slicing orientation, experiment information). The zip can be opened with 'Import Standardized ABBA Project (Zip)'. The session itself is not modified.

        Parameters:
        downscale_deformation_field (int): Deformation field downscaling factor. The deformation field (atlas coordinates of each pixel) is computed every N pixels of the exported slices.
        experiment_information (str): Experiment information. Free text describing the experiment (animal, staining, sectioning...), stored in the metadata of the zip.
        identifier (str): Export identifier. Short name of the export, used in the zip file name: abba_export_<identifier>.zip.
        output_folder : Output folder. Folder where the zip is written. A zip with the same name must not exist.
        pixel_size_um (float): Pixel size of the exported slices (micrometers). The original slice images are downscaled to this pixel size to keep the zip small.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to export, comma separated (e.g. '0,2'), or '*' for all channels.
        """
        ExportStdZipStateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportStdZipStateCommand')
        return self.ij.command().run(ExportStdZipStateCommand, True,
                                    'mp', self.mp,
                                    'downscale_deformation_field', downscale_deformation_field,
                                    'experiment_information', experiment_information,
                                    'identifier', identifier,
                                    'output_folder', output_folder,
                                    'pixel_size_um', pixel_size_um,
                                    'slice_channels_csv', slice_channels_csv).get()

    def import_demo_slices_omero(self,
            demo_dataset: str,
            project_directory):
        """
        Imports demo mouse brain sections streamed from a public OMERO server, through a QuPath project downloaded from Zenodo. Requires an internet connection and the OMERO dependencies.

        Parameters:
        demo_dataset (str): Demo dataset. '25 sections': a subset, faster to try ABBA. '97 sections': the full brain.
        project_directory : QuPath project folder (optional). Existing folder where the demo QuPath project is downloaded, to keep it and export registrations to it. If empty or missing, a temporary folder is used.
        """
        ImportDemoSlicesOMEROCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportDemoSlicesOMEROCommand')
        return self.ij.command().run(ImportDemoSlicesOMEROCommand, True,
                                    'mp', self.mp,
                                    'demo_dataset', demo_dataset,
                                    'project_directory', project_directory).get()

    def import_demo_slices_zenodo(self,
            number_of_slides: int):
        """
        Imports demo mouse brain sections from whole slide images (vsi) downloaded from Zenodo and cached locally (about 1 GB per slide). The label and overview images of each slide are imported as extra slices (their name does not contain '10x'). All slices are selected at the end.

        Parameters:
        number_of_slides (int): Number of slides. Number of slides to download, from 1 to 7, picked around the central slide. Each slide contains several sections.
        """
        ImportDemoSlicesZENODOCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportDemoSlicesZENODOCommand')
        return self.ij.command().run(ImportDemoSlicesZENODOCommand, True,
                                    'mp', self.mp,
                                    'number_of_slides', number_of_slides).get()

    def import_slice_from_image_plus(self,
            image,
            slice_position_mm: float):
        """
        Imports an image opened in ImageJ as a single slice, all channels included. The image should be calibrated (pixel size).

        Parameters:
        image : Image. ImageJ image to import; by default the current image.
        slice_position_mm (float): Slice position (mm). Initial position of the slice along the atlas slicing axis, in mm, as the Z shown in the slice information (0 = front of the atlas).
        """
        ImportSliceFromImagePlusCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSliceFromImagePlusCommand')
        return self.ij.command().run(ImportSliceFromImagePlusCommand, True,
                                    'mp', self.mp,
                                    'image', image,
                                    'slice_position_mm', slice_position_mm).get()

    def import_slice_from_sources(self,
            slice_position_mm: float,
            sources):
        """
        Imports BigDataViewer-Playground sources as a single slice: each source becomes one channel of the slice.

        Parameters:
        slice_position_mm (float): Slice position (mm). Initial position of the slice along the atlas slicing axis, in mm, as the Z shown in the slice information (0 = front of the atlas).
        sources : Sources (channels). Sources forming the slice, one per channel, in channel order. Their calibration should be in mm.
        """
        ImportSliceFromSourcesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSliceFromSourcesCommand')
        return self.ij.command().run(ImportSliceFromSourcesCommand, True,
                                    'mp', self.mp,
                                    'slice_position_mm', slice_position_mm,
                                    'sources', sources).get()

    def import_slices_from_files(self,
            datasetname: str,
            files,
            first_slice_position_mm: float,
            slice_spacing_mm: float,
            split_rgb_channels: bool):
        """
        Imports images from Bio-Formats compatible files (vsi, czi, ome.tiff, lif...) as slices. Each image series of each file becomes one slice, all channels included. The imported slices are selected.

        Parameters:
        datasetname (str): Dataset name. Name of the dataset grouping the imported images in the BigDataViewer-Playground source tree.
        files : Files to import. Image files to open with Bio-Formats. Files should have a pixel size calibration.
        first_slice_position_mm (float): Position of the first slice (mm). Initial position of the first imported slice along the atlas slicing axis, in mm, as the Z shown in the slice information (0 = front of the atlas). Positions can be adjusted later, for instance with DeepSlice.
        slice_spacing_mm (float): Spacing between slices (mm). Distance between consecutive imported slices along the slicing axis, in mm. Use a negative value to reverse their order.
        split_rgb_channels (bool): Split RGB channels. If checked, RGB images are split into three channels (red, green, blue); otherwise they are kept as a single RGB channel.
        """
        ImportSlicesFromFilesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromFilesCommand')
        return self.ij.command().run(ImportSlicesFromFilesCommand, True,
                                    'mp', self.mp,
                                    'datasetname', datasetname,
                                    'files', files,
                                    'first_slice_position_mm', first_slice_position_mm,
                                    'slice_spacing_mm', slice_spacing_mm,
                                    'split_rgb_channels', split_rgb_channels).get()

    def import_slices_from_qupath(self,
            first_slice_position_mm: float,
            qupath_project,
            slice_spacing_mm: float):
        """
        Imports all images of a QuPath project as slices, one slice per project image, all channels included. Registrations can then be exported back to the QuPath project. Do not add or remove images in the QuPath project after the import.

        Parameters:
        first_slice_position_mm (float): Position of the first slice (mm). Initial position of the first imported slice along the atlas slicing axis, in mm, as the Z shown in the slice information (0 = front of the atlas). Positions can be adjusted later, for instance with DeepSlice.
        qupath_project : QuPath project file (.qpproj). The project.qpproj file of the QuPath project to import.
        slice_spacing_mm (float): Spacing between slices (mm). Distance between consecutive imported slices along the slicing axis, in mm. Use a negative value to reverse their order. Cannot be 0.
        """
        ImportSlicesFromQuPathCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromQuPathCommand')
        return self.ij.command().run(ImportSlicesFromQuPathCommand, True,
                                    'mp', self.mp,
                                    'first_slice_position_mm', first_slice_position_mm,
                                    'qupath_project', qupath_project,
                                    'slice_spacing_mm', slice_spacing_mm).get()

    def import_slices_from_quicknii(self,
            quicknii_project,
            split_rgb_channels: bool):
        """
        Imports the images of a QuickNII series (JSON file, also produced by DeepSlice) as slices, together with their registration: slice positions, in-plane affine transforms and atlas slicing angle. The import is approximate: a single slicing angle (median of all slices) is applied to all slices.

        Parameters:
        quicknii_project : QuickNII file (.json). QuickNII series file, in JSON format. The images it references must be in the same folder.
        split_rgb_channels (bool): Split RGB channels. If checked, RGB images are split into three channels (red, green, blue); otherwise they are kept as a single RGB channel.
        """
        ImportSlicesFromQuickNIICommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportSlicesFromQuickNIICommand')
        return self.ij.command().run(ImportSlicesFromQuickNIICommand, True,
                                    'mp', self.mp,
                                    'quicknii_project', quicknii_project,
                                    'split_rgb_channels', split_rgb_channels).get()

    def import_std_zip_state(self,
            zip_file):
        """
        Opens a standardized ABBA project zip, created with 'Export Standardized ABBA Project (Zip)', in a new ABBA window: the atlas and slicing orientation stored in the zip are loaded, then the downscaled slices and their registrations.

        Parameters:
        zip_file : Standardized project (.zip). Zip file created with 'Export Standardized ABBA Project (Zip)'.
        """
        ImportStdZipStateCommand = jimport('ch.epfl.biop.atlas.aligner.command.ImportStdZipStateCommand')
        return self.ij.command().run(ImportStdZipStateCommand, True,
                                    'zip_file', zip_file).get()

    def mirror_do(self,
            mirror_side: str):
        """
        Turns hemi-sections into full sections, for instance before DeepSlice which needs full sections. The vertical midline of the atlas acts as a mirror: the half of each selected slice on the chosen side is kept, and its mirror image replaces the other half. Place the hemi-section against the atlas midline first. Undo with 'Un-Mirror Slices'.

        Parameters:
        mirror_side (str): Half to keep (as displayed). Side of the atlas midline, as displayed on screen, where the tissue is. 'Left': the left half is kept and mirrored onto the right half. 'Right': the right half is kept and mirrored onto the left half.
        """
        MirrorDoCommand = jimport('ch.epfl.biop.atlas.aligner.command.MirrorDoCommand')
        return self.ij.command().run(MirrorDoCommand, True,
                                    'mp', self.mp,
                                    'mirror_side', mirror_side).get()

    def mirror_undo(self):
        """
        Removes the mirroring of the selected slices, made with 'Mirror Slices', while keeping the registrations done afterwards.

        """
        MirrorUndoCommand = jimport('ch.epfl.biop.atlas.aligner.command.MirrorUndoCommand')
        return self.ij.command().run(MirrorUndoCommand, True,
                                    'mp', self.mp).get()

    def raster_slices(self,
            interpolate: bool,
            pixel_size_um: float):
        """
        Speeds up the display of the selected slices by computing and caching their registered image at a fixed pixel size. The cached image has a lower resolution than the original image. Experimental.

        Parameters:
        interpolate (bool): Interpolate. If checked, pixels are linearly interpolated when resampled; otherwise the nearest pixel is used.
        pixel_size_um (float): Pixel size (micrometers). Pixel size of the cached images: larger is faster and uses less memory, but is blurrier.
        """
        RasterSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.RasterSlicesCommand')
        return self.ij.command().run(RasterSlicesCommand, True,
                                    'mp', self.mp,
                                    'interpolate', interpolate,
                                    'pixel_size_um', pixel_size_um).get()

    def raster_slices_deformation(self,
            grid_spacing_um: float):
        """
        Speeds up the display of the selected slices by computing their deformation field on a grid and interpolating it. Only useful after spline registrations. Experimental.

        Parameters:
        grid_spacing_um (float): Grid spacing (micrometers). Spacing of the grid on which the deformation is computed. Larger is faster but less accurate. Must be above the atlas resolution.
        """
        RasterSlicesDeformationCommand = jimport('ch.epfl.biop.atlas.aligner.command.RasterSlicesDeformationCommand')
        return self.ij.command().run(RasterSlicesDeformationCommand, True,
                                    'mp', self.mp,
                                    'grid_spacing_um', grid_spacing_um).get()

    def register_slices_bigwarp(self,
            atlas_channels_csv: str,
            slice_channels_csv: str):
        """
        Manual in-plane non-linear registration of the selected slices: each slice is opened in BigWarp, one after the other, where landmarks are placed by hand. Selected channels are only used for display.

        Parameters:
        atlas_channels_csv (str): Atlas channels. 0-based indices of the atlas channels to use, comma separated (e.g. '0,1'). '*' is not accepted. Channel indices are shown in the atlas display card.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to use, comma separated (e.g. '0,1'). '*' is not accepted.
        """
        RegisterSlicesBigWarpCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesBigWarpCommand')
        return self.ij.command().run(RegisterSlicesBigWarpCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'slice_channels_csv', slice_channels_csv).get()

    def register_slices_copy_and_apply(self,
            model_slice_index: int,
            skip_pre_transform: bool):
        """
        Copies all registrations of a model slice and appends them, as they are (no new computation), to the registrations of each selected slice. The model slice itself is left unchanged.

        Parameters:
        model_slice_index (int): Model slice index. 0-based index of the slice whose registrations are copied, in the slice order along the slicing axis.
        skip_pre_transform (bool): Skip the pre-transform. If checked, the model slice pre-transform is not copied: the out-of-plane part of X or Y flips, and rotations made with older ABBA versions. In-plane edits are registrations and are always copied.
        """
        RegisterSlicesCopyAndApplyCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesCopyAndApplyCommand')
        return self.ij.command().run(RegisterSlicesCopyAndApplyCommand, True,
                                    'mp', self.mp,
                                    'model_slice_index', model_slice_index,
                                    'skip_pre_transform', skip_pre_transform).get()

    def register_slices_deepslice_appose(self,
            allow_slicing_angle_change: bool,
            ensemble: bool,
            model: str,
            post_processing: str,
            slice_channels_csv: str,
            slice_spacing_um: float,
            pixel_size_um: Optional[float] = None):
        """
        Runs DeepSlice (installed automatically in a local Python environment) on the selected slices: sets their position along the slicing axis, adds an in-plane affine registration and optionally adjusts the atlas slicing angle. The result depends on the slices display settings: avoid saturation.

        Parameters:
        allow_slicing_angle_change (bool): Adjust atlas slicing angle. If checked, the atlas slicing angles (X and Y rotations) are set to the median angle found by DeepSlice. This changes the slicing for all slices, not only the selected ones.
        ensemble (bool): Ensemble (average of several models, slower). If checked, DeepSlice averages the predictions of several models. Results may be better or not depending on the dataset: try both.
        model (str): DeepSlice model. Species DeepSlice was trained on: 'mouse' or 'rat'. It should match the atlas.
        pixel_size_um (float): Pixel size sent to DeepSlice (micrometers). Optional. Pixel size used to downsample the slices before sending them to DeepSlice. Defaults to 10.0 for mouse and 40.0 for rat; larger values are faster.
        post_processing (str): Position post-processing. How the slice positions predicted by DeepSlice are corrected. 'Keep order': the current slice order is preserved. 'Keep order + ensure regular spacing': order preserved and slices evenly spaced, spacing estimated by DeepSlice. 'Keep order + set spacing (parameter below)': order preserved and slices evenly spaced with the spacing given below. 'No post-processing': raw DeepSlice positions, slices may be reordered.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels sent to DeepSlice, comma separated (e.g. '0,2'), or '*' for all channels. Selected channels are merged into an RGB image with their current display settings (color and min/max).
        slice_spacing_um (float): Slice spacing (micrometers). Distance between consecutive slices. Only used with 'Keep order + set spacing (parameter below)'.
        """
        RegisterSlicesDeepSliceApposeCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceApposeCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceApposeCommand, True,
                                    'mp', self.mp,
                                    'allow_slicing_angle_change', allow_slicing_angle_change,
                                    'ensemble', ensemble,
                                    'model', model,
                                    'post_processing', post_processing,
                                    'slice_channels_csv', slice_channels_csv,
                                    'slice_spacing_um', slice_spacing_um,
                                    *self._optional_input('pixel_size_um', pixel_size_um)).get()

    def register_slices_deepslice_local(self,
            allow_slicing_angle_change: bool,
            ensemble: bool,
            model: str,
            post_processing: str,
            slice_channels_csv: str,
            slice_spacing_um: float,
            pixel_size_um: Optional[float] = None):
        """
        Obsolete, use 'ABBA - DeepSlice Registration' instead. Runs DeepSlice from a user-configured conda environment on the selected slices: sets their position along the slicing axis, adds an in-plane affine registration and optionally adjusts the atlas slicing angle.

        Parameters:
        allow_slicing_angle_change (bool): Adjust atlas slicing angle. If checked, the atlas slicing angles (X and Y rotations) are set to the median angle found by DeepSlice. This changes the slicing for all slices, not only the selected ones.
        ensemble (bool): Ensemble (average of several models, slower). If checked, DeepSlice averages the predictions of several models. Results may be better or not depending on the dataset: try both.
        model (str): DeepSlice model. Species DeepSlice was trained on: 'mouse' or 'rat'. It should match the atlas.
        pixel_size_um (float): Pixel size sent to DeepSlice (micrometers). Optional. Pixel size used to downsample the slices before sending them to DeepSlice. Defaults to 10.0 for mouse and 40.0 for rat; larger values are faster.
        post_processing (str): Position post-processing. How the slice positions predicted by DeepSlice are corrected. 'Keep order': the current slice order is preserved. 'Keep order + ensure regular spacing': order preserved and slices evenly spaced, spacing estimated by DeepSlice. 'Keep order + set spacing (parameter below)': order preserved and slices evenly spaced with the spacing given below. 'No post-processing': raw DeepSlice positions, slices may be reordered.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels sent to DeepSlice, comma separated (e.g. '0,2'), or '*' for all channels. Selected channels are merged into an RGB image with their current display settings (color and min/max).
        slice_spacing_um (float): Slice spacing (micrometers). Distance between consecutive slices. Only used with 'Keep order + set spacing (parameter below)'.
        """
        RegisterSlicesDeepSliceLocalCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceLocalCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceLocalCommand, True,
                                    'mp', self.mp,
                                    'allow_slicing_angle_change', allow_slicing_angle_change,
                                    'ensemble', ensemble,
                                    'model', model,
                                    'post_processing', post_processing,
                                    'slice_channels_csv', slice_channels_csv,
                                    'slice_spacing_um', slice_spacing_um,
                                    *self._optional_input('pixel_size_um', pixel_size_um)).get()

    def register_slices_deepslice_web(self,
            allow_slicing_angle_change: bool,
            maintain_slices_order: bool,
            model: str,
            slice_channels_csv: str,
            pixel_size_um: Optional[float] = None):
        """
        Obsolete, use 'ABBA - DeepSlice Registration' instead. Registers the selected slices with the DeepSlice web interface: the downsampled slices are sent to the website by hand, and the result file is loaded back. Requires a graphical user interface.

        Parameters:
        allow_slicing_angle_change (bool): Adjust atlas slicing angle. If checked, the atlas slicing angles (X and Y rotations) are set to the median angle found by DeepSlice. This changes the slicing for all slices, not only the selected ones.
        maintain_slices_order (bool): Keep slice order. If checked, slices keep their current order: slices swapped by DeepSlice are moved back.
        model (str): DeepSlice model. Species DeepSlice was trained on: 'mouse' or 'rat'. It should match the atlas.
        pixel_size_um (float): Pixel size sent to DeepSlice (micrometers). Optional. Pixel size used to downsample the slices before sending them to DeepSlice. Defaults to 10.0 for mouse and 40.0 for rat; larger values are faster.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels sent to DeepSlice, comma separated (e.g. '0,2'), or '*' for all channels. Selected channels are merged into an RGB image with their current display settings (color and min/max).
        """
        RegisterSlicesDeepSliceWebCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceWebCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceWebCommand, True,
                                    'mp', self.mp,
                                    'allow_slicing_angle_change', allow_slicing_angle_change,
                                    'maintain_slices_order', maintain_slices_order,
                                    'model', model,
                                    'slice_channels_csv', slice_channels_csv,
                                    *self._optional_input('pixel_size_um', pixel_size_um)).get()

    def register_slices_edit_last(self,
            atlas_channels_csv: str,
            reuse_original_channels: bool,
            slice_channels_csv: str):
        """
        Manually edits the last registration of each selected slice, if it is editable: spline registrations (Elastix spline, BigWarp) open in BigWarp, affine registrations (Elastix affine, manual, DeepSlice) open in the affine editor.

        Parameters:
        atlas_channels_csv (str): Atlas channels displayed. 0-based indices of the atlas channels displayed in the editor, comma separated (e.g. '0,2'), or '*' for all channels. Ignored if the channels used by the registration are displayed.
        reuse_original_channels (bool): Display the channels used by the registration. If checked, the editor displays the channels used when the registration was made, and the two channel fields below are ignored.
        slice_channels_csv (str): Slice channels displayed. 0-based indices of the slice channels displayed in the editor, comma separated (e.g. '0,2'), or '*' for all channels. Ignored if the channels used by the registration are displayed.
        """
        RegisterSlicesEditLastCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesEditLastCommand')
        return self.ij.command().run(RegisterSlicesEditLastCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'reuse_original_channels', reuse_original_channels,
                                    'slice_channels_csv', slice_channels_csv).get()

    def register_slices_elastix_affine(self,
            atlas_channels_csv: str,
            slice_channels_csv: str,
            pixel_size_um: float,
            show_imageplus_registration_result: bool = False):
        """
        Automatic in-plane affine registration (translation, rotation, scaling, shear) of the selected slices to the atlas with Elastix, restricted to the current region of interest. Atlas and slice channels are paired in order and must be equal in number.

        Parameters:
        atlas_channels_csv (str): Atlas channels. 0-based indices of the atlas channels to use, comma separated (e.g. '0,1'). '*' is not accepted. Channel indices are shown in the atlas display card.
        pixel_size_um (float): Registration pixel size (micrometers). Atlas and slices are resampled at this pixel size before being registered. Smaller is more precise but slower; 40 is a good start for a mouse brain.
        show_imageplus_registration_result (bool): Show registration images. If checked, the resampled atlas and slice images sent to Elastix are displayed as ImageJ images (for debugging).
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to use, comma separated (e.g. '0,1'). '*' is not accepted.
        """
        RegisterSlicesElastixAffineCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixAffineCommand')
        return self.ij.command().run(RegisterSlicesElastixAffineCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'pixel_size_um', pixel_size_um,
                                    'show_imageplus_registration_result', show_imageplus_registration_result,
                                    'slice_channels_csv', slice_channels_csv).get()

    def register_slices_elastix_spline(self,
            atlas_channels_csv: str,
            slice_channels_csv: str,
            nb_control_points_x: int,
            pixel_size_um: float,
            show_imageplus_registration_result: bool = False):
        """
        Automatic in-plane non-linear (B-spline) registration of the selected slices to the atlas with Elastix, restricted to the current region of interest. Usually run after an affine registration. Atlas and slice channels are paired in order and must be equal in number. The result can be edited in BigWarp.

        Parameters:
        atlas_channels_csv (str): Atlas channels. 0-based indices of the atlas channels to use, comma separated (e.g. '0,1'). '*' is not accepted. Channel indices are shown in the atlas display card.
        nb_control_points_x (int): Number of control points along X. Size of the B-spline control point grid along X (minimum 2), the Y count follows the region of interest aspect ratio. More points allow more local deformations.
        pixel_size_um (float): Registration pixel size (micrometers). Atlas and slices are resampled at this pixel size before being registered. Smaller is more precise but slower; 20 is a good start for a mouse brain.
        show_imageplus_registration_result (bool): Show registration images. If checked, the resampled atlas and slice images sent to Elastix are displayed as ImageJ images (for debugging).
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to use, comma separated (e.g. '0,1'). '*' is not accepted.
        """
        RegisterSlicesElastixSplineCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixSplineCommand')
        return self.ij.command().run(RegisterSlicesElastixSplineCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'nb_control_points_x', nb_control_points_x,
                                    'pixel_size_um', pixel_size_um,
                                    'show_imageplus_registration_result', show_imageplus_registration_result,
                                    'slice_channels_csv', slice_channels_csv).get()

    def register_slices_manual_affine(self,
            atlas_channels_csv: str,
            slice_channels_csv: str):
        """
        Manual in-plane affine registration: moves, rotates, scales and shears the selected slices with a gizmo, in a single dedicated window. Selected channels are only used for display. The result can be edited later.

        Parameters:
        atlas_channels_csv (str): Atlas channels. 0-based indices of the atlas channels to use, comma separated (e.g. '0,1'). '*' is not accepted. Channel indices are shown in the atlas display card.
        slice_channels_csv (str): Slice channels. 0-based indices of the slice channels to use, comma separated (e.g. '0,1'). '*' is not accepted.
        """
        RegisterSlicesManualAffineCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesManualAffineCommand')
        return self.ij.command().run(RegisterSlicesManualAffineCommand, True,
                                    'mp', self.mp,
                                    'atlas_channels_csv', atlas_channels_csv,
                                    'slice_channels_csv', slice_channels_csv).get()

    def register_slices_remove_last(self):
        """
        Removes the last registration of each selected slice (it can be undone).

        """
        RegisterSlicesRemoveLastCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesRemoveLastCommand')
        return self.ij.command().run(RegisterSlicesRemoveLastCommand, True,
                                    'mp', self.mp).get()

    def reindex_slices(self,
            new_channel_order_csv: str):
        """
        Reorders, removes or duplicates the channels of the selected slices. Each selected slice is replaced by a new slice with the new channels, at the same position and with the same registrations. The same channel order is applied to all selected slices.

        Parameters:
        new_channel_order_csv (str): New channel order. Comma separated 0-based indices of the original channels, in their new order: '0,2' keeps the first and third channels, '1,0' swaps the first two channels.
        """
        ReindexSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.ReindexSlicesCommand')
        return self.ij.command().run(ReindexSlicesCommand, True,
                                    'mp', self.mp,
                                    'new_channel_order_csv', new_channel_order_csv).get()

    def rotate_slices(self,
            angle_degrees: float,
            axis_string: str):
        """
        Rotates the selected slices around the center of the registration ROI. Z: in-plane rotation, clockwise on screen. X or Y: 180 or -180 degrees only (flip)

        Parameters:
        angle_degrees (float): Angle (degrees). Rotation angle. Around Z, positive is clockwise on screen.
        axis_string (str): Rotation axis. 'Z': in-plane rotation, any angle. 'X' or 'Y': flips the section upside down or left-right, only 180 or -180 degrees are accepted.
        """
        RotateSlicesCommand = jimport('ch.epfl.biop.atlas.aligner.command.RotateSlicesCommand')
        return self.ij.command().run(RotateSlicesCommand, True,
                                    'mp', self.mp,
                                    'angle_degrees', angle_degrees,
                                    'axis_string', axis_string).get()

    def set_slices_background(self,
            white_background_value: int):
        """
        For brightfield images with a white background: the area outside of the selected slices images is filled with this value instead of black, which avoids dark edges during registrations and exports. Works for 8-bit, 16-bit and RGB images.

        Parameters:
        white_background_value (int): Background value. Pixel value used outside of the images: 255 for 8-bit or RGB images, 65535 for 16-bit images.
        """
        SetSlicesBackgroundCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesBackgroundCommand')
        return self.ij.command().run(SetSlicesBackgroundCommand, True,
                                    'mp', self.mp,
                                    'white_background_value', white_background_value).get()

    def set_slices_deselected(self,
            slices_csv: str):
        """
        Removes slices from the current selection, by index. Other slices keep their selection state.

        Parameters:
        slices_csv (str): Slice indices. 0-based indices of the slices, in the order along the slicing axis. '*' for all slices, comma separated values ('0,3'), inclusive ranges ('2:5'), ranges with a step ('0:2:10'). Negative indices count from the end: -1 is the last slice.
        """
        SetSlicesDeselectedCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesDeselectedCommand')
        return self.ij.command().run(SetSlicesDeselectedCommand, True,
                                    'mp', self.mp,
                                    'slices_csv', slices_csv).get()

    def set_slices_display_range(self,
            display_max: float,
            display_min: float,
            slice_channels_csv: str):
        """
        Sets the display range (min and max displayed values) of channels of the selected slices. Besides the display, it changes the images sent to DeepSlice: avoid saturated images.

        Parameters:
        display_max (float): Display max. Pixel value displayed at full brightness; higher values are saturated.
        display_min (float): Display min. Pixel value displayed as black.
        slice_channels_csv (str): Channels. 0-based indices of the channels to adjust, comma separated (e.g. '0,2'), or '*' for all channels. Channels missing in a slice are skipped.
        """
        SetSlicesDisplayRangeCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesDisplayRangeCommand')
        return self.ij.command().run(SetSlicesDisplayRangeCommand, True,
                                    'mp', self.mp,
                                    'display_max', display_max,
                                    'display_min', display_min,
                                    'slice_channels_csv', slice_channels_csv).get()

    def set_slices_selected(self,
            slices_csv: str):
        """
        Adds slices to the current selection, by index. Already selected slices stay selected. Most commands act on the selected slices.

        Parameters:
        slices_csv (str): Slice indices. 0-based indices of the slices, in the order along the slicing axis. '*' for all slices, comma separated values ('0,3'), inclusive ranges ('2:5'), ranges with a step ('0:2:10'). Negative indices count from the end: -1 is the last slice.
        """
        SetSlicesSelectedCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesSelectedCommand')
        return self.ij.command().run(SetSlicesSelectedCommand, True,
                                    'mp', self.mp,
                                    'slices_csv', slices_csv).get()

    def set_slices_thickness(self,
            thickness_um: float):
        """
        Sets the thickness of the selected slices along the slicing axis. It affects the 3D display (reconstructed brain) and the 3D resampled export, not the registrations.

        Parameters:
        thickness_um (float): Slice thickness (micrometers). Thickness of each selected slice, centered on its position.
        """
        SetSlicesThicknessCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessCommand')
        return self.ij.command().run(SetSlicesThicknessCommand, True,
                                    'mp', self.mp,
                                    'thickness_um', thickness_um).get()

    def set_slices_thickness_match_neighbors(self):
        """
        Sets the thickness of each selected slice so that it extends halfway to its neighbors, leaving no gap between slices. It affects the 3D display (reconstructed brain) and the 3D resampled export, not the registrations.

        """
        SetSlicesThicknessMatchNeighborsCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessMatchNeighborsCommand')
        return self.ij.command().run(SetSlicesThicknessMatchNeighborsCommand, True,
                                    'mp', self.mp).get()
