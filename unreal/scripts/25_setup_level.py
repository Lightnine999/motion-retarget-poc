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

if unreal.EditorAssetLibrary.does_asset_exist(level_path):
    safe("load_level", lambda: unreal.EditorLevelLibrary.load_level(level_path))
else:
    safe("new_level", lambda: unreal.EditorLevelLibrary.new_level(level_path))

target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")

# 기존 액터 정리 (재실행 대비)
existing_actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in existing_actors:
    if a.get_actor_label() in ("PreviewCharacter", "PreviewCamera", "PreviewLight", "PreviewSky"):
        unreal.EditorLevelLibrary.destroy_actor(a)

# 스켈레탈 메시 액터 스폰
char_actor = safe("spawn_char", lambda: unreal.EditorLevelLibrary.spawn_actor_from_object(
    target_mesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
if char_actor:
    char_actor.set_actor_label("PreviewCharacter")
    skel_comp = char_actor.skeletal_mesh_component if hasattr(char_actor, "skeletal_mesh_component") else None
    REPORT["char_actor_class"] = char_actor.get_class().get_name()
    REPORT["char_actor_components"] = [c.get_class().get_name() for c in char_actor.get_components_by_class(unreal.ActorComponent)]

# 카메라 스폰
camera_actor = safe("spawn_camera", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.CineCameraActor, unreal.Vector(300, 0, 120), unreal.Rotator(0, 180, 0)))
if camera_actor:
    camera_actor.set_actor_label("PreviewCamera")

# 라이트 스폰
light_actor = safe("spawn_light", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(-45, 45, 0)))
if light_actor:
    light_actor.set_actor_label("PreviewLight")

sky_actor = safe("spawn_sky", lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkyLight, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)))
if sky_actor:
    sky_actor.set_actor_label("PreviewSky")

safe("save_level", lambda: unreal.EditorLevelLibrary.save_current_level())

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/25_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
