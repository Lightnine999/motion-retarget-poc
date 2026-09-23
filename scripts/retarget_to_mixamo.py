import torch
from motius.motion import export_motion_to_fbx

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)
p = d["smpl_params_global"]

motion_data = {
    "global_orient": p["global_orient"].numpy(),
    "body_pose": p["body_pose"].numpy(),
    "transl": p["transl"].numpy(),
    "betas": p["betas"].numpy(),
}

result = export_motion_to_fbx(
    motion_data,
    source_representation="smpl",
    character_fbx="blender/assets/mixamo_character.fbx",
    output_path="outputs/kaggle_tennis/mixamo_retargeted.fbx",
    model_path="inputs/checkpoints/body_models/smpl/SMPL_NEUTRAL.pkl",
    model_type="smpl",
    gender="neutral",
    source_fps=30.0,
    output_fps=30,
    backend="blender",
)
print("output_path:", result.output_path)
print("manifest_path:", result.manifest_path)
print("armature_name:", result.armature_name)
print("bone_map:", result.bone_map)
import json
print(json.dumps(result.metadata, indent=2)[:3000])
