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

## 7. 4차 문제 — 잔여 떨림을 "다듬기"가 아니라 "처음부터 다시 만들기"로 해결 (2026-09-24)

### 7.0 배경 — 왜 후처리를 포기하고 1단계부터 재시작했는가

§4의 디스파이크(후처리) 경로가 막힌 뒤에도 실제 사용자 확인 결과는 계속 나빴다. Blender에서 `smpl_source_clean.fbx`를 직접 열어 F-curve 그래프를 봤더니 **한 프레임 만에 본이 급격히 이동·회전**하는 게 그래프로 명확히 보였다 — 즉 §3.3에서 "해결됐다"고 판단했던 1단계(SMPL 파라미터 → FBX 변환) 자체가 여전히 깨끗하지 않았다는 뜻이었다. 그래서 방향을 바꿨다: **후처리로 다듬는 대신, Motius 라이브러리의 스무딩(`_smooth_global_rotations`)을 아예 거치지 않고 1단계를 처음부터 직접 재구현**하기로 했다. 원본 SMPL 데이터 자체는 (Blender에서 눈으로 봤을 때) 매끄럽다고 확인된 상태였으므로, 문제는 "SMPL → Blender 본 적용" 변환 코드에 있다고 보고 그 부분만 다시 짰다.

### 7.1 시행착오 1 — rest_basis 합성을 빼먹어 캐릭터가 튜브처럼 붕괴

SMPL의 `body_pose`(axis-angle)를 Blender 본의 로컬 회전에 **rest_basis(본의 레스트 방향) 합성 없이 직접 대입**했다. 결과: 캐릭터가 긴 튜브 모양으로 완전히 무너짐. 사용자가 스크린샷으로 즉시 지적("이게 뭐지? 거짓말하지말고 왜 그런지 솔직하게 얘기해") — 원인은 Blender 본이 자기 고유의 "레스트 방향"(head→tail이 로컬 Y축)을 가지는데, SMPL의 axis-angle은 이 방향과 무관한 SMPL 고유 좌표계 기준 회전이라, 두 좌표계를 rest_basis로 연결해주지 않으면 본이 전혀 엉뚱한 축으로 회전한다는 것.

**수정**: Motius의 원래 공식 `rotation = global_rotation @ rest_basis` (부모 체인까지 합성한 전역 회전을 본의 레스트 방향에 곱함)을 스무딩만 제외하고 그대로 복원.

### 7.2 시행착오 2 — rest_basis를 복원해도 여전히 붕괴 (레퍼런스 자체가 이미 깨져있었음)

rest_basis를 복원한 v2로 다시 렌더링했지만 **여전히 실타래처럼 뒤틀린 모습**이 나왔다. 원인을 좁히기 위해 세 가지 대조군을 렌더링했다:

1. **`smpl_source_clean.fbx`(원본, 아무 수정도 안 한 것) 자체를 같은 카메라로 렌더링** → 프레임 1부터 이미 실타래처럼 꼬여 있었다. 즉 1단계 변환 자체가 처음부터 문제였다는 걸 재확인.
2. **같은 파일의 순수 레스트(바인드) 포즈만 렌더링**(애니메이션 제거) → **완벽한 T-pose**였다. 즉 스켈레톤 구조/rest_basis 자체는 정상이고, 문제는 "애니메이션을 입히는 로직" 쪽에 있다는 게 확정됨.

### 7.3 시행착오 3 — 좌표계 축 불일치 발견 (SMPL Y-up vs Blender Z-up)

원본 raw SMPL 파라미터의 `transl`(골반 이동) 값을 찍어보니 **Y축이 항상 1.2~1.5(사람 키 높이 범위)에 몰려있고, X/Z가 좌우·전후 이동 범위**였다 — 이건 SMPL 원본이 **Y-up 좌표계**(Y=높이)라는 신호다. 반면 Blender 아마추어(레스트포즈)는 이미 확인했듯 **Z-up**(Z=높이)이다. 이 축 변환을 빼먹고 raw transl/회전을 그대로 Blender Z-up 공간에 넣고 있었다.

**수정**: `Rconv = [[1,0,0],[0,0,-1],[0,1,0]]`(Y-up → Z-up, X축 기준 90도 회전)을 전역 회전과 이동 모두에 적용. 그래도 **여전히 붕괴**(실타래 모양)가 재현됐다 — 축 문제는 실재했지만 유일한 원인은 아니었다는 뜻.

### 7.4 근본 원인 확정 — Blender 의존성 그래프 미갱신 (핵심 발견)

축 변환까지 고쳤는데도 안 되자, **회전값을 아예 0(Identity)으로 놓고 rest_basis만 넣는 대조 실험**을 했다 — 이론상 완벽한 T-pose가 나와야 하는데 여전히 붕괴(바운딩박스 span 12m, 정상은 ~1.8m)했다. **이게 결정적 단서였다.** SMPL 데이터나 좌표계가 아니라, **본을 Blender에 적용하는 코드 자체**에 버그가 있다는 뜻이기 때문이다.

**진짜 원인**: `pose_bone.matrix = 절대행렬` 로 부모 본을 먼저 설정한 뒤, 그 직후 자식 본을 설정할 때 Blender가 **의존성 그래프(depsgraph)를 즉시 갱신해주지 않아서**, 자식 본의 setter가 "아직 갱신 안 된(예전) 부모 상태"를 기준으로 자기 위치를 잘못 역산하고 있었다. 부모→자식 순서로 정확히 순회했음에도, 매 본 설정 직후 `bpy.context.view_layer.update()`를 호출하지 않으면 이 오차가 관절마다 누적되어 몸 전체가 늘어난 실처럼 붕괴한다.

**수정**: 매 본의 `pb.matrix = m` 대입 직후 `bpy.context.view_layer.update()`를 강제 호출. 이 한 줄로 identity 테스트가 즉시 완벽한 T-pose(span 1.77m)로 돌아왔다.

> **핵심 키포인트**: 이번 세션에서 실제로 문제를 일으킨 두 가지는 (1) SMPL(Y-up)과 Blender(Z-up)의 좌표계 축 불일치, (2) `pose_bone.matrix` 절대값 setter를 부모→자식 순서로 연속 호출할 때 Blender가 각 호출 사이에 의존성 그래프를 자동으로 갱신해주지 않는다는 것 — 이 두 가지였다. 겉보기 증상(몸이 실타래처럼 붕괴)이 완전히 동일해서 두 원인을 분리해내기 어려웠고, "회전을 아예 0으로 만드는" 대조 실험으로 좌표계 문제와 API 사용 버그를 분리한 것이 돌파구였다.

### 7.5 검증 — 실제 FK 데이터로 재검증

수정된 코드(순수 forward kinematics, 스무딩 없음, rest_basis 합성 + view_layer.update() 픽스 모두 적용)로 실제 SMPL 모션 데이터를 다시 적용해 정면·측면 각 7프레임을 렌더링했다. 전부 해부학적으로 정상인 인체 형태였고, 테니스 스윙 동작(준비 자세 → 팔 뻗기 → 스윙 완료)이 자연스럽게 이어졌다. 최종 산출물: `outputs/kaggle_tennis/smpl_source_fk.fbx`.

### 7.6 언리얼 재도전 — 같은 "허리 뒤틀림" 재현

정리된 `smpl_source_fk.fbx`를 언리얼로 가져와 기존 IK Retargeter(`SMPL_to_Mixamo_Retargeter`)로 Mixamo 캐릭터에 리타겟팅했다. 그런데 **처음 이 프로젝트를 시작했을 때 겪었던 것과 똑같은 "허리가 뒤틀려 보인다"는 증상이 그대로 재현**됐다.

### 7.7 "축 문제"라는 가설을 세우고 실제로 검증 → 반박됨

사용자가 "블렌더와 언리얼의 글로벌 축 자체가 다른 것 아니냐"는 가설을 제기했다. 추측하지 않고 실측으로 검증했다:

- **위치(translation) 검증**: 이미 확보해둔 Blender 레스트포즈 좌표(10개 본)와 언리얼에 임포트된 스켈레톤의 레스트포즈 좌표를 나란히 대조 → `언리얼 = (X, -Y, Z) × 100`(Y축 부호만 반전 + cm 스케일)이 **밀리미터 오차 이내로 완벽히 일치**. 축이 스크램블된 게 아니라 표준적이고 정확한 변환이었다.
- **회전 연속성 검증**: 소스 애니메이션(`SMPL_Source_Anim`)의 Pelvis~어깨 본들을 전 프레임(311프레임)에 걸쳐 프레임 간 회전 변화량을 측정 → 불연속(25도 이상 급변) 0건, 전부 매끄러움.

→ **결론: Blender→언리얼 FBX 변환(위치·회전 모두)은 완벽하게 정상. "축 문제" 가설은 데이터로 반박됨.**

### 7.8 진짜 원인 — 리타겟된 Hips(골반) 본의 회전이 전 프레임 고정됨

같은 방식으로 **리타겟 결과물(Mixamo)**을 검사하니, `Hips` 본만 311프레임 내내 프레임간 회전 변화가 **정확히 0.0도**였고, 그 위 `Spine`(13.8°) `Neck`(13.1°) `Shoulder`(7~8°)는 정상적으로 움직이고 있었다. 골반이 고정된 채 그 위 척추만 돌아가니 눈에는 "허리가 뒤틀린다"로 보이는 것이었다.

리타겟터의 오퍼레이터 스택(UE5.8부터 op 기반 아키텍처)을 들여다보니 "Pelvis Motion"과 "Root Motion" 두 개의 op가 있었고, "Root Motion" op의 `rotate_with_pelvis` 설정이 `False`였다. `True`로 바꾸고 재리타겟했지만 **Hips 회전은 여전히 0.0도로 고정** — "Pelvis Motion" op 자체의 `rotation_alpha`는 이미 1.0(완전 전달)인데도 회전이 넘어오지 않았다. 여기서부터는 언리얼 IK Retargeter 내부(Pelvis Motion op의 실제 회전 처리 경로, 또는 소스/타겟 Retarget Pose 정렬)를 더 깊이 봐야 해서 **시간 관계상 중단, 내일 이어서 진행 예정**.

### 7.9 방향 전환 — 언리얼 대신 Blender에서 직접 Mixamo 캐릭터에 리타겟팅 (성공)

언리얼 조사가 막힌 동안, 오늘 검증 완료한 클린 SMPL 모션(§7.5)을 실제 믹사모 캐릭터 메쉬(`blender/assets/mixamo_character.fbx`, 후드·바지·신발·머리카락까지 스키닝된 실제 자산)에 Blender 안에서 직접 얹어보기로 했다. SMPL 22관절과 믹사모의 대응 본 22개가 부모-자식 구조까지 정확히 1:1로 일치한다는 걸 먼저 확인했으므로(Pelvis↔Hips, L_Hip↔LeftUpLeg, … L_Wrist↔LeftHand), §7.4에서 검증된 것과 같은 방식(`global_rotation @ rest_basis`, FK 위치 전파, `view_layer.update()`)을 믹사모 본 이름으로 그대로 재적용했다.

**여기서 새 버그 두 개를 더 만났다** (둘 다 "믹사모 아마추어 오브젝트 자체에 90도 회전 + 0.01 스케일 보정이 걸려있다"는 사실을 놓쳐서 생긴 것):

1. **레스트 방향 변환 공식 오용**: 이 오브젝트 보정을 좌표계 변환이라고 보고 `RCONV @ basis @ RCONV.transposed()`(켤레/similarity transform)를 썼다. 이 공식은 "같은 공간 안에서 작동하는 연산자를 새 좌표계로 옮길 때" 쓰는 것이고, 여기서 필요했던 건 "로컬→아마추어 기저를 로컬→월드 기저로 바꾸는" 단순 좌측 곱셈(`RCONV @ basis`)이었다. 결과: 머리가 렌더링에서 아예 사라지고 몸통이 이상하게 뒤틀림.
2. **`pose_bone.matrix`가 "월드 공간"이 아니라 "아마추어 오브젝트 로컬 공간"이라는 사실을 놓침**: (1)을 고친 뒤에도 여전히 물구나무선 듯한 이상한 자세가 나왔다. 원인은 내가 모션 데이터를 "월드 좌표"(Z-up, 미터)로 변환해서 `pb.matrix`에 넣고 있었는데, 이 프로퍼티는 애초에 **오브젝트의 로컬 좌표계** 기준이라, 오브젝트 자체가 이미 90도+스케일 보정을 갖고 있는 이 믹사모 리그에서는 "월드 좌표를 로컬 슬롯에 넣는" 이중 변환이 되어버린 것.

**수정**: 변환을 아예 걷어내고, SMPL 원본 그대로(Y-up, 미터, `smpl_params_fk.npz` — Z-up 변환판이 아닌 원판)를 사용하되 위치만 cm 스케일(×100)로 맞춰 믹사모의 **로컬 레스트 데이터**(`bone.head_local`, `bone.matrix_local`, 둘 다 변환 없이 원본 그대로)에 직접 적용. 믹사모의 로컬 공간이 SMPL의 원본 Y-up 공간과 정확히 같은 컨벤션이라는 걸 활용해, 아예 좌표 변환 자체를 생략하는 방향으로 단순화했다.

**결과**: 정면·측면 각 7프레임, 준비 자세부터 스윙 완료까지 전부 해부학적으로 정상인 인체 형태. 실제 믹사모 메쉬(후드·바지·신발·머리카락)까지 완벽하게 따라옴. 허리 뒤틀림 없음.

### 7.10 최종 증거 — 원본 영상과 나란히 비교

원본 테니스 영상(왼쪽)과 오늘 재구축한 클린 SMPL 모션을 얹은 Mixamo 캐릭터(오른쪽)를 `ffmpeg hstack`으로 나란히 붙인 비교 영상: [media/mixamo_fk_clean_comparison.mp4](media/mixamo_fk_clean_comparison.mp4)

### 7.11 오늘 세션 요약

| 단계 | 증상 | 진짜 원인 | 고친 방법 |
|---|---|---|---|
| SMPL→Blender v1 | 캐릭터가 튜브처럼 붕괴 | rest_basis 합성 누락 | `global_rotation @ rest_basis` 복원 |
| SMPL→Blender v2 | 여전히 실타래처럼 붕괴 | ① SMPL(Y-up)·Blender(Z-up) 축 불일치, ② `pose_bone.matrix` 연속 호출 시 depsgraph 미갱신 | ① Rconv 좌표 변환 ② 매 본마다 `view_layer.update()` |
| 언리얼 리타겟 | 허리 뒤틀림 (예전과 동일 증상) | (가설: 축 불일치 → **실측으로 반박**) 진짜: 리타겟된 Hips 회전이 전 프레임 고정 | 미해결 — Pelvis Motion op 내부 조사 필요, 내일 계속 |
| Blender→Mixamo 직접 리타겟 | 머리 소실 → 물구나무선 자세 | ① rest_basis 변환에 켤레 공식 오용 ② `pose_bone.matrix`가 오브젝트 로컬 공간이라는 점 간과 | 좌표 변환 자체를 생략하고 SMPL 원본(Y-up)을 믹사모 로컬 공간에 직접 적용 |

**최종 산출물**: `outputs/kaggle_tennis/smpl_source_fk.fbx`(순정 SMPL, 스무딩 없음), `outputs/kaggle_tennis/mixamo_character_fk_retarget.fbx`(Mixamo 캐릭터 최종본), 비교 영상 [media/mixamo_fk_clean_comparison.mp4](media/mixamo_fk_clean_comparison.mp4).

**재현 스크립트** (전부 이번 세션에 작성, `scripts/` 아래):
- `scripts/rebuild_smpl_fbx_fk.py` — §7.1~7.5, 순정 SMPL 재구축 최종본
- `scripts/retarget_onto_mixamo_blender.py` — §7.9, Mixamo 캐릭터 직접 리타겟 최종본
- `scripts/preview_rest_pose.py`, `scripts/preview_reference_fbx.py` — §7.2 대조군 렌더링
- `scripts/render_stills_fk_retarget.py` — §7.10 비교 영상용 프레임 렌더
- `unreal/scripts/75~91` — §7.6~7.8 언리얼 재도전 전 과정(재임포트/재리타겟/축 검증/회전 연속성 검증/오퍼레이터 스택 조사)

**남은 과제**: 언리얼 IK Retargeter의 Pelvis Motion op가 회전을 Hips에 제대로 전달하지 못하는 문제 — 축 정렬 자체는 이미 검증 완료(§7.7)이므로, 다음 조사는 리타겟터의 Retarget Pose 정렬 상태와 Pelvis Motion op의 실제 회전 계산 경로에 집중해야 한다.
