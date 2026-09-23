import bpy
op = bpy.ops.export_scene.fbx
rna = op.get_rna_type()
for prop in rna.properties:
    if "quat" in prop.identifier.lower() or "rotation" in prop.identifier.lower() or "interp" in prop.identifier.lower():
        print(prop.identifier, "-", prop.description)
