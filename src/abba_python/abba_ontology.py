from brainglobe_atlasapi import BrainGlobeAtlas
from brainglobe_atlasapi.descriptors import STRUCTURES_FILENAME
from scyjava import jimport
from jpype import JImplements, JOverride
from jpype.types import JString

AtlasHelper = jimport('ch.epfl.biop.atlas.struct.AtlasHelper')
AtlasOntology = jimport('ch.epfl.biop.atlas.struct.AtlasOntology')


@JImplements(AtlasOntology)
class AbbaOntology(object):
    """This python class is part of the translation mechanism between the underlying Java ABBA API:
    https://github.com/BIOP/ijp-atlas/tree/main/src/main/java/ch/epfl/biop/atlas/struct
    and the BrainGlobe API:
    https://github.com/brainglobe/bg-atlasapi/

    Wrapper inner class that implements the following Java interface:
    https://github.com/BIOP/ijp-atlas/blob/main/src/main/java/ch/epfl/biop/atlas/struct/AtlasOntology.java
    """

    def __init__(self, bg_atlas: BrainGlobeAtlas):
        self.atlas = bg_atlas

    @JOverride
    def getName(self):
        return JString(self.atlas.atlas_name)

    @JOverride
    def initialize(self):
        BrainGlobeHelper = jimport('ch.epfl.biop.atlas.brainglobe.BrainGlobeHelper')
        print(str(self.atlas.root_dir / STRUCTURES_FILENAME))
        print(BrainGlobeHelper)
        print(BrainGlobeHelper.buildTreeAndGetRoot)
        self.root_node = BrainGlobeHelper.buildTreeAndGetRoot(JString(
            str(self.atlas.root_dir / STRUCTURES_FILENAME)))  # AbbaAtlasNode(self.atlas,
        # self.atlas.structures.tree.root, None)
        self.idToAtlasNodeMap = AtlasHelper.buildIdToAtlasNodeMap(self.root_node)

    # noinspection PyPep8Naming
    @JOverride
    def setDataSource(self, dataSource):
        self.dataSource = dataSource

    @JOverride
    def getDataSource(self):
        return self.dataSource  # return URL

    @JOverride
    def getRoot(self):
        return self.root_node  # return AtlasNode

    @JOverride
    def getNodeFromId(self, index):
        return self.idToAtlasNodeMap.get(index)  # return AtlasNode

    @JOverride
    def getNamingProperty(self):
        return self.namingProperty

    # noinspection PyPep8Naming
    @JOverride
    def setNamingProperty(self, namingProperty):
        self.namingProperty = namingProperty
