from bg_atlasapi import BrainGlobeAtlas
from scyjava import jimport
from jpype import JImplements, JOverride
from jpype.types import JString
from abba_python.abba_private.AbbaOntology import AbbaOntology
from abba_python.abba_private.AbbaMap import AbbaMap

ArrayList = jimport('java.util.ArrayList')
Atlas = jimport('ch.epfl.biop.atlas.struct.Atlas')


@JImplements(Atlas)
class AbbaAtlas(object):
    """This python class is part of the translation mechanism between the underlying Java ABBA API:
    https://github.com/BIOP/ijp-atlas/tree/main/src/main/java/ch/epfl/biop/atlas/struct
    and the BrainGlobe API:
    https://github.com/brainglobe/bg-atlasapi/

    Wrapper inner class that implements the following Java interface:
    https://github.com/BIOP/ijp-atlas/blob/main/src/main/java/ch/epfl/biop/atlas/struct/Atlas.java
    """

    def __init__(self, bg_atlas: BrainGlobeAtlas, ij):
        self.atlas = bg_atlas
        self.ij = ij

    @JOverride
    def getMap(self):
        return self.bg_atlasmap

    @JOverride
    def getOntology(self):
        return self.bg_ontology

    @JOverride
    def initialize(self, mapURL, ontologyURL):
        self.bg_ontology = AbbaOntology(self.atlas)
        self.bg_ontology.initialize()
        self.bg_ontology.setNamingProperty(JString('acronym'))
        self.bg_atlasmap = AbbaMap(self.atlas, self.ij)
        self.bg_atlasmap.initialize(self.atlas.atlas_name)
        self.dois = ArrayList()
        self.dois.add(JString(self.atlas.metadata['citation'].split("doi.org/", 1)[1]))

    @JOverride
    def getDOIs(self):
        return self.dois

    @JOverride
    def getURL(self):
        return JString(self.atlas.metadata['atlas_link'])

    @JOverride
    def getName(self):
        return JString(self.atlas.atlas_name)

    @JOverride
    def toString(self):
        return self.getName()
