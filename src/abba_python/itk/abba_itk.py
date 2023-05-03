from scyjava import jimport
from jpype import JImplements, JOverride
from jpype.types import JString, JDouble, JInt
import os

from src.abba_python.scijava_python_command import ScijavaCommand, ScijavaInput
import itk
import numpy as np
import tempfile

ExternalABBARegistrationPlugin = jimport('ch.epfl.biop.atlas.aligner.plugin.ExternalABBARegistrationPlugin')
AffineTransform3D = jimport('net.imglib2.realtransform.AffineTransform3D')
MultiSlicePositioner = jimport('ch.epfl.biop.atlas.aligner.MultiSlicePositioner')

Supplier = jimport('java.util.function.Supplier')

Command = jimport('org.scijava.command.Command')
JPlugin = jimport('org.scijava.plugin.Plugin')
Parameter = jimport('org.scijava.plugin.Parameter')
ImagePlus = jimport('ij.ImagePlus')

SimpleABBARegistrationPlugin = jimport('ch.epfl.biop.atlas.aligner.plugin.SimpleABBARegistrationPlugin')

ElastixTransform = jimport('itc.transforms.elastix.ElastixTransform')
ElastixEuler2DToAffineTransform3D = jimport('itc.converters.ElastixEuler2DToAffineTransform3D')
File = jimport('java.io.File')

SourcesChannelsSelect = jimport('ch.epfl.biop.sourceandconverter.processor.SourcesChannelsSelect')
HashMap = jimport('java.util.HashMap')
SimpleRegistrationWrapper = jimport('ch.epfl.biop.atlas.aligner.plugin.SimpleRegistrationWrapper')


@JImplements(SimpleABBARegistrationPlugin)
class ITKRigidRegistration(object):

    def __init__(self, ij):
        print('init SimpleRotateAffineRegistration')
        self.ij = ij
        pass

    # @return Sampling required for the registration, in micrometer (double)
    #
    @JOverride
    def getVoxelSizeInMicron(self):
        return JDouble(40)

    # Is called before registration to pass any extra registration parameter
    # argument. Passed as a dictionary of String to preserve serialization
    # capability.
    # param parameters dictionary of parameters (Map<String, String>)
    @JOverride
    def setRegistrationParameters(self, parameters):
        self.parameters = parameters

    # param fixed image (ImagePlus)
    # param moving image (ImagePlus)
    # param fixed mask (ImagePlus)
    # param moving mask (ImagePlus)
    # return the transform, result of the registration, (InvertibleRealTransform)
    # going from fixed to moving coordinates, in pixels
    @JOverride
    def register(self, fixed, moving, fixedMask, movingMask):
        # fixed.show()
        # moving.show()
        # ij.py.show(fixed)
        # ij.py.show(moving)

        # global parameter_object
        parameter_object = itk.ParameterObject.New()
        default_rigid_parameter_map = parameter_object.GetDefaultParameterMap('rigid')
        parameter_object.AddParameterMap(default_rigid_parameter_map)

        # global fixed_py
        # global moving_py
        fixed_py = self.ij.py.from_java(fixed)
        moving_py = self.ij.py.from_java(moving)
        fixed_py = fixed_py.to_numpy().astype(np.float32)
        moving_py = moving_py.to_numpy().astype(np.float32)

        # Call registration function
        with tempfile.TemporaryDirectory() as temp_dir:
            # ... do something with temp_dir
            itk.elastix_registration_method(
                fixed_py, moving_py,
                output_directory=temp_dir,
                parameter_object=parameter_object,
                log_to_console=False)
            output_path = os.path.join(temp_dir, 'TransformParameters.0.txt')
            et = ElastixTransform.load(File(output_path))
            transform = ElastixEuler2DToAffineTransform3D.convert(et)

        # temp dir automatically cleaned up when context exited
        return transform


@JImplements(Supplier)
class ITKRigidRegistrationSupplier(object):

    def __init__(self, ij):
        self.ij = ij
        pass

    @JOverride
    def get(self):
        return SimpleRegistrationWrapper(JString('ITKRigidRegistration'),
                                         ITKRigidRegistration(self.ij))


def add_abba_itk_registrations(ij):
    MultiSlicePositioner.registerRegistrationPlugin('ITKRigidRegistration',
                                                    ITKRigidRegistrationSupplier(ij))

    @ScijavaCommand(context=ij.context(),  # ij context needed
                    name='ITK - Rigid Registration')
    @ScijavaInput('fixed_channel', JInt,
                  label='Atlas channel index:', description='')
    @ScijavaInput('moving_channel', JInt,
                  label='Section channel index', description='')
    @ScijavaInput('mp', MultiSlicePositioner,
                  label='Section channel index', description='')
    class SimpleRotateAffineRegistrationCommand:
        def run(self):
            params = HashMap()
            self.mp.registerSelectedSlices('ITKRigidRegistration',
                                           SourcesChannelsSelect(self.fixed_channel),
                                           SourcesChannelsSelect(self.moving_channel),
                                           params)

    MultiSlicePositioner.registerRegistrationPluginUI('ITKRigidRegistration',
                                                      'ITK - Rigid Registration');
