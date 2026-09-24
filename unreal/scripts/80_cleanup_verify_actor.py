import unreal

for a in (unreal.EditorLevelLibrary.get_all_level_actors() or []):
    if a.get_actor_label() == "VerifyCharacter_FK":
        unreal.EditorLevelLibrary.destroy_actor(a)
unreal.EditorLevelLibrary.save_current_level()
print("cleaned up")
