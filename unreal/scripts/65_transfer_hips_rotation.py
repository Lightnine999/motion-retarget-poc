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


source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
source_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")
source_ikrig_controller = unreal.IKRigController.get_controller(source_ikrig)

target_anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean"
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

source_pelvis_ref = source_ikrig_controller.get_ref_pose_transform_of_bone("Pelvis").rotation
REPORT["source_pelvis_ref_q"] = [source_pelvis_ref.x, source_pelvis_ref.y, source_pelvis_ref.z, source_pelvis_ref.w]

num_frames = unreal.AnimationLibrary.get_num_frames(target_anim)

source_pelvis_rot = []
for f in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, ["Pelvis"], f, False, source_mesh)[0]
    source_pelvis_rot.append(t.rotation)

target_hips_current = []
for f in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, ["Hips"], f, False, target_mesh)[0]
    target_hips_current.append(t)

target_hips_ref_q = target_hips_current[0].rotation  # 이미 확인: 매 프레임 동일한 레퍼런스 고정값
pos = [t.translation for t in target_hips_current]
scale = [t.scale3d for t in target_hips_current]

new_rot = []
source_pelvis_ref_conj = quat_conj(source_pelvis_ref)
for f in range(num_frames):
    delta_q = quat_mul(source_pelvis_ref_conj, source_pelvis_rot[f])
    new_q = quat_mul(target_hips_ref_q, delta_q)
    new_rot.append(new_q)

REPORT["new_rot_sample"] = [[round(v, 3) for v in [q.x, q.y, q.z, q.w]] for q in new_rot[::50]]

controller = target_anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Transfer Hips rotation from source Pelvis", True))
ok = safe("write_hips_rot", lambda: controller.set_bone_track_keys("hips", pos, new_rot, scale, True))
safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(target_anim_path))

REPORT["write_ok"] = ok

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/65_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
