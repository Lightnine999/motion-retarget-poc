import json

IN_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump.json"
REF_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/ref_pose_dump.json"
OUT_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump_local.json"

with open(IN_PATH) as f:
    dump = json.load(f)
with open(REF_PATH) as f:
    ref_pose = json.load(f)

bone_order = dump["bone_order"]
bone_parents = dump["bone_parents"]
root_bone = bone_order[0]


def quat_mul(a, b):
    # a, b: [x,y,z,w]  ->  a*b (해밀턴 곱, 먼저 b 적용 후 a 적용하는 표준 합성)
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    x = aw * bx + ax * bw + ay * bz - az * by
    y = aw * by - ax * bz + ay * bw + az * bx
    z = aw * bz + ax * by - ay * bx + az * bw
    w = aw * bw - ax * bx - ay * by - az * bz
    return [x, y, z, w]


def quat_conj(q):
    x, y, z, w = q
    return [-x, -y, -z, w]


# 1) 레퍼런스(bind) 포즈를 로컬로 변환
ref_world_q = {b: ref_pose[b]["q"] for b in bone_order}
ref_local_q = {}
for b in bone_order:
    parent = bone_parents.get(b)
    if parent is None or parent not in ref_world_q:
        ref_local_q[b] = ref_world_q[b]
    else:
        ref_local_q[b] = quat_mul(quat_conj(ref_world_q[parent]), ref_world_q[b])

# 2) 매 프레임: 글로벌 -> 로컬 -> (레스트 대비) 델타로 변환
for frame_data in dump["frames"]:
    world_q = {b: frame_data[b]["q"] for b in bone_order}
    local_q = {}
    for b in bone_order:
        parent = bone_parents.get(b)
        if parent is None or parent not in world_q:
            local_q[b] = world_q[b]
        else:
            local_q[b] = quat_mul(quat_conj(world_q[parent]), world_q[b])

    for b in bone_order:
        delta_q = quat_mul(quat_conj(ref_local_q[b]), local_q[b])
        frame_data[b]["q"] = delta_q

with open(OUT_PATH, "w") as f:
    json.dump(dump, f)

print("converted, wrote", OUT_PATH)
