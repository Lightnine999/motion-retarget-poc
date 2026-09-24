"""GUI에서 실행: smpl_source_fk.fbx(재구축 결과)를 불러와서 재생 준비까지 해둔다.
사용자가 스페이스바만 누르면 바로 뷰포트에서 애니메이션을 확인할 수 있게 세팅."""
import bpy

FK_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_fk.fbx"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FK_FBX)

for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

scene = bpy.context.scene
scene.frame_set(1)

# 3D 뷰포트를 솔리드 셰이딩으로 맞추고, 카메라 대신 뷰포트에서 바로 보이게 준비
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = "SOLID"
                with bpy.context.temp_override(area=area):
                    bpy.ops.view3d.view_all()

print("SMPL_FK 결과 로드 완료. 스페이스바로 재생해서 확인하세요.")
