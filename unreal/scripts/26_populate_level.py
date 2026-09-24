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

existing_actors = safe("get_actors", lambda: unreal.EditorLevelLibrary.get_all_level_actors())
REPORT["existing_actor_count"] = len(existing_actors) if existing_actors else 0
REPORT["existing_actor_labels"] = [a.get_actor_label() for a in existing_actors] if existing_actors else []

char_actor = safe("spawn_char", lambda: unreal.EditorLevelLibrary.spawn_actor_from_object(
    target_mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
REPORT["char_actor_is_none"] = char_actor is None
if char_actor:
    char_actor.set_actor_label("PreviewCharacter")
    REPORT["char_actor_class"] = char_actor.get_class().get_name()

camera_actor = safe("spawn_camera", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.CineCameraActor, unreal.Vector(300, 0, 120), unreal.Rotator(0, 180, 0)))
REPORT["camera_actor_is_none"] = camera_actor is None
if camera_actor:
    camera_actor.set_actor_label("PreviewCamera")

light_actor = safe("spawn_light", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(-45, 45, 0)))
REPORT["light_actor_is_none"] = light_actor is None
if light_actor:
    light_actor.set_actor_label("PreviewLight")

sky_actor = safe("spawn_sky", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkyLight, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
REPORT["sky_actor_is_none"] = sky_actor is None
if sky_actor:
    sky_actor.set_actor_label("PreviewSky")

safe("save_level", lambda: unreal.EditorLevelLibrary.save_current_level())

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/26_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
