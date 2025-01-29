from brainglobe_atlasapi import BrainGlobeAtlas
from scyjava import jimport
from jpype import JImplements, JOverride
from jpype.types import JString, JDouble, JInt
from itertools import zip_longest

import numpy as np

AffineTransform3D = jimport('net.imglib2.realtransform.AffineTransform3D')
ArrayList = jimport('java.util.ArrayList')
AtlasHelper = jimport('ch.epfl.biop.atlas.struct.AtlasHelper')
AtlasMap = jimport('ch.epfl.biop.atlas.struct.AtlasMap')
BdvFunctions = jimport('bdv.util.BdvFunctions')
BdvOptions = jimport('bdv.util.BdvOptions')
SourceVoxelProcessor = jimport('ch.epfl.biop.sourceandconverter.SourceVoxelProcessor')

RandomAccessibleIntervalSource = jimport('bdv.util.RandomAccessibleIntervalSource')
Util = jimport('net.imglib2.util.Util')
SourceAndConverterHelper = jimport('sc.fiji.bdvpg.sourceandconverter.SourceAndConverterHelper')

SourceAndConverterServices = jimport('sc.fiji.bdvpg.services.SourceAndConverterServices')
ARGBType = jimport('net.imglib2.type.numeric.ARGBType')

def array_to_source(ij, array, name,
                    color=None,
                    transform=AffineTransform3D()):
    img = ij.py.to_java(array)
    name_java_str = JString(name)
    # we supposed it's of dimension 3
    pixel_type = Util.getTypeFromInterval(img)
    rai_source = RandomAccessibleIntervalSource(img, pixel_type, transform, name_java_str)
    source = SourceAndConverterHelper.createSourceAndConverter(rai_source)
    converter_setup = SourceAndConverterServices.getSourceAndConverterService().getConverterSetup(source)
    # converter_setup.setDisplayRange(JDouble(0),JDouble(200)) <- This won't have any effect, because I think it's overriden after, but the syntax is correct
    if color is None:
        color = WHITE
    converter_setup.setColor(ARGBType(color))
    return source

WHITE = ARGBType.rgba(255, 255, 255, 255)
LIGHT_BLUE = ARGBType.rgba(30, 136, 229, 255)
ORANGE = ARGBType.rgba(255, 193, 7, 255)

@JImplements(AtlasMap)
class AbbaMap(object):
    """This python class is part of the translation mechanism between the underlying Java ABBA API:
    https://github.com/BIOP/ijp-atlas/tree/main/src/main/java/ch/epfl/biop/atlas/struct
    and the BrainGlobe API:
    https://github.com/brainglobe/bg-atlasapi/

    Wrapper inner class that implements the following Java interface:
    https://github.com/BIOP/ijp-atlas/blob/main/src/main/java/ch/epfl/biop/atlas/struct/AtlasMap.java
    """

    def __init__(self, bg_atlas: BrainGlobeAtlas, ij):
        # this function is called way too many times if I put here the content
        # of initialize... and I don't know why
        # that's why there's this initialize function
        self.atlas = bg_atlas
        self.ij = ij

    # noinspection PyPep8Naming
    @JOverride
    def setDataSource(self, dataSource):
        self.dataSource = dataSource

    # noinspection PyPep8Naming
    @JOverride
    def initialize(self, atlasName):
        self.atlasName = str(atlasName)

        atlas_resolution_in__mm = JDouble(min(self.atlas.metadata['resolution']) / 1000.0)

        vox_x_mm = self.atlas.metadata['resolution'][2] / 1000.0
        vox_y_mm = self.atlas.metadata['resolution'][1] / 1000.0
        vox_z_mm = self.atlas.metadata['resolution'][0] / 1000.0

        affine_transform = AffineTransform3D()
        affine_transform.scale(JDouble(vox_x_mm), JDouble(vox_y_mm), JDouble(vox_z_mm))

        transform_to_asr = AffineTransform3D()

        expected_orientation = "asr"
        axes_str = self.atlas.orientation
        if axes_str != expected_orientation:
            raise ValueError(f"Invalid orientation: expected '{expected_orientation}', but got '{axes_str}'.")

        affine_transform = affine_transform.preConcatenate(transform_to_asr)

        # Convert
        reference_sac = array_to_source(self.ij, self.atlas.reference,
                                        name=self.atlas.atlas_name + '_reference',
                                        color=LIGHT_BLUE,
                                        transform=affine_transform)

        left_right_sac = array_to_source(self.ij, self.atlas.hemispheres,
                                         name=self.atlas.atlas_name + '_hemispheres',
                                         transform=affine_transform)

        self.annotation_sac = array_to_source(self.ij, self.atlas.annotation,
                                              name=self.atlas.atlas_name + '_annotation',
                                              transform=affine_transform)

        image_keys = ArrayList()
        image_keys.add(JString('reference'))
        for extra_channel in self.atlas.metadata['additional_references']:
            image_keys.add(JString(extra_channel))
        image_keys.add(JString('borders'))
        image_keys.add(JString('X'))
        image_keys.add(JString('Y'))
        image_keys.add(JString('Z'))
        image_keys.add(JString('Left Right'))

        structural_images = dict()
        self.maxValues = dict()
        structural_images['reference'] = reference_sac
        print("Max = "+str(np.max(self.atlas.reference)))
        self.maxValues['reference'] = JDouble(np.max(self.atlas.reference.astype(np.float64)) * 2)
        for extra_channel, color in zip_longest(self.atlas.metadata['additional_references'], (ORANGE,)):
            if extra_channel is None:
                # zip_longest() added a padded value
                continue
            structural_images[extra_channel] = array_to_source(self.ij, self.atlas.additional_references[extra_channel],
                                                               name=self.atlas.atlas_name + '_' + extra_channel,
                                                               color=color,
                                                               transform=affine_transform)
            self.maxValues[extra_channel] = JDouble(np.max(self.atlas.additional_references[extra_channel].astype(np.float64)) * 2)
        structural_images['borders'] = SourceVoxelProcessor.getBorders(self.annotation_sac)
        self.maxValues['borders'] = 256  # we know this one.
        structural_images['X'] = AtlasHelper.getCoordinateSac(0, JString('X'))
        structural_images['Y'] = AtlasHelper.getCoordinateSac(1, JString('Y'))
        structural_images['Z'] = AtlasHelper.getCoordinateSac(2, JString('Z'))
        structural_images['Left Right'] = left_right_sac

        self.atlas_resolution_in__mm = atlas_resolution_in__mm
        self.affine_transform = affine_transform
        self.image_keys = image_keys
        self.structural_images = structural_images

    @JOverride
    def getDataSource(self):
        return self.dataSource  # return URL

    @JOverride
    def getStructuralImages(self):
        return self.structural_images

    @JOverride
    def getImagesKeys(self):
        return self.image_keys

    @JOverride
    def getLabelImage(self):
        return self.annotation_sac  # SourceAndConverter

    @JOverride
    def getAtlasPrecisionInMillimeter(self):
        return self.atlas_resolution_in__mm

    @JOverride
    def getCoronalTransform(self) -> AffineTransform3D:
        return AffineTransform3D()

    @JOverride
    def getImageMax(self, key):
        return self.maxValues[key]

    @JOverride
    def labelRight(self):
        return JInt(2)

    @JOverride
    def labelLeft(self):
        return JInt(1)
