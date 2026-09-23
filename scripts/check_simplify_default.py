import bpy
op = bpy.ops.export_scene.fbx
rna = op.get_rna_type()
for prop in rna.properties:
    if prop.identifier == "bake_anim_simplify_factor":
        print("default:", prop.default, "min:", prop.hard_min, "max:", prop.hard_max, "desc:", prop.description)
