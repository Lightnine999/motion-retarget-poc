import torch
import numpy as np
from scipy.spatial.transform import Rotation as R

d = torch.load("outputs/kaggle_tennis/hmr4d_results.pt", map_location="cpu", weights_only=False)
p = d["smpl_params_global"]

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
    global_R[:, j] = local_R[:, j] if par < 0 else np.einsum("tij,tjk->tik", global_R[:, par], local_R[:, j])

SMPL_TO_BLENDER = np.array([[1.0,0,0],[0,0,-1.0],[0,1.0,0]])
global_R_blender = np.einsum("ab,tjbc,cd->tjad", SMPL_TO_BLENDER, global_R, SMPL_TO_BLENDER.T).astype(np.float32)

np.save("outputs/kaggle_tennis/global_R_blender.npy", global_R_blender)
print("saved", global_R_blender.shape)
