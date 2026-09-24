import unreal
import json
import time

REPORT = {}

level_path = "/Game/Render/PreviewLevel"
unreal.EditorLevelLibrary.load_level(level_path)

world = unreal.EditorLevelLibrary.get_editor_world()
REPORT["world_is_none"] = world is None

char_actor = None
for a in unreal.EditorLevelLibrary.get_all_level_actors():
    if a.get_actor_label() == "PreviewCharacter":
        char_actor = a

REPORT["char_actor_found"] = char_actor is not None
if char_actor:
    skel_comp = char_actor.skeletal_mesh_component
    REPORT["anim_asset"] = str(skel_comp.get_editor_property("animation_to_play")) if hasattr(skel_comp, "get_editor_property") else None
    skel_comp.set_position(2.0, False)
    skel_comp.set_playing(False)

REPORT["help_execute_console_command"] = unreal.SystemLibrary.execute_console_command.__doc__

unreal.SystemLibrary.execute_console_command(world, "HighResShot 1280x720")
time.sleep(1.0)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/33_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

unreal.SystemLibrary.quit_editor()
