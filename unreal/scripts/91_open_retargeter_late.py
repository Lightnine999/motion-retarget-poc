import unreal
retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
subsystem.open_editor_for_assets([retargeter])
print("Retargeter 에디터 열기 완료")
