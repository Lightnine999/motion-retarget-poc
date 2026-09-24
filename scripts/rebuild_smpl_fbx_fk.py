"""
1단계 재구축 v3: 순수 FK(스무딩 없음)로 합성한 전역 회전을 Motius와 동일하게
'글로벌 회전 x rest_basis'로 본에 적용하고, 위치(translation)도 제대로 된
forward kinematics로 계산한다.

v1 실수: rest_basis 합성을 빼먹어서 본이 엉뚱한 축으로 회전 -> 캐릭터 붕괴
v2 실수: 회전은 고쳤지만 자식 본의 위치(translation)를 FK로 전파하지 않고
         이전 프레임/레스트 값을 그대로 남겨둠 -> 부모가 회전해도 자식이 안 따라감
         (같은 '튜브처럼 늘어나는' 증상의 원인이 될 수 있음)
v3: pos[child] = pos[parent] + G[parent] @ (rest_head[child] - rest_head[parent])
    을 명시적으로 계산해서 진짜 forward kinematics로 위치를 구한다.
    렌더링(뷰포트 스크린샷)까지 같은 스크립트에서 수행해서 육안 검증 근거를 남긴다.
"""
import bpy
import mathutils
import numpy as np
import math
import os

FK_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_params_fk_zup.npz"
REF_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx"
OUT_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_fk.fbx"
SHOT_DIR = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/fk_preview"

# Pelvis 포함, PARENTS는 이 리스트 안의 인덱스를 가리킴 (SMPL22_PARENTS와 동일 순서)
JOINT_ORDER = [
    "Pelvis", "L_Hip", "R_Hip", "Spine1", "L_Knee", "R_Knee", "Spine2",
    "L_Ankle", "R_Ankle", "Spine3", "L_Foot", "R_Foot", "Neck",
    "L_Collar", "R_Collar", "Head", "L_Shoulder", "R_Shoulder",
    "L_Elbow", "R_Elbow", "L_Wrist", "R_Wrist",
]
PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]

npz = np.load(FK_PATH)
global_mat = npz["global_mat"]  # [T,22,3,3] 순수 SMPL 전역 회전(부모체인 합성, 스무딩 없음)
transl = npz["transl"]          # [T,3]
num_frames = global_mat.shape[0]
print(f"frames: {num_frames}")


def np_to_matrix(m3):
    return mathutils.Matrix(m3.tolist())


os.makedirs(SHOT_DIR, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=REF_FBX)

armature = None
mesh_obj = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
    elif obj.type == "MESH":
        mesh_obj = obj
assert armature is not None
assert mesh_obj is not None

armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = num_frames
scene.render.fps = 30

pose_bones = armature.pose.bones
for pb in pose_bones:
    pb.rotation_mode = "QUATERNION"

missing = [n for n in JOINT_ORDER if n not in pose_bones]
print("missing bones:", missing)

# 레스트 방향(rest_basis)과 레스트 위치(head_local, 암니처 공간) 캐시
rest_basis = {}
rest_head = {}
for name in JOINT_ORDER:
    b = armature.data.bones[name]
    rest_basis[name] = b.matrix_local.to_3x3()
    rest_head[name] = b.head_local.copy()

pelvis_rest_head = rest_head["Pelvis"]

for index in range(num_frames):
    frame = index + 1
    scene.frame_set(frame)

    # 1) 순수 FK로 각 관절의 월드(암니처 공간) 위치를 먼저 계산
    pos = {}
    pos["Pelvis"] = pelvis_rest_head + mathutils.Vector(tuple(transl[index]))
    for j, name in enumerate(JOINT_ORDER):
        if name == "Pelvis":
            continue
        parent_idx = PARENTS[j]
        parent_name = JOINT_ORDER[parent_idx]
        offset = rest_head[name] - rest_head[parent_name]
        parent_global_rot = np_to_matrix(global_mat[index, parent_idx])
        pos[name] = pos[parent_name] + parent_global_rot @ offset

    # 2) 회전(global_rotation @ rest_basis) + 위 위치로 pose_bone.matrix 설정
    for j, name in enumerate(JOINT_ORDER):
        if name not in pose_bones:
            continue
        pb = pose_bones[name]
        rotation = np_to_matrix(global_mat[index, j]) @ rest_basis[name]
        m = rotation.to_4x4()
        m.translation = pos[name]
        pb.matrix = m
        # 자식 본의 pb.matrix setter가 "갱신 전" 부모 상태를 참조하는 걸 막기 위해
        # 본 하나 설정할 때마다 즉시 의존성 그래프를 갱신한다.
        # (이걸 빼먹으면 identity 회전만 넣어도 T-pose가 실타래처럼 붕괴됨 - 실측 확인함)
        bpy.context.view_layer.update()
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        pb.keyframe_insert(data_path="location", frame=frame)

scene.frame_set(1)

if armature.animation_data and armature.animation_data.action:
    action = armature.animation_data.action
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        curves = legacy
    else:
        curves = []
        for layer in getattr(action, "layers", ()):
            for strip in getattr(layer, "strips", ()):
                for channelbag in getattr(strip, "channelbags", ()):
                    curves.extend(channelbag.fcurves)
    for curve in curves:
        for kp in curve.keyframe_points:
            kp.interpolation = "LINEAR"

# --- 육안 검증용 뷰포트 스크린샷 (여러 프레임, 정면/측면) ---
# 전신이 프레임에 확실히 들어오도록, 실제 메시 월드 바운딩박스를 프레임마다 계산해서
# 카메라 위치/스케일을 자동으로 맞춘다 (고정 카메라로 인한 프레이밍 오판 방지).
depsgraph = bpy.context.evaluated_depsgraph_get()


def world_bbox(frame):
    scene.frame_set(frame)
    depsgraph.update()
    ev = mesh_obj.evaluated_get(depsgraph)
    mat = ev.matrix_world
    coords = [mat @ v.co for v in ev.data.vertices]
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    zs = [c.z for c in coords]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


preview_frames = sorted(set([1, num_frames // 6, num_frames // 3, num_frames // 2,
                              2 * num_frames // 3, 5 * num_frames // 6, num_frames]))
print("preview frames:", preview_frames)

# 전체 프리뷰 프레임을 아우르는 바운딩박스 하나로 카메라를 고정 (프레임마다 스케일이 바뀌면 비교가 어려움)
all_x, all_y, all_z = [], [], []
for f in preview_frames:
    (x0, x1), (y0, y1), (z0, z1) = world_bbox(f)
    all_x += [x0, x1]
    all_y += [y0, y1]
    all_z += [z0, z1]
cx = (min(all_x) + max(all_x)) / 2
cy = (min(all_y) + max(all_y)) / 2
cz = (min(all_z) + max(all_z)) / 2
span = max(max(all_x) - min(all_x), max(all_y) - min(all_y), max(all_z) - min(all_z))
scale = span * 1.4 + 0.5
print(f"bbox center=({cx:.2f},{cy:.2f},{cz:.2f}) span={span:.2f} ortho_scale={scale:.2f}")

dist = span * 3 + 3
bpy.ops.object.camera_add(location=(cx, cy - dist, cz), rotation=(math.radians(90), 0, 0))
cam_front = bpy.context.object
cam_front.name = "Cam_Front"
cam_front.data.type = "ORTHO"
cam_front.data.ortho_scale = scale

bpy.ops.object.camera_add(location=(cx + dist, cy, cz), rotation=(math.radians(90), 0, math.radians(90)))
cam_side = bpy.context.object
cam_side.name = "Cam_Side"
cam_side.data.type = "ORTHO"
cam_side.data.ortho_scale = scale

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 480
scene.render.resolution_y = 640
scene.display_settings.display_device = "sRGB"
scene.render.image_settings.file_format = "PNG"

for cam, tag in [(cam_front, "front"), (cam_side, "side")]:
    scene.camera = cam
    for f in preview_frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(SHOT_DIR, f"{tag}_frame{f:04d}.png")
        bpy.ops.render.render(write_still=True)

print("preview screenshots saved to:", SHOT_DIR)

# 카메라는 export에서 제외
bpy.data.objects.remove(cam_front, do_unlink=True)
bpy.data.objects.remove(cam_side, do_unlink=True)

bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=False,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,
    add_leaf_bones=False,
)
print("exported:", OUT_FBX)
