import torch
from motius.motion import export_smpl_fbx
from motius.motion.fbx.bridge import motion_to_smpl_animation

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)
p = d["smpl_params_global"]

motion_data = {
    "global_orient": p["global_orient"].numpy(),
    "body_pose": p["body_pose"].numpy(),
    "transl": p["transl"].numpy(),
    "betas": p["betas"].numpy(),
}

bridge = motion_to_smpl_animation(
    motion_data,
    source_representation="smpl",
    model_path="inputs/checkpoints/body_models/smpl/SMPL_NEUTRAL.pkl",
    gender="neutral",
    source_fps=30.0,
    output_fps=30.0,
)

result = export_smpl_fbx(
    bridge.animation,
    output_path="outputs/kaggle_tennis/smpl_source_clean.fbx",
    model_path="inputs/checkpoints/body_models/smpl/SMPL_NEUTRAL.pkl",
    model_type="smpl",
    gender="neutral",
    backend="blender",
)
print("output_path:", result.output_path)
print("armature_name:", result.armature_name)
print("frames:", result.frames)
