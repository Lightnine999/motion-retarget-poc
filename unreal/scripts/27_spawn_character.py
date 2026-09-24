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


level_path = "/Game/Render/PreviewLevel"
safe("load_level", lambda: unreal.EditorLevelLibrary.load_level(level_path))

target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")

for a in (unreal.EditorLevelLibrary.get_all_level_actors() or []):
    if a.get_actor_label() == "PreviewCharacter":
        unreal.EditorLevelLibrary.destroy_actor(a)

char_actor = safe("spawn_char", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
REPORT["char_actor_is_none"] = char_actor is None

if char_actor:
    char_actor.set_actor_label("PreviewCharacter")
    skel_comp = char_actor.skeletal_mesh_component
    REPORT["skel_comp_dir_mesh_related"] = [a for a in dir(skel_comp) if "mesh" in a.lower() or "anim" in a.lower()]
    ok = safe("set_mesh", lambda: skel_comp.set_skeletal_mesh(target_mesh))
    REPORT["set_mesh_ok"] = ok
    REPORT["help_set_animation_mode"] = skel_comp.set_animation_mode.__doc__
    REPORT["help_set_animation"] = skel_comp.set_animation.__doc__
    REPORT["help_play_animation"] = skel_comp.play_animation.__doc__
    ok2 = safe("set_anim_mode", lambda: skel_comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE))
    ok3 = safe("set_anim_asset", lambda: skel_comp.set_animation(anim))
    REPORT["set_anim_mode_ok"] = ok2
    REPORT["set_anim_asset_ok"] = ok3

safe("save_level", lambda: unreal.EditorLevelLibrary.save_current_level())

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/27_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
