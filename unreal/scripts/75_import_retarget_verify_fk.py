"""
1단계 재구축 결과(smpl_source_fk.fbx: 좌표계 변환 + view_layer.update() 버그 수정 반영,
스무딩 없는 순수 FK)를 언리얼로 가져와서:
  1) 기존 /Game/Source/SMPL_Source_Anim 을 새 FBX로 재임포트(교체)
  2) SMPL_to_Mixamo_Retargeter 로 Mixamo_Character 에 배치 리타겟
  3) 소스/타겟 양쪽 다 여러 프레임에 걸쳐 본 세그먼트 길이·좌우 대칭·연속 프레임 점프량을
     수치로 검증 (71_sanity_check_skeleton.py 패턴 재사용 + 프레임 커버리지 확대)
"""
import unreal
import json
import math
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


# --- 1) 재임포트 ---
existing_skeleton = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Skeleton")
REPORT["existing_skeleton_is_none"] = existing_skeleton is None


def import_anim_only(filename, dest_path, dest_name, skeleton):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.automated = True
    task.save = True
    task.replace_existing = True

    options = unreal.FbxImportUI()
    options.import_mesh = False
    options.import_as_skeletal = True
    options.import_animations = True
    options.create_physics_asset = False
    options.skeleton = skeleton

    anim_data = unreal.FbxAnimSequenceImportData()
    try:
        anim_data.import_bone_tracks = True
    except AttributeError:
        pass
    options.anim_sequence_import_data = anim_data

    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.imported_object_paths)


imported = safe("import_fk_source", lambda: import_anim_only(
    "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_fk.fbx",
    "/Game/Source",
    "SMPL_Source_Anim",
    existing_skeleton,
))
REPORT["imported_paths"] = imported

# --- 2) 배치 리타겟 ---
anim_asset_data = unreal.EditorAssetLibrary.find_asset_data("/Game/Source/SMPL_Source_Anim")
retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

REPORT["anim_asset_data_valid"] = anim_asset_data.is_valid() if anim_asset_data else False

inputs = unreal.IKRetargetBatchOperationInputs()
inputs.set_editor_property("assets_to_retarget", [anim_asset_data])
inputs.set_editor_property("ik_retarget_asset", retargeter)
inputs.set_editor_property("source_mesh", source_mesh)
inputs.set_editor_property("target_mesh", target_mesh)
inputs.set_editor_property("target_path", "/Game/Retarget/Animations")
inputs.set_editor_property("suffix", "_OnMixamo_FK")
inputs.set_editor_property("overwrite_existing_files", True)

retarget_result = safe("run_batch_retarget", lambda: unreal.IKRetargetBatchOperation.run_batch_retarget(inputs))

result_paths = []
target_anim_path = None
if retarget_result:
    for ad in retarget_result:
        entry = {}
        for prop in ["package_name", "asset_name"]:
            try:
                entry[prop] = str(ad.get_editor_property(prop))
            except Exception:
                pass
        pkg_name = entry.get("package_name")
        if pkg_name:
            saved = safe(f"save_{pkg_name}", lambda p=pkg_name: unreal.EditorAssetLibrary.save_asset(p))
            entry["saved"] = saved
            target_anim_path = pkg_name
        result_paths.append(entry)
REPORT["result_paths"] = result_paths
REPORT["target_anim_path"] = target_anim_path

# --- 3) 수치 검증 (소스 + 타겟 둘 다, 프레임 커버리지 넓게) ---
source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path) if target_anim_path else None

SOURCE_CHAIN = ["Pelvis", "Spine1", "Spine2", "Spine3", "Neck", "Head"]
SOURCE_LR = [("L_Shoulder", "R_Shoulder"), ("L_Wrist", "R_Wrist"), ("L_Ankle", "R_Ankle")]
TARGET_CHAIN = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
TARGET_LR = [("LeftShoulder", "RightShoulder"), ("LeftHand", "RightHand"), ("LeftFoot", "RightFoot")]


def vec_len(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def analyze(anim, mesh, chain, lr_pairs, frames):
    all_bones = chain + [b for pair in lr_pairs for b in pair]
    per_frame = []
    for f in frames:
        try:
            poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, all_bones, f, False, mesh)
        except Exception as e:
            per_frame.append({"frame": f, "error": str(e)})
            continue
        pos = {b: t.translation for b, t in zip(all_bones, poses)}
        seg = {f"{chain[i]}-{chain[i+1]}": round(vec_len(pos[chain[i]], pos[chain[i + 1]]), 1)
               for i in range(len(chain) - 1)}
        lr = {f"{l}_{r}_dist": round(vec_len(pos[l], pos[r]), 1) for l, r in lr_pairs}
        per_frame.append({"frame": f, "seg": seg, "lr": lr,
                           "root_z": round(pos[chain[0]].z, 1)})
    return per_frame


num_frames = safe("get_num_frames_source", lambda: unreal.AnimationLibrary.get_num_frames(source_anim)) or 0
REPORT["num_frames_source"] = num_frames
frames = list(range(0, num_frames, max(1, num_frames // 30)))

if source_anim and source_mesh:
    REPORT["source_analysis"] = analyze(source_anim, source_mesh, SOURCE_CHAIN, SOURCE_LR, frames)

if target_anim and target_mesh:
    num_frames_t = safe("get_num_frames_target", lambda: unreal.AnimationLibrary.get_num_frames(target_anim)) or 0
    REPORT["num_frames_target"] = num_frames_t
    frames_t = list(range(0, num_frames_t, max(1, num_frames_t // 30)))
    REPORT["target_analysis"] = analyze(target_anim, target_mesh, TARGET_CHAIN, TARGET_LR, frames_t)

# 세그먼트 길이 변동폭 자동 판정: 리지드 본이면 프레임 간 길이가 거의 일정해야 함
def check_rigidity(analysis, label):
    if not analysis:
        return None
    seg_names = analysis[0].get("seg", {}).keys()
    issues = []
    for name in seg_names:
        vals = [f["seg"][name] for f in analysis if "seg" in f and name in f["seg"]]
        if not vals:
            continue
        vmin, vmax = min(vals), max(vals)
        spread = vmax - vmin
        if vmax > 0 and spread / vmax > 0.15:
            issues.append({"segment": name, "min": vmin, "max": vmax, "spread_ratio": round(spread / vmax, 3)})
    return issues


REPORT["source_rigidity_issues"] = check_rigidity(REPORT.get("source_analysis"), "source")
REPORT["target_rigidity_issues"] = check_rigidity(REPORT.get("target_analysis"), "target")

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/75_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print("DONE. target_anim_path=", target_anim_path)
print("source_rigidity_issues:", REPORT["source_rigidity_issues"])
print("target_rigidity_issues:", REPORT["target_rigidity_issues"])
