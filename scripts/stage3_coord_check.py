import torch
import numpy as np
from scipy.spatial.transform import Rotation as R

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)
p = d["smpl_params_global"]

JOINT_NAMES = ["Pelvis","L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
               "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
               "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist","L_Hand","R_Hand"]
PARENTS = [-1,0,0,0,1,2,3,4,5,6,7,8,9,9,9,12,13,14,16,17,18,19,20,21]

body_pose = p["body_pose"].numpy()
global_orient = p["global_orient"].numpy()
T = body_pose.shape[0]
pose = body_pose.reshape(T, 21, 3)
full_aa = np.concatenate([global_orient[:, None, :], pose], axis=1)
local_R = R.from_rotvec(full_aa.reshape(-1, 3)).as_matrix().reshape(T, 22, 3, 3)

global_R = np.zeros_like(local_R)
for j in range(22):
    par = PARENTS[j]
    if par < 0:
        global_R[:, j] = local_R[:, j]
    else:
        global_R[:, j] = np.einsum("tij,tjk->tik", global_R[:, par], local_R[:, j])

# Motius의 SMPL_TO_BLENDER conjugate 변환을 그대로 재현 (float64 유지)
SMPL_TO_BLENDER = np.array([[1.0,0,0],[0,0,-1.0],[0,1.0,0]])
global_R_blender = np.einsum("ab,tjbc,cd->tjad", SMPL_TO_BLENDER, global_R, SMPL_TO_BLENDER.T)

def geodesic_deg(R1, R2):
    Rel = np.einsum("...ij,...kj->...ik", R2, R1)
    tr = np.trace(Rel, axis1=-2, axis2=-1)
    cos_t = np.clip((tr - 1) / 2, -1, 1)
    return np.degrees(np.arccos(cos_t))

print("=== SMPL_TO_BLENDER 좌표변환 적용 후 (여전히 Blender 안 거침, numpy) ===")
for name in ["Neck", "Head", "L_Shoulder", "R_Shoulder"]:
    j = JOINT_NAMES.index(name)
    dg = geodesic_deg(global_R_blender[:-1, j], global_R_blender[1:, j])
    print(f"  {name:12s} max={dg.max():6.1f} mean={dg.mean():5.2f}")

# 직교성/행렬식 확인 (float32 캐스팅 문제 여부)
for name in ["Neck"]:
    j = JOINT_NAMES.index(name)
    Rm = global_R_blender[:, j].astype(np.float32)
    det = np.linalg.det(Rm)
    orth_err = np.abs(np.einsum("tij,tkj->tik", Rm, Rm) - np.eye(3)).max()
    print(f"float32 캐스팅 후 {name}: det range=({det.min():.6f},{det.max():.6f}) orth_err_max={orth_err:.6f}")
