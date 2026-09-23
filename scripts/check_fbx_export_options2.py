import bpy
op = bpy.ops.export_scene.fbx
rna = op.get_rna_type()
for prop in rna.properties:
    print(prop.identifier)
