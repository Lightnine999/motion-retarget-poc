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
REPORT["bone_related_methods"] = sorted([a for a in dir(skel_comp) if "bone" in a.lower()])
REPORT["socket_related_methods"] = sorted([a for a in dir(skel_comp) if "socket" in a.lower()])
REPORT["boneSpaces_members"] = sorted([a for a in dir(unreal.BoneSpaces) if not a.startswith("_")]) if hasattr(unreal, "BoneSpaces") else "NO BoneSpaces"

for name in ["get_bone_transform", "get_socket_transform", "get_socket_location"]:
    fn = getattr(skel_comp, name, None)
    REPORT[f"help_{name}"] = fn.__doc__ if fn else "NOT FOUND"

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/78_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
print("done")
