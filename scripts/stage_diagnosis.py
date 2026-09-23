import torch
import numpy as np
from scipy.spatial.transform import Rotation as R

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)

# SMPL22 kinematic tree (parents), 0=Pelvis
JOINT_NAMES = ["Pelvis","L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
               "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
               "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist","L_Hand","R_Hand"]
PARENTS = [-1,0,0,0,1,2,3,4,5,6,7,8,9,9,9,12,13,14,16,17,18,19,20,21]

def geodesic_deg(R1, R2):
    Rel = np.einsum("...ij,...kj->...ik", R2, R1)
    tr = np.trace(Rel, axis1=-2, axis2=-1)
    cos_t = np.clip((tr - 1) / 2, -1, 1)
    return np.degrees(np.arccos(cos_t))

def analyze(body_pose, global_orient, label):
    T = body_pose.shape[0]
    pose = body_pose.reshape(T, 21, 3)
    full_aa = np.concatenate([global_orient[:, None, :], pose], axis=1)  # (T,22,3) Pelvis..R_Wrist (22 joints, SMPL22)
    local_R = R.from_rotvec(full_aa.reshape(-1, 3)).as_matrix().reshape(T, 22, 3, 3)

    global_R = np.zeros_like(local_R)
    for j in range(22):
        p = PARENTS[j]
        if p < 0 or p >= 22:
            global_R[:, j] = local_R[:, j]
        else:
            global_R[:, j] = np.einsum("tij,tjk->tik", global_R[:, p], local_R[:, j])

    print(f"=== {label} : 글로벌(체인 합성) 회전, Blender 전혀 안 거침 ===")
    for name in ["Neck", "Head", "L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow", "Spine3"]:
        j = JOINT_NAMES.index(name)
        d_g = geodesic_deg(global_R[:-1, j], global_R[1:, j])
        top = np.argsort(d_g)[-6:][::-1]
        print(f"  {name:12s} max={d_g.max():6.1f} mean={d_g.mean():5.2f} top_frames={[(int(i)+1, round(float(d_g[i]),1)) for i in top]}")

p_global = d["smpl_params_global"]
analyze(p_global["body_pose"].numpy(), p_global["global_orient"].numpy(), "최종본 smpl_params_global (후처리 완료)")

raw = d["net_outputs"]["pred_smpl_params_global"]
raw_body_pose = raw["body_pose"][0].numpy()
raw_global_orient = raw["global_orient"][0].numpy()
analyze(raw_body_pose, raw_global_orient, "신경망 원시 출력 net_outputs.pred_smpl_params_global (후처리 전)")

diff_body = np.abs(p_global["body_pose"].numpy() - raw_body_pose).max()
diff_orient = np.abs(p_global["global_orient"].numpy() - raw_global_orient).max()
print(f"\n최종본 vs 원시출력 차이: body_pose max_abs_diff={diff_body:.6f}, global_orient max_abs_diff={diff_orient:.6f}")
