"""
GVHMR raw 출력(hmr4d_results.pt)에서 SMPL 파라미터를 꺼내, Motius의 스무딩을
전혀 거치지 않은 순수 forward-kinematics 전역 회전을 직접 계산해 npz로 저장한다.

RETARGETING_JITTER_INVESTIGATION.md §7의 근본 수정(rest_basis 합성 + 좌표축 변환 +
Blender depsgraph 갱신)을 적용하려면, 스무딩이 섞이지 않은 이 "순정" 전역 회전이
반드시 필요하다 — Motius 라이브러리를 거치면 내부적으로 Whittaker 스무딩이 섞여
들어가 짐벌락의 원인이 된다(§3.2~3.3).

출력 3종:
  - smpl_params_raw.npz    : 원본 axis-angle/이동값 그대로 (디버깅용)
  - smpl_params_fk.npz     : 순수 FK 전역 회전(Y-up, SMPL 원본 좌표계) — Mixamo
                              캐릭터에 직접 리타겟할 때 이걸 그대로 쓴다(§7.9).
  - smpl_params_fk_zup.npz : 위와 같은 데이터를 Z-up으로 변환한 버전 — Blender의
                              Z-up SMPL 아마추어(smpl_source_clean.fbx)에 얹을 때
                              이 버전을 쓴다(§7.1~7.5).

실행 환경: conda gvhmr 환경(torch, scipy 필요). Blender 내장 파이썬이 아니다.
    conda run -n gvhmr python scripts/compute_smpl_fk.py \
        outputs/kaggle_tennis/hmr4d_results.pt outputs/kaggle_tennis
"""
import sys
import numpy as np
import torch
from scipy.spatial.transform import Rotation

# SMPL22 컨벤션(손 관절 제외, Pelvis 포함 22관절). motius.motion.skeleton.names 기준.
PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]

# SMPL(Y-up) -> Blender Z-up 변환: X축 기준 90도 회전
RCONV = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)


def main(pt_path: str, out_dir: str) -> None:
    d = torch.load(pt_path, map_location="cpu", weights_only=False)
    p = d["smpl_params_global"]

    global_orient = p["global_orient"].numpy()  # [T,3]
    body_pose = p["body_pose"].numpy()           # [T,63] (21 joints x 3)
    transl = p["transl"].numpy()                 # [T,3]
    T = global_orient.shape[0]

    np.savez(f"{out_dir}/smpl_params_raw.npz",
             global_orient=global_orient, body_pose=body_pose, transl=transl)

    local_aa = np.concatenate(
        [global_orient[:, None, :], body_pose.reshape(T, 21, 3)], axis=1
    )  # [T,22,3]
    local_mat = Rotation.from_rotvec(local_aa.reshape(-1, 3)).as_matrix().reshape(T, 22, 3, 3)

    global_mat = np.empty_like(local_mat)
    global_mat[:, 0] = local_mat[:, 0]
    for j in range(1, 22):
        global_mat[:, j] = global_mat[:, PARENTS[j]] @ local_mat[:, j]

    np.savez(f"{out_dir}/smpl_params_fk.npz", global_mat=global_mat, transl=transl)

    global_mat_z = RCONV[None, None] @ global_mat @ RCONV.T[None, None]
    transl_z = (RCONV[None] @ transl[:, :, None])[:, :, 0]
    np.savez(f"{out_dir}/smpl_params_fk_zup.npz", global_mat=global_mat_z, transl=transl_z)

    print(f"frames={T}")
    print(f"saved: {out_dir}/smpl_params_raw.npz")
    print(f"saved: {out_dir}/smpl_params_fk.npz      (Y-up, Mixamo 직접 리타겟용)")
    print(f"saved: {out_dir}/smpl_params_fk_zup.npz  (Z-up, SMPL Blender 아마추어용)")


if __name__ == "__main__":
    pt_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/kaggle_tennis/hmr4d_results.pt"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs/kaggle_tennis"
    main(pt_path, out_dir)
