import unreal
import json
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


def quat_conj(q):
    return unreal.Quat(-q.x, -q.y, -q.z, q.w)


def quat_mul(a, b):
    x = a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y
    y = a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x
    z = a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w
    w = a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z
    return unreal.Quat(x, y, z, w)


# target_bone <- source_bone (1:1 대응, 본 개수가 같아서 직접 델타 전달 가능)
BONE_MAP = {
    "Hips": "Pelvis",
    "Spine": "Spine1",
    "Spine1": "Spine2",
    "Spine2": "Spine3",
    "Neck": "Neck",
    "Head": "Head",
    "LeftShoulder": "L_Collar",
    "RightShoulder": "R_Collar",
}

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
source_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")
source_ikrig_controller = unreal.IKRigController.get_controller(source_ikrig)

target_anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean"
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
target_ikrig_controller = unreal.IKRigController.get_controller(target_ikrig)

num_frames = unreal.AnimationLibrary.get_num_frames(target_anim)

source_bones = list(BONE_MAP.values())
target_bones = list(BONE_MAP.keys())

# 소스 전체 프레임 회전 수집
source_rot_per_frame = {b: [] for b in source_bones}
for f in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, source_bones, f, False, source_mesh)
    for b, t in zip(source_bones, poses):
        source_rot_per_frame[b].append(t.rotation)

# 타겟 현재 위치/스케일 (회전만 교체, 위치/스케일 유지)
target_pos_per_frame = {}
target_scale_per_frame = {}
for tb in target_bones:
    pos_list = []
    scale_list = []
    for f in range(num_frames):
        t = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, [tb], f, False, target_mesh)[0]
        pos_list.append(t.translation)
        scale_list.append(t.scale3d)
    target_pos_per_frame[tb] = pos_list
    target_scale_per_frame[tb] = scale_list

# 레퍼런스 포즈 (소스/타겟 각각)
source_ref = {b: source_ikrig_controller.get_ref_pose_transform_of_bone(b).rotation for b in source_bones}
target_ref = {tb: target_ikrig_controller.get_ref_pose_transform_of_bone(tb).rotation for tb in target_bones}

controller = target_anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Delta-transfer upper body from source", True))

written = []
for tb, sb in BONE_MAP.items():
    s_ref_conj = quat_conj(source_ref[sb])
    t_ref = target_ref[tb]
    new_rot = []
    for f in range(num_frames):
        delta_q = quat_mul(s_ref_conj, source_rot_per_frame[sb][f])
        new_q = quat_mul(t_ref, delta_q)
        new_rot.append(new_q)
    track_name = tb.lower()
    ok = safe(f"write_{track_name}", lambda track_name=track_name, tb=tb, new_rot=new_rot:
              controller.set_bone_track_keys(track_name, target_pos_per_frame[tb], new_rot, target_scale_per_frame[tb], True))
    written.append({"target_bone": tb, "source_bone": sb, "ok": ok})

safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(target_anim_path))

REPORT["written"] = written

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/70_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
