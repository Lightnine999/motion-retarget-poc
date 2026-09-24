import unreal
import json

anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def find_root(mesh, known_bone):
    b = known_bone
    for _ in range(50):
        parent = str(subsystem.get_bone_parent(mesh, b))
        if parent in ("None", ""):
            return b
        b = parent
    return b


def walk_tree(mesh, root):
    order = []
    parents = {}

    def recurse(bone, parent):
        order.append(bone)
        parents[bone] = parent
        for c in subsystem.get_bone_children(mesh, bone):
            recurse(str(c), bone)

    recurse(root, None)
    return order, parents


root = find_root(target_mesh, "Neck")
bone_order, bone_parents = walk_tree(target_mesh, root)

num_frames = unreal.AnimationLibrary.get_num_frames(anim)
seq_length = unreal.AnimationLibrary.get_sequence_length(anim)
frame_rate = (num_frames - 1) / seq_length if seq_length > 0 else 30.0

per_frame = []
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, bone_order, frame, False, target_mesh)
    frame_data = {}
    for bone, t in zip(bone_order, poses):
        q = t.rotation
        p = t.translation
        s = t.scale3d
        frame_data[bone] = {
            "q": [q.x, q.y, q.z, q.w],
            "p": [p.x, p.y, p.z],
            "s": [s.x, s.y, s.z],
        }
    per_frame.append(frame_data)

out = {
    "bone_order": bone_order,
    "bone_parents": bone_parents,
    "num_frames": num_frames,
    "frame_rate": frame_rate,
    "sequence_length": seq_length,
    "frames": per_frame,
}

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump.json", "w") as f:
    json.dump(out, f)

print(f"dumped {num_frames} frames, {len(bone_order)} bones")
