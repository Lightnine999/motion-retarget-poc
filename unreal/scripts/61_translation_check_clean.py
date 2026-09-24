import unreal
import json
import math

anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean"
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

    def recurse(bone):
        order.append(bone)
        for c in subsystem.get_bone_children(mesh, bone):
            recurse(str(c))

    recurse(root)
    return order


root = find_root(target_mesh, "Neck")
bone_order = walk_tree(target_mesh, root)
num_frames = unreal.AnimationLibrary.get_num_frames(anim)

max_pos_len = {b: 0.0 for b in bone_order}
max_pos_frame = {b: -1 for b in bone_order}
max_scale_dev = {b: 0.0 for b in bone_order}
max_scale_frame = {b: -1 for b in bone_order}

for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, bone_order, frame, False, target_mesh)
    for b, t in zip(bone_order, poses):
        p = t.translation
        plen = math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
        if plen > max_pos_len[b]:
            max_pos_len[b] = plen
            max_pos_frame[b] = frame
        s = t.scale3d
        sdev = max(abs(s.x - 1.0), abs(s.y - 1.0), abs(s.z - 1.0))
        if sdev > max_scale_dev[b]:
            max_scale_dev[b] = sdev
            max_scale_frame[b] = frame

# 위치 크기 큰 순서로 정렬
ranked = sorted(bone_order, key=lambda b: -max_pos_len[b])[:15]
result = {
    "top_position_outliers": [
        {"bone": b, "max_pos_len": max_pos_len[b], "at_frame": max_pos_frame[b]} for b in ranked
    ],
    "top_scale_outliers": sorted(
        [{"bone": b, "max_scale_dev": max_scale_dev[b], "at_frame": max_scale_frame[b]} for b in bone_order],
        key=lambda x: -x["max_scale_dev"]
    )[:15],
}

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/61_translation_check.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
