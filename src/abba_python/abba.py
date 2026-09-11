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
            'ch.epfl.biop:bigdataviewer-biop-tools:0.23.1',
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

    # ------------------------ Hand-made in-plane corrections
    # A registration is appended after the existing ones: a row-packed matrix [m00 m01 0 tx, m10 m11 0 ty,
    # 0 0 1 0] moves each point p of the registered slice to M p + t, in mm, in the aligner coordinates
    # of the snapshots (x to the right, y down). Rotation direction is easy to misjudge on images:
    # check a correction with compare() and its Dice scores.

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

    def get_fit_scores(self, slices: Optional[Sequence[int]] = None, pixel_size_mm: float = 0.05,
                       **options: Any) -> list:
        """
        Dice between the tissue mask and the atlas brain mask of each slice (1 = perfect overlap),
        requires a recent ImageToAtlasRegister (SliceSnapshot.tissueAtlasDice)

        :param options: SliceSnapshot.Options fields, e.g. registrationStepBack=1 to score the
            state before the last registration, atlasSlicingAxisPositionMm to score a candidate z
        :return: list of (index, name, dice)
        """
        SliceSnapshot, java_options = self._snapshot_options(dict(options, pixelSizeMm=pixel_size_mm))
        indices = range(self.get_n_slices()) if slices is None else slices
        return [(i, str(s.getName()), float(SliceSnapshot.tissueAtlasDice(self.mp, s, java_options)))
                for i, s in zip(indices, self._get_slices(list(indices)))]

    def compare(self, index: int, path: str, **options: Any) -> dict:
        """
        Saves a PNG with the slice before (left) and after (right) its last registration, and
        returns the tissue / atlas Dice scores when the ImageToAtlasRegister version provides them

        :param options: SliceSnapshot.Options fields, see snapshot
        :return: dict with path, dice_before, dice_after (None when unavailable)
        """
        ArrayList = jimport('java.util.ArrayList')
        slice_ = self._get_slices([index])[0]
        steps_back = [1, 0] if int(slice_.getNumberOfRegistrations()) > 0 else [0]
        images = ArrayList()
        dice = []
        for step_back in steps_back:
            SliceSnapshot, java_options = self._snapshot_options(dict(options, registrationStepBack=step_back))
            images.add(SliceSnapshot.render(self.mp, slice_, java_options))
            if hasattr(SliceSnapshot, 'tissueAtlasDice'):
                dice.append(float(SliceSnapshot.tissueAtlasDice(self.mp, slice_, java_options)))
            else:
                dice.append(None)
        saved = str(SliceSnapshot.save(SliceSnapshot.tile(images, len(steps_back)), path))
        return {'path': saved, 'dice_before': dice[0] if len(dice) == 2 else None, 'dice_after': dice[-1]}

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
        ExportDeformationFieldToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportDeformationFieldToImageJCommand')
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
        ExportRegistrationToQuPathCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportRegistrationToQuPathCommand')
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
        ExportResampledSlicesToBDVSourceCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportResampledSlicesToBDVSourceCommand')
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
        ExportSlicesOriginalDataToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesOriginalDataToImageJCommand')
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
        ExportSlicesToBDVJsonDatasetCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToBDVJsonDatasetCommand')
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
        ExportSlicesToQuickNIIDatasetCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportSlicesToQuickNIIDatasetCommand')
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
        ExportTransformedAtlasToImageJCommand = jimport('ch.epfl.biop.atlas.aligner.command.ExportTransformedAtlasToImageJCommand')
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
        RegisterSlicesCopyAndApplyCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesCopyAndApplyCommand')
        return self.ij.command().run(RegisterSlicesCopyAndApplyCommand, True,
                                    'mp', self.mp,
                                    'model_slice_index', model_slice_index,
                                    'skip_pre_transform', skip_pre_transform).get()

    def register_slices_deepslice_appose(self,
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
        RegisterSlicesDeepSliceApposeCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceApposeCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceApposeCommand, True,
                                    'mp', self.mp,
                                    'allow_slicing_angle_change', allow_slicing_angle_change,
                                    'channels', channels,
                                    'ensemble', ensemble,
                                    'model', model,
                                    'post_processing', post_processing,
                                    'px_size_micron', px_size_micron,
                                    'slices_spacing_micrometer', slices_spacing_micrometer).get()

    def register_slices_deepslice_local(self,
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
        RegisterSlicesDeepSliceLocalCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceLocalCommand')
        return self.ij.command().run(RegisterSlicesDeepSliceLocalCommand, True,
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
        RegisterSlicesDeepSliceWebCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesDeepSliceWebCommand')
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
        RegisterSlicesElastixAffineCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixAffineCommand')
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
        RegisterSlicesElastixSplineCommand = jimport('ch.epfl.biop.atlas.aligner.command.RegisterSlicesElastixSplineCommand')
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
        SetSlicesThicknessMatchNeighborsCommand = jimport('ch.epfl.biop.atlas.aligner.command.SetSlicesThicknessMatchNeighborsCommand')
        return self.ij.command().run(SetSlicesThicknessMatchNeighborsCommand, True,
                                    'mp', self.mp).get()
