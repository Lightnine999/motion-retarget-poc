"""
75번 스크립트의 get_bone_poses_for_frame 기반 검증이 로컬(부모 기준) 공간값을
반환하는 것으로 의심되어(좌우 대칭 쌍이 전부 0.0, Hips-Spine이 수백m로 폭주)
신뢰할 수 없었다. 실제 캐릭터를 레벨에 스폰해서 SkeletalMeshComponent의
월드 스페이스 본 위치(get_bone_location, WORLD)를 프레임별로 직접 쿼리하는
방식으로 재검증한다. 이건 실제 렌더링에 쓰이는 것과 동일한 평가 경로라 신뢰도가 높다.
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


target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_FK")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

world = unreal.EditorLevelLibrary.get_editor_world()
REPORT["world_is_none"] = world is None

for a in (unreal.EditorLevelLibrary.get_all_level_actors() or []):
    if a.get_actor_label() == "VerifyCharacter_FK":
        unreal.EditorLevelLibrary.destroy_actor(a)

char_actor = safe("spawn", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
if char_actor:
    char_actor.set_actor_label("VerifyCharacter_FK")
    skel_comp = char_actor.skeletal_mesh_component
    safe("set_mesh", lambda: skel_comp.set_skeletal_mesh(target_mesh))
    safe("set_anim_mode", lambda: skel_comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE))
    safe("set_anim_asset", lambda: skel_comp.set_animation(target_anim))
    safe("set_update_in_editor", lambda: skel_comp.set_update_animation_in_editor(True))

    fps = 30.0
    num_frames = safe("get_num_frames", lambda: unreal.AnimationLibrary.get_num_frames(target_anim)) or 300
    REPORT["num_frames"] = num_frames

    CHAIN = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
    LR = [("LeftShoulder", "RightShoulder"), ("LeftHand", "RightHand"), ("LeftFoot", "RightFoot")]
    all_bones = CHAIN + [b for pair in LR for b in pair]

    def vec_len(a, b):
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)

    frames = list(range(0, num_frames, max(1, num_frames // 40)))
    per_frame = []
    for f in frames:
        t = f / fps
        safe(f"set_position_{f}", lambda t=t: skel_comp.set_position(t, False))
        safe(f"refresh_{f}", lambda: skel_comp.refresh_bone_transforms())
        safe(f"tick_{f}", lambda: skel_comp.tick_component(0.0333, unreal.LevelTick.LEVELTICK_ALL, None))
        pos = {}
        for b in all_bones:
            loc = safe(f"loc_{b}_{f}", lambda b=b: skel_comp.get_socket_location(b))
            pos[b] = loc
        if any(v is None for v in pos.values()):
            per_frame.append({"frame": f, "error": "missing bone location"})
            continue
        seg = {f"{CHAIN[i]}-{CHAIN[i+1]}": round(vec_len(pos[CHAIN[i]], pos[CHAIN[i + 1]]), 2)
               for i in range(len(CHAIN) - 1)}
        lr = {f"{l}_{r}_dist": round(vec_len(pos[l], pos[r]), 2) for l, r in LR}
        per_frame.append({"frame": f, "seg": seg, "lr": lr, "hips_z": round(pos["Hips"].z, 2)})

    REPORT["per_frame"] = per_frame

    def check_rigidity(analysis):
        if not analysis or "seg" not in analysis[0]:
            return None
        seg_names = analysis[0]["seg"].keys()
        issues = []
        for name in seg_names:
            vals = [f["seg"][name] for f in analysis if "seg" in f and name in f["seg"]]
            if not vals:
                continue
            vmin, vmax = min(vals), max(vals)
            spread = vmax - vmin
            if vmax > 0 and spread / vmax > 0.1:
                issues.append({"segment": name, "min": vmin, "max": vmax, "spread_ratio": round(spread / vmax, 3)})
        return issues

    REPORT["rigidity_issues"] = check_rigidity(per_frame)

    lr_names = LR
    lr_summary = {}
    for l, r in lr_names:
        key = f"{l}_{r}_dist"
        vals = [f["lr"][key] for f in per_frame if "lr" in f]
        if vals:
            lr_summary[key] = {"min": min(vals), "max": max(vals), "mean": round(sum(vals) / len(vals), 2)}
    REPORT["lr_summary"] = lr_summary

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/77_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print("DONE")
print("rigidity_issues:", REPORT.get("rigidity_issues"))
print("lr_summary:", REPORT.get("lr_summary"))
