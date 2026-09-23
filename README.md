# motion-retarget-poc

영상 속 인물의 동작을 뽑아서 다른 3D 캐릭터에 옮겨보는 기술 검증(POC) 프로젝트.

- 요구사항: [PRD.md](PRD.md)
- 기술 설계: [TECH_SPEC.md](TECH_SPEC.md)
- **리타겟팅 떨림(짐벌락) 원인 규명 전체 기록**: [RETARGETING_JITTER_INVESTIGATION.md](RETARGETING_JITTER_INVESTIGATION.md)

## 상태

**핵심 기술 1 파이프라인(영상 → 3D 모션 → Mixamo 캐릭터 리타겟팅) end-to-end 동작 확인, 품질은 부분 해결 상태.** GVHMR(Kaggle GPU) → [Motius](https://github.com/ZeyuLing/Motius)로 SMPL FBX 생성 → Blender + Rokoko 무료 애드온으로 Mixamo 캐릭터에 리타겟팅. 캐릭터 접지·팔다리 방향·목/어깨의 150°+ 짐벌락 스파이크는 근본 원인(FBX가 회전을 오일러로만 저장하는 데서 오는 랩어라운드)을 찾아 해결했지만, 잔여 떨림(19~60°)을 더 줄이려는 후처리는 반복 실패 — 전체 경위는 위 문서 참고.

## 셋업 (최초 1회, 사용자당)

1. Colab에서 [colab/gvhmr_inference.ipynb](colab/gvhmr_inference.ipynb) 열고 `런타임 > 런타임 유형 변경`에서 GPU 선택
2. [smpl.is.tue.mpg.de](https://smpl.is.tue.mpg.de/) / [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de/)에서 무료 가입 후 "파이썬 코드베이스용" 모델 다운로드 (자세한 안내는 노트북 4번 셀 참고)
3. `런타임 > 모두 실행`

## 결과물

- **핵심 기술 1 (오픈소스 3D 리타겟팅): 완료.** 영상(테니스 스윙) → GVHMR 3D 모션 추정(312프레임, 전처리 153초+추론 1초) → Motius로 Mixamo 캐릭터에 SMPL 관절 회전 직접 리타겟팅(팔 방향 오차 평균 8.8°) → Blender 헤드리스 렌더로 결과 확인. GUI 없이 전 과정 스크립트로 실행됨.
- 핵심 기술 2 (상용 서비스 비교): _TBD_

## 알게 된 것 (셋업 과정의 함정들)

- GVHMR 공식 체크포인트 Google Drive 링크는 공유 쿼터 초과로 자주 막힘 → HuggingFace 미러(`camenduru/GVHMR`)로 우회
- `chumpy` 패키지는 기본 pip build-isolation에서 빌드 실패 → `numpy` 먼저 설치 후 `--no-build-isolation`으로 우회
- SMPL·SMPL-X는 완전히 다른 두 사이트에서 따로 받아야 함 (`smpl.is.tue.mpg.de` vs `smpl-x.is.tue.mpg.de`)
- Colab에서 대용량 파일 브라우저 드래그 업로드는 불안정 → 구글 드라이브 경유가 훨씬 안정적
- Blender 헤드리스 **애니메이션** 렌더(EEVEE/Workbench 둘 다)는 Colab의 EGL 초기화 문제로 멈추는 경우가 있음 → 프레임 단위 정지 이미지 렌더(`write_still=True`)는 정상 동작
- `mixamo-llm-mocap` 같은 랜드마크 기반 리타겟 도구는 사람이 프레임 구간별로 스펙을 수작업으로 짜야 해서 자동화 POC엔 부적합 — SMPL 관절 회전을 직접 받는 `Motius`가 훨씬 적합했음
- **Motius 리타겟팅은 팔(어깨~손목) "방향"만 보정하고 "비틀림(roll/twist)"은 전혀 보정하지 않으며, 팔 체인 바깥의 척추·목·다리·손은 방향 보정조차 없음** — Mixamo 캐릭터를 기본 포즈(보통 A포즈)로 받으면 이 구조적 빈틈이 그대로 드러나 팔다리가 뒤틀려 보인다. **Mixamo에서 캐릭터를 받을 때 반드시 "T-pose with skin" 옵션을 선택할 것.** `backend="fbxsdk"`/`backend="blender"` 둘 다 동일한 수학 구조라 백엔드 전환은 해결책이 아니다. 근거·코드 위치는 [TECH_SPEC.md §2.7](TECH_SPEC.md#27-motius-리타겟팅-함정--트위스트-미보정-2026-09-22) 참고
- **GVHMR은 GPU 없이 실행 자체가 안 됨** — `.cuda()`가 핵심 모델 파일 포함 14개 파일에 하드코딩돼 있어 CPU/Apple Silicon(MPS) 둘 다 크래시한다. Colab GPU 무료 쿼터가 막히면 코드를 고치는 대신 [kaggle/gvhmr_inference_kaggle.ipynb](kaggle/gvhmr_inference_kaggle.ipynb)로 Kaggle 무료 GPU(주 30시간)를 쓰는 게 더 빠르다. 근거는 [TECH_SPEC.md §2.8](TECH_SPEC.md#28-gvhmr은-gpu-없이-실행-불가--cuda-하드코딩-2026-09-23) 참고
