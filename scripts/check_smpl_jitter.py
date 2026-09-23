import torch
import numpy as np

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)
p = d["smpl_params_global"]

body_pose = p["body_pose"].numpy()   # (T, 63) = 21 joints x 3 (axis-angle)
global_orient = p["global_orient"].numpy()  # (T, 3)
T = body_pose.shape[0]
print("frames:", T)

JOINT_NAMES = [
    "L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
    "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
    "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist",
]

def axis_angle_to_matrix(aa):
    # aa: (...,3) -> (...,3,3), Rodrigues
    theta = np.linalg.norm(aa, axis=-1, keepdims=True)
    theta_safe = np.where(theta < 1e-8, 1.0, theta)
    axis = aa / theta_safe
    x, y, z = axis[..., 0], axis[..., 1], axis[..., 2]
    c = np.cos(theta)[..., 0]
    s = np.sin(theta)[..., 0]
    C = 1 - c
    R = np.stack([
        c + x*x*C,     x*y*C - z*s,   x*z*C + y*s,
        y*x*C + z*s,   c + y*y*C,     y*z*C - x*s,
        z*x*C - y*s,   z*y*C + x*s,   c + z*z*C,
    ], axis=-1).reshape(aa.shape[:-1] + (3, 3))
    return R

pose = body_pose.reshape(T, 21, 3)
R = axis_angle_to_matrix(pose)  # (T,21,3,3)

def geodesic_deg(R1, R2):
    Rel = np.einsum("...ij,...kj->...ik", R2, R1)  # R2 @ R1^T
    trace = np.trace(Rel, axis1=-2, axis2=-1)
    cos_theta = np.clip((trace - 1) / 2, -1, 1)
    return np.degrees(np.arccos(cos_theta))

deltas = geodesic_deg(R[:-1], R[1:])  # (T-1, 21)

print(f"{'joint':12s} {'mean_deg/frame':>15s} {'max_deg/frame':>15s} {'p95_deg/frame':>15s}")
for j, name in enumerate(JOINT_NAMES):
    d_j = deltas[:, j]
    print(f"{name:12s} {d_j.mean():15.2f} {d_j.max():15.2f} {np.percentile(d_j,95):15.2f}")

# global_orient(pelvis) 자체도 확인
Rg = axis_angle_to_matrix(global_orient)
dg = geodesic_deg(Rg[:-1], Rg[1:])
print(f"{'Pelvis(global)':12s} {dg.mean():15.2f} {dg.max():15.2f} {np.percentile(dg,95):15.2f}")

# 가장 튀는 프레임 몇 개 찾기 (Neck, Head, L_Shoulder, R_Shoulder 기준)
for name in ["Neck", "Head", "L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow"]:
    j = JOINT_NAMES.index(name)
    d_j = deltas[:, j]
    top = np.argsort(d_j)[-5:][::-1]
    print(f"{name} 급격 변화 상위 5프레임(0-indexed, frame->frame+1):", [(int(i), round(float(d_j[i]),1)) for i in top])
