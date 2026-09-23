import bpy
import math
from mathutils import Quaternion

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_retargeted.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

action = armature.animation_data.action
frame_end = int(action.frame_range[1])
scene = bpy.context.scene

all_bones = [pb.name for pb in armature.pose.bones]

# 1) 전 프레임의 quaternion(위치 포함) 추출 + 이중피복 연속성 보정
loc_history = {b: [] for b in all_bones}
quat_history = {b: [] for b in all_bones}
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    for b in all_bones:
        pb = armature.pose.bones[b]
        loc_history[b].append(pb.location.copy())
        q = pb.matrix.to_quaternion()
        if quat_history[b] and q.dot(quat_history[b][-1]) < 0:
            q = -q
        quat_history[b].append(q.copy())

def smooth_quats(qs, radius=2):
    n = len(qs)
    out = []
    for i in range(n):
        lo = max(0, i - radius)
        hi = min(n, i + radius + 1)
        window = qs[lo:hi]
        # 반복 pairwise slerp로 근사 평균 (참조 쿼터니언 기준 부호 통일)
        ref = qs[i]
        acc = Quaternion((0, 0, 0, 0))
        for q in window:
            qq = q if q.dot(ref) >= 0 else -q
            acc = Quaternion((acc.w + qq.w, acc.x + qq.x, acc.y + qq.y, acc.z + qq.z))
        acc.normalize()
        out.append(acc)
    return out

smoothed = {b: smooth_quats(quat_history[b], radius=2) for b in all_bones}

# 2) 스무딩 전/후 비교: 문제 본들의 프레임간 변화량
check_bones = ["mixamorig10:Neck", "mixamorig10:RightForeArm", "mixamorig10:LeftForeArm", "mixamorig10:RightArm"]
for b in check_bones:
    before = quat_history[b]
    after = smoothed[b]
    def deltas(qs):
        return [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    db, da = deltas(before), deltas(after)
    print(f"{b:25s} before(max)={max(db):6.1f} after(max)={max(da):6.1f} before(mean)={sum(db)/len(db):5.2f} after(mean)={sum(da)/len(da):5.2f}")

# 3) 스무딩 결과를 애니메이션에 다시 기록 (위치는 그대로, 회전만 교체)
armature.animation_data_clear()
for pb in armature.pose.bones:
    pb.matrix_basis.identity()
    pb.rotation_mode = "QUATERNION"

for i, f in enumerate(range(1, frame_end + 1)):
    scene.frame_set(f)
    for b in all_bones:
        pb = armature.pose.bones[b]
        pb.location = loc_history[b][i]
        pb.rotation_quaternion = smoothed[b][i]
        pb.keyframe_insert(data_path="location", frame=f, group=b)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f, group=b)

bpy.ops.wm.save_as_mainfile(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smoothed.blend")
print("saved smoothed .blend")
