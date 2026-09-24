import unreal
import json

target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
for a in (unreal.EditorLevelLibrary.get_all_level_actors() or []):
    if a.get_actor_label() == "VerifyCharacter_FK":
        unreal.EditorLevelLibrary.destroy_actor(a)
char_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
char_actor.set_actor_label("VerifyCharacter_FK")
skel_comp = char_actor.skeletal_mesh_component
skel_comp.set_skinned_asset_and_update(target_mesh)

REPORT = {}
REPORT["tick_refresh_methods"] = sorted([a for a in dir(skel_comp)
                                          if "tick" in a.lower() or "refresh" in a.lower() or "recalc" in a.lower() or "update" in a.lower()])
REPORT["help_set_position"] = skel_comp.set_position.__doc__

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/79_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
print("done")
