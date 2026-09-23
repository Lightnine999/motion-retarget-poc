# 리타겟팅 떨림(Jitter) 원인 규명 및 대응 기록

> 작성일: 2026-09-23
> 상태: **부분 해결** — 극단적 스파이크(150~180°)는 근본 해결됨. 잔여 떨림(19~60° 수준)을 더 줄이려는 후처리(디스파이크)는 반복적으로 실패, 원인 미특정. 다른 섹션(파이프라인)에서 재시도 예정.

## 0. 한 줄 요약

Kaggle GVHMR → Motius/Rokoko로 Mixamo 캐릭터 리타겟팅 후 목·어깨·팔꿈치가 심하게 떠는 문제의 근본 원인은 **"FBX 파일 포맷이 회전을 쿼터니언이 아니라 항상 오일러(XYZ) 3채널로만 저장한다"**는 점이었다. Blender 내부에서는 쿼터니언으로 안전하게 다뤄도, **FBX로 굽는 순간 오일러로 변환되며 프레임마다 독립적으로 "다른 표현(branch)"을 골라버려 실제 짐벌락/랩어라운드가 발생**한다. 이걸 "이전 프레임과 연속적인 오일러"로 직접 변환해서 저장하도록 Motius 라이브러리를 패치해 극단적 스파이크는 잡았지만, 그 위에 추가로 시도한 "더 다듬기(디스파이크 후처리)"는 매번 자체 export 단계에서 같은 문제를 재도입해 실패했다.

## 1. 파이프라인 개요

```
영상(테니스 스윙)
  → GVHMR (Kaggle GPU) → hmr4d_results.pt (SMPL 파라미터, 312프레임)
  → [로컬 Mac] Motius: SMPL → 순정 SMPL 스켈레톤 FBX (smpl_source_clean.fbx)
  → [로컬 Mac] Blender + Rokoko 무료 애드온: SMPL FBX → Mixamo 캐릭터로 리타겟팅
  → mixamo_rokoko_retargeted.fbx
  → Blender 헤드리스 렌더 → mp4
```

- GVHMR 실행: [kaggle/gvhmr_inference_kaggle.ipynb](kaggle/gvhmr_inference_kaggle.ipynb) (Colab GPU 쿼터 소진으로 Kaggle로 전환, 관련 내용은 [TECH_SPEC.md §2.8](TECH_SPEC.md#28-gvhmr은-gpu-없이-실행-불가--cuda-하드코딩-2026-09-23) 참고)
- 결과물: `outputs/kaggle_tennis/hmr4d_results.pt` (다운로드 완료, 로컬 보관)
- 로컬 환경: conda `gvhmr`(Python 3.10), torch 2.3.0(MPS), Blender 5.2.2 LTS(`/Applications/Blender.app`), Motius(`pip install git+https://github.com/ZeyuLing/Motius.git`), Rokoko Studio Live for Blender — Blender 5.x 호환 포크(`abaqDev/Rokoko-Blender-Addon`)

## 2. 1차 문제 — 캐릭터가 공중에 뜨고 팔다리가 이상하게 꺾임

**증상**: Motius로 첫 리타겟팅했을 때 캐릭터가 땅에 발을 안 딛고, 팔다리가 완전히 다른 모션처럼 꺾임.

**원인**: Motius(`motius/motion/fbx/_blender.py`)의 `_REST_POSE_DIRECTION_CHILD` 딕셔너리가 **팔 체인(어깨~손목) 6개 본에만** 방향 보정(`rotation_difference` swing 보정)을 적용하고, 척추·목·다리는 전혀 보정하지 않는 구조적 한계가 있었다.

**대응**: `_REST_POSE_DIRECTION_CHILD`를 척추 전체 체인(Pelvis→Spine1→Spine2→Spine3→Neck→Head)과 다리 체인(Hip→Knee→Ankle)까지 확장. 발이 땅에 닿고 팔다리 방향이 정상화됨 — 이 시점에는 성공으로 보였음(후에 2차 문제가 드러남).

## 3. 2차 문제 — 목·어깨·팔이 0.5프레임 만에 150~180°씩 튐 (본 조사의 핵심)

**증상**: 다리/척추 보정 후에도 목·어깨·팔꿈치가 프레임마다 격렬하게 떪. 사용자가 "짐벌락 아니냐"고 의심, **4단계 파이프라인을 처음부터 순서대로 확인**하라고 지시.

### 3.1 단계별 진단 (실제로 수행한 순서)

| 단계 | 확인 방법 | 결과 |
|---|---|---|
| ① 영상→뼈대(원시 추정) | `hmr4d_results.pt`의 `net_outputs.pred_smpl_params_global`(신경망 원시 출력, 후처리 전)과 최상위 `smpl_params_global`(최종본) 비교 | **완전히 동일**(`max_abs_diff=0.0`). "후처리에서 노이즈 유입" 가설 기각. |
| ② SMPL을 입혔을 때 | Blender를 전혀 거치지 않고 순수 numpy로 SMPL 관절 체인(Pelvis→...→Neck/Elbow)의 글로벌 회전을 직접 합성, 프레임 간 geodesic 각도 변화 측정 | **전혀 안 튐** — Neck 최대 15.8°, 어깨 24~27°, 팔꿈치 27~37°. 전부 정상 스윙 범위. 좌표 변환(SMPL→Blender 축 변환)까지 재현해도 동일. |
| ③ FBX를 추출했을 때 | 위와 **완전히 동일한 데이터**를 Blender 안에서 keyframe만 찍고(FBX 왕복 없이) 재생 → 여전히 깨끗함. **그 다음 그대로 FBX로 export→재import**만 했더니 → Neck 160.7°, 어깨 161~162°로 폭발 | **범인 확정: FBX export/import 왕복 자체.** |
| ④ 믹사모 리타겟팅 후 | Motius/Rokoko 둘 다, 서로 다른 코드베이스인데도 **정확히 같은 프레임**(2~8, 133~137, 244~247)에서 같은 크기로 스파이크 | 3번의 오염이 그대로 전파된 것일 뿐, 리타겟팅 로직 자체는 무죄. |

### 3.2 근본 원인

FBX 바이너리를 `strings`로 직접 열어 확인: `Lcl Rotation`(로컬 회전) 커브와 `QuaternionInterpolate` 플래그가 별도로 존재 — 즉 **FBX는 회전을 항상 오일러(XYZ) 3채널로 저장**하고, `QuaternionInterpolate`는 "재생 시 보간 방식" 플래그일 뿐 저장 형식이 아니다. Blender 내부에서는 pose bone을 `rotation_mode="QUATERNION"`으로 다뤄 안전했지만, FBX export 시 quaternion→euler 변환이 **매 프레임 독립적으로** 이뤄지며(이전 프레임과의 연속성을 전혀 고려 안 함) 진짜 짐벌락/랩어라운드가 발생했다. `bake_anim_simplify_factor=0.0`으로 꺼도 재현되어, 키프레임 단순화 문제가 아님을 확인.

### 3.3 1차 수정 시도와 그 함정들 (전부 `motius/motion/fbx/_blender.py`의 `_key_pose_bone` 관련)

1. **시도 A — `Euler.make_compatible()`로 사후 보정**: 실패. Blender가 quaternion→euler 변환 시 이미 "임의 branch"를 선택해버린 뒤라, `make_compatible()`(단순 ±360° 주기 조정)로는 그 branch 자체를 못 되돌림.
2. **시도 B — 절대(armature-space) 회전행렬에서 직접 `Matrix.to_euler("XYZ", previous_euler)`로 연속 변환**: 짐벌락은 해결(수치는 numpy 원본과 정확히 일치, 19~60°대)됐지만 **몸 전체가 뒤틀리는 새로운 문제 발생**. 원인: 절대(부모 포함 누적) 회전값을 그대로 로컬(부모 기준 상대) 필드에 밀어넣어, 부모 본(척추 체인)이 이미 회전한 상태에서 자식(목/어깨)에 그 회전이 중복 적용됨. **사용자가 "1차 문제 때와 똑같이 몸이 뒤틀렸다"고 정확히 지적**하며 발견.
3. **시도 C(근본 수정 확정) — `pose_bone.matrix = 절대행렬` (setter, Blender가 부모의 현재 포즈를 감안해 올바른 로컬 `matrix_basis`를 역산해줌) → 그 결과인 `pose_bone.matrix_basis`에서 `to_euler("XYZ", previous_euler)`로 연속 변환**: **포즈 왜곡과 짐벌락 둘 다 해결.** 실측(`mixamo_rokoko_retargeted.fbx`): 목 19°, 어깨 29~33°, 팔꿈치 37~60° — 150°+ 스파이크 완전히 사라짐, 몸도 정상적으로 서 있음(프레임별 스크린샷 비교로 확인).

패치 위치: [patches/motius_blender_patched.py](patches/motius_blender_patched.py) — `_key_pose_bone`, `_animate_smpl_armature`, `_retarget_animation` 세 함수 수정. **주석에 위 함정(절대 vs 로컬)을 명시해뒀다.**

### 3.4 Rokoko 애드온 자체의 별도 버그 2개 (Blender 5.x 호환 문제, Motius와 무관)

Rokoko 리타겟팅(`bpy.ops.rsl.retarget_animation`) 실행 중 별도로 발견/수정:

1. **Action Slot 유실**: `copy_rest_pose()`가 소스 아마추어를 복제한 뒤 액션을 지웠다가 재할당하는데, Blender 4.4+의 새 Action Slot 시스템에서 슬롯을 재연결 안 해서 재생 시 `frame_range`가 `(1,2)`(빈 액션)로 나옴. → 복제 직후의 슬롯을 저장해뒀다가 복원하도록 패치.
2. **청크 합치기 슬롯 버그**: `bake_animation()`이 25프레임씩 나눠 굽고 하나로 합치는데, 각 청크(별도 Action)의 fcurve를 조회할 때 `armature_target`의 "현재(마지막) 슬롯"을 잘못 참조해서 첫 청크 이후 데이터가 유실됨. → `get_action_fcurves(action, None)`(슬롯 자동 탐색)으로 교체.

패치 위치: [patches/rokoko_retargeting_patched.py](patches/rokoko_retargeting_patched.py)

## 4. 3차 문제 — 잔여 떨림(19~60°)을 더 줄이려는 후처리(디스파이크)가 계속 실패

3.3의 근본 수정만으로도 150°+ 스파이크는 없앴지만, 사용자는 "목/어깨 10° 이하까지 더 다듬고 싶다"는 요구로 **이상치 프레임만 정밀 탐지해 SLERP 보간으로 대체하는 후처리 스크립트**(`despike_rotation5.py` → `despike_final.py`)를 여러 차례 시도했다.

**패턴**: 매번 "export 직전(메모리상) 검증"에서는 목표 수치(10~11°)를 달성했지만, **실제로 저장된 FBX를 재import해서 검증하면 다시 나빠짐**(despike_rotation5: 그대로 방치 시 원본과 동일한 150°+대로 복귀 확인됨 — 이는 스크립트가 `mixamo_rokoko_retargeted.fbx`[3.3 근본수정 반영판]를 다시 열어 처리한 뒤, **패치 안 된 일반 `bpy.ops.export_scene.fbx()`를 그대로 호출**해 3.2의 문제를 재도입한 것으로 확인. despike_final: 3.3과 동일한 "matrix_basis 기준 연속 오일러" 패턴을 despike 스크립트 자체에도 이식했음에도, export 전 10.6°였던 게 export 후 26~67°로 다시 악화 — **원인 미특정**).

**despike_final.py에서 원인으로 의심되는 것(미검증)**: Motius 원본 함수는 프레임을 바깥 루프, 본을 안쪽 루프로 돌며 매 본마다 `pose_bone.matrix = 절대값`(setter)을 호출한 직후 바로 오일러를 추출하는 반면, despike_final.py는 본을 바깥 루프, 프레임을 안쪽 루프로 돌며 `pose_bone.matrix`(setter)를 전혀 호출하지 않고 `rotation_euler`/`location`을 직접 대입했다. 이론상 로컬(`matrix_basis`) 값은 부모의 현재 포즈와 무관해야 하므로 문제 없어야 하지만, 실측 결과는 그렇지 않았다 — `bake_anim=True`가 우리가 넣은 키프레임을 그대로 쓰지 않고 매 프레임 "최종 결과"를 독자적으로 재평가·재분해하는 것으로 추정되나 확증하지 못했다.

**결론**: 디스파이크(후처리) 경로는 여기서 중단. **`mixamo_rokoko_retargeted.fbx`(디스파이크 없음, 3.3 근본 수정만 적용)를 최종 산출물로 확정**했다 — 목 19°, 어깨 29~33°, 팔꿈치 37~60°, 몸 포즈 정상, 150°+ 스파이크 없음.

## 5. 현재 상태 요약

| 항목 | 상태 |
|---|---|
| 캐릭터 접지(발이 땅에 닿음) | ✅ 해결 (§2) |
| 팔/다리/척추 방향 | ✅ 해결 (§2) |
| 목/어깨/팔 150°+ 짐벌락 스파이크 | ✅ 해결 (§3.3, Motius `_blender.py` 패치) |
| 몸 전체 포즈 왜곡(뒤틀림) | ✅ 해결 (§3.3, 절대→로컬 버그 수정) |
| 잔여 떨림(19~60°, 후처리로 더 다듬기) | ❌ 미해결 — 시도할 때마다 export 단계에서 재발, 원인 미특정 |

**최종 산출물**: `outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx` (렌더: `mixamo_nodespike_render.mp4`, 원본 비교: `side_by_side_nodespike.mp4`)

## 6. 재현/재시도를 위한 참고

- **패치는 로컬 pip 설치본과 사용자 Blender 애드온 폴더에만 있고, 이 저장소에는 반영 안 돼 있다.** 환경을 새로 만들면 사라지므로, 재적용하려면:
  ```bash
  cp patches/motius_blender_patched.py \
    /opt/anaconda3/envs/gvhmr/lib/python3.10/site-packages/motius/motion/fbx/_blender.py
  cp patches/rokoko_retargeting_patched.py \
    "$HOME/Library/Application Support/Blender/5.2/scripts/addons/rokoko_studio_live/operators/retargeting.py"
  ```
- 핵심 진단/재현 스크립트(`scripts/` 아래, 전부 이번 세션에서 작성):
  - `scripts/stage_diagnosis.py`, `scripts/stage3_coord_check.py`, `scripts/stage3_blender_isolate.py`, `scripts/stage3_keyframe_isolate.py`, `scripts/stage3_fbx_roundtrip.py`, `scripts/stage3_euler_fix.py` — §3.1~3.3 단계별 진단에 쓴 스크립트들(순서대로 실행하면 재현 가능)
  - `scripts/export_smpl_source.py` — Motius로 순정 SMPL FBX 생성
  - `scripts/rokoko_retarget2.py` — Rokoko 리타겟팅 실행(헤드리스)
  - `scripts/render_stills_rokoko.py` — Blender 헤드리스 프레임 렌더
  - `scripts/despike_rotation5.py`, `scripts/despike_final.py` — §4 실패한 후처리 시도(재시도 시 참고용으로 남겨둠, 그대로 쓰면 안 됨)
- 다음에 다른 파이프라인(예: Unreal Engine IK Retargeter)으로 시도할 경우, 이 문서의 §3.2(FBX가 회전을 오일러로만 저장한다는 사실)는 **Blender/Motius/Rokoko에 국한되지 않고 FBX 포맷 자체의 특성**이므로, 다른 도구에서도 유사한 함정이 있을 수 있다는 점을 염두에 둘 것.
