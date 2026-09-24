"""GUI 에디터가 완전히 로드된 뒤 실행되는 startup 스크립트.
SMPL_to_Mixamo_Retargeter 에셋 에디터를 자동으로 열어준다."""
import unreal

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
unreal.AssetEditorSubsystem().open_editor_for_assets([retargeter])
print("Retargeter 에디터 열기 완료")
