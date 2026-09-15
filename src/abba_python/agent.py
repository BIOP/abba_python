"""
Agent API: read the state of an ABBA session as text, act with JSON actions, look at slices as images
"""

import inspect
import json
import time
from typing import Any, Optional, Sequence

from scyjava import jimport

from .abba import Abba
from .command_metadata import ABBA_COMMANDS, REGISTRATION_COMMANDS
from .commands import AbbaCommands


class AbbaAgent:
    """
    Drives an Abba session for a program, for instance an LLM agent

    Slices are addressed by their index, which follows the z order and changes when a slice
    moves: re-read the state after each apply.

    Example::

        abba = Abba('Adult Mouse Brain - Allen Brain Atlas V3p1', headless=True)
        agent = AbbaAgent(abba)
        agent.describe_state()
    """

    def __init__(self, abba: Abba):
        self.abba = abba
        self.ij = abba.ij
        self.mp = abba.mp
        # Collects ABBA's error, warning and info messages, see get_messages
        self._messages: list = []
        self._subscribe_to_messages()
        # userActionsSize() after each batch created by apply / delete_slices (see undo)
        self._undoable_batches: list = []
        self._redoable_batches: list = []

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

        Described from the SciJava command the registration runs
        (ch.epfl.biop.command.register.<type without 'Registration'>RegisterCommand), see
        command_metadata.REGISTRATION_COMMANDS. All values have to be passed as strings. px, py, sx
        and sy (the region of interest, in mm) default to the current ROI.

        :return: dict name -> {type, label, description, default, choices, required, style, min, max},
            see get_command_parameters; defaults are strings here
        """
        if registration_type == 'AffineRegistration':
            return {'transform': {'type': 'String', 'default': '[1,0,0,0, 0,1,0,0, 0,0,1,0]',
                                  'label': 'Row-packed 3x4 affine matrix',
                                  'description': 'Applied to the registered slice positions, in mm, '
                                                 'see translate_slice'},
                    'pz': {'type': 'String', 'default': '0', 'label': 'z position', 'description': ''}}
        command_name = registration_type.removesuffix('Registration') + 'RegisterCommand'
        command = REGISTRATION_COMMANDS.get(command_name)
        if command is None:
            raise ValueError(f'No register command {command_name} for {registration_type}')
        parameters = {}
        for item in command['input']:
            if item['name'] in self._REGISTRATION_PLUGIN_INPUTS:
                continue
            parameter = {key: item.get(key, True if key == 'required' else None) for key in self._INPUT_KEYS}
            if item['name'] in ('px', 'py', 'sx', 'sy'):
                parameter['default'] = 'optional, current ROI'
            elif parameter['default'] is not None:
                parameter['default'] = str(parameter['default'])
            parameters[item['name']] = parameter
        return parameters

    # Keys of each input returned by get_command_parameters
    _INPUT_KEYS = ('type', 'label', 'description', 'default', 'choices', 'required', 'style', 'min', 'max')

    def describe_commands(self) -> list:
        """
        The ABBA commands that have a method in Abba, with what they do and the messages their dialog shows

        Read from command_metadata, generated with the commands. get_command_parameters() gives the
        inputs of one.

        :return: list of dicts with keys name (class), method (of Abba), title, description, messages,
            sorted by name
        """
        return [{'name': name,
                 'method': command['method'],
                 'title': command.get('label') or command.get('menuPath', name).rsplit('>', 1)[-1],
                 'description': command.get('description', ''),
                 'messages': command.get('messages', [])}
                for name, command in ABBA_COMMANDS.items() if 'method' in command]

    def get_command_parameters(self, command_name: str, initialized: bool = True) -> dict:
        """
        Parameters of the Abba method running an ABBA command: whether they are required, their default
        and, for a list of choices (post_processing...), the exact strings accepted

        Labels, descriptions and choices come from command_metadata; required and default from the
        method signature. Some commands compute defaults or choices when they open, from the session
        (DeepSlice pixel size, ontology keys of naming_choice): with initialized=True, they are
        created and initialized, without running, to report these values.

        :param command_name: class name, e.g. 'RegisterSlicesDeepSliceApposeCommand', or method name,
            e.g. 'register_slices_deepslice_appose', see describe_commands()
        :param initialized: report the values computed when the command opens, if any
        :return: dict name -> {type (Java), label, description, default, choices, required, style,
            min, max}. A parameter that is not required and has a None default is computed by the
            command: default then gives the value it computes now, if initialized
        """
        matches = [(name, command) for name, command in ABBA_COMMANDS.items()
                   if 'method' in command and command_name in (name, command['method'])]
        if not matches:
            raise ValueError(f'No ABBA command named {command_name}, see describe_commands()')
        command = matches[0][1]
        items = command['input']
        if initialized and (command.get('hasInitializer') or command.get('dynamic')):
            items = self._initialized_inputs(command)
        signature = inspect.signature(getattr(AbbaCommands, command['method']))
        parameters = {}
        for item in items:
            parameter = signature.parameters.get(item['name'].lower())
            if parameter is None:
                continue  # the session, set by the method
            required = parameter.default is inspect.Parameter.empty
            default = None if required else parameter.default
            if default is None and not required and initialized:
                default = item.get('default')
            parameters[parameter.name] = dict(
                {key: item.get(key) for key in self._INPUT_KEYS}, default=default, required=required)
        return parameters

    def _initialized_inputs(self, command: dict) -> list:
        """Inputs of a command created with this session and initialized, see scijava-introspect"""
        HashMap = jimport('java.util.HashMap')
        preset = HashMap()
        for item in command['input']:
            if item['type'] == 'MultiSlicePositioner':
                preset.put(item['name'], self.mp)
        introspector = jimport('ch.unige.biochem.scijava.introspect.CommandIntrospector')
        described = introspector.describeInitialized(self.ij.context(), jimport(command['name']).class_, preset)
        return json.loads(str(described))['input']

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

        :param index: slice index, or None to render the atlas only (set atlasZMm)
        :param path: PNG file path
        :param options: fields of ch.epfl.biop.atlas.aligner.inspect.SliceSnapshot.Options, e.g.
            pixelSizeMm=0.025, atlasChannel=0, registrationStepBack=1, atlasZMm=6.5
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
                dict(options, atlasZMm=float(z), atlasChannel=atlas_channel))
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
