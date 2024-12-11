from brainglobe_atlasapi import show_atlases, BrainGlobeAtlas

show_atlases()
atlas = BrainGlobeAtlas("prairie_vole_25um")
print(atlas.orientation)