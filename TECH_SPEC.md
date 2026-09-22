# 모션 리타겟팅 POC — 기술 명세서

> STATUS: DRAFT
> 작성일: 2026-09-22
> 관련 문서: [PRD.md](PRD.md)

## 1. 전체 아키텍처

```
                         ┌─────────────────────────┐
                         │   입력 영상 1개           │
                         │ (유튜브 다운로드 / 촬영)   │
                         └───────────┬──────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                        │
        [핵심 기술 1: 3D 리타겟팅]              [핵심 기술 2: 상용 서비스 비교]
                 │                                        │
     ① GVHMR (Colab, GPU)                     ① 키프레임 이미지 추출 (로컬)
     영상 → 3D 월드좌표 모션(SMPL)                          │
                 │                             ② Kling / 힉스필드 / Seedance 2.0
     ② Blender 헤드리스 (로컬)                    API 호출 (로컬, 오케스트레이션)
     GVHMR 결과 → Mixamo 캐릭터 리타겟                       │
     → 렌더링                                  ③ 결과 영상 저장 + 비교표 작성
                 │                                        │
     ③ 결과 MP4                                ④ 결과 MP4 N개 + 비교표
                 │                                        │
                 └───────────────┬────────────────────────┘
                                  │
                         ④ README에 결과 정리 (팀 공유)
```

## 2. 핵심 기술 1 — 오픈소스 3D 모션 리타겟팅

### 2.1 단계별 상세

| 단계 | 실행 위치 | 도구/모델 | 입력 | 출력 |
|---|---|---|---|---|
| 2-1. 영상 준비 | 로컬 | `yt-dlp` | 유튜브 URL 또는 촬영 파일 | 5~15초 클립 (mp4) |
| 2-2. 3D 모션 추정 | Colab (GPU) | [GVHMR](https://github.com/zju3dv/GVHMR) | 클립 | SMPL 파라미터 시퀀스 (`.pt`/`.npz`) |
| 2-3. 리타겟팅 + 렌더링 | 로컬 (Blender 헤드리스) | Blender `bpy` 스크립트 (참고: [mixamo-llm-mocap](https://github.com/squall01337/mixamo-llm-mocap), 대체재: [Motius](https://github.com/ZeyuLing/Motius)) | SMPL 모션 + Mixamo FBX 캐릭터 | 렌더링된 MP4 |

### 2.2 모델 선정 근거

**GVHMR** (zju3dv, SIGGRAPH Asia 2024 / TPAMI 2026)
- 영상 하나에서 중력·카메라 기준이 아닌 **월드 좌표계 기준** 3D 모션을 복원하는 최신 오픈소스 모델. WHAM·4D-Humans·ViTPose 계보를 이어받아 검증된 방식을 쓴다.
- 내부적으로 2D 관절 검출(ViTPose류) → 시계열 3D lifting → SMPL 파라미터 회귀까지 한 번에 처리한다. 순수 OpenPose(2D 좌표만)로는 얻을 수 없는 **관절 회전값**을 직접 제공하기 때문에 3D 캐릭터 리타겟팅에 필수적이다.
- 셋업 비용: SMPL 바디 모델 라이선스 동의 + 체크포인트 다운로드(수 GB) 필요. GPU 필요 → Colab에서 실행.

**리타겟팅**: `mixamo-llm-mocap` 리포는 GVHMR 추정 결과를 Mixamo 리깅 캐릭터에 Blender로 자동 리타겟팅하는 파이프라인을 이미 제공한다 (2026-08 갱신). 이걸 그대로 가져다 쓰거나, 참고해서 우리 스크립트로 재구성한다. 막히면 `Motius`(SMPL→FBX 변환 범용 도구)로 대체한다.

**렌더링**: Blender를 GUI로 열지 않고 `blender --background --python render.py` 형태의 **헤드리스 커맨드라인 실행**으로 "캐릭터 로드 → 리타겟 → 렌더"를 한 번에 처리해서 MP4를 직접 뽑는다. glTF 웹 뷰어 방식은 본 축(axis) 변환 이슈 등 호환성 리스크가 있어 1차 구현에서는 제외하고, 여유가 있으면 스트레치 목표로 남긴다.

### 2.3 디렉토리 구조 (제안)

```
motion-retarget-poc/
├── PRD.md
├── TECH_SPEC.md
├── README.md
├── inputs/                  # 원본/트리밍 영상 (git 추적 안 함)
├── colab/
│   └── gvhmr_inference.ipynb   # GVHMR 추론 (Colab 실행용)
├── blender/
│   ├── retarget_render.py      # bpy 헤드리스 스크립트
│   └── assets/                 # Mixamo FBX 캐릭터 (git 추적 안 함, 크기 큼)
├── outputs/
│   └── core1_3d_retarget/      # 최종 MP4 결과
└── .gitignore
```

### 2.4 실행 환경 분담

| 단계 | 환경 | 이유 |
|---|---|---|
| 영상 다운로드/트리밍 | 로컬 Mac | 가벼운 I/O 작업 |
| GVHMR 추론 | Colab GPU | SMPL 체크포인트 + GPU 필요한 무거운 딥러닝 연산 |
| Blender 리타겟/렌더링 | 로컬 Mac | GPU보다는 CPU/Blender 엔진 의존, 로컬 Blender 앱 활용이 자연스러움 |

## 3. 핵심 기술 2 — 상용 AI 영상 서비스 비교

### 3.1 대상 서비스

| 서비스 | 기능 | 연동 방식 |
|---|---|---|
| **Kling Motion Control** (2.6/3.0) | 이미지에 모션 참조 영상을 적용해 애니메이션 생성 | REST API (Replicate `kwaivgi/kling-v2.6-motion-control` 또는 PiAPI 경유) |
| **Higgsfield Genjutsu** | 참조 영상의 모션/카메라 워크를 유지하며 인물·오브젝트 교체 | 공식 REST API 없음 — Python SDK(`higgsfield-client`) 또는 CLI, `cloud.higgsfield.ai` 경유 |
| **Seedance 2.0** (ByteDance) | 이미지+텍스트 기반 고품질 영상 생성, 모션 안정성 강점 | REST API (wavespeed.ai 경유) |

> 참고: 사용자가 언급한 "시댄스 2.0"은 검색 결과 정확히 일치하는 서비스명이 없어, 발음이 유사한 **Seedance 2.0**으로 추정하고 진행한다. 실제 의도한 서비스가 다르면 이 표를 교체한다.

### 3.2 실행 흐름

1. 2.1에서 준비한 클립에서 대표 키프레임 이미지 1장 추출 (`ffmpeg`).
2. 같은 클립을 "모션 참조 영상"으로 각 서비스 API에 전달.
3. 서비스별 결과 영상을 `outputs/core2_commercial_compare/<서비스명>/`에 저장.
4. 결과를 나란히 비교하는 표(매끄러움 주관 평가, 소요 시간, 비용, 실패 여부)를 README에 정리.

### 3.3 주의사항

- API 키는 `.env` 파일로 관리하고 저장소에 커밋하지 않는다 (`.gitignore`에 포함).
- 각 서비스는 유료이므로, 실제 호출 전에 요금을 확인하고 서비스당 1~2회 호출로 제한한다.
- Higgsfield는 공개 REST API가 없어 다른 두 서비스와 통합 난이도가 다를 수 있음 — 막히면 웹 UI 수동 실행 후 결과만 저장하는 것으로 대체한다.

## 4. 한계 및 향후 확장

- 이번 POC는 사람 1명, 단순 동작(카메라 컷 없음)만 대상으로 한다.
- 손가락/표정 등 디테일 리타겟팅은 다루지 않는다.
- 렌더링 결과는 Mixamo 기본 캐릭터 기준이며, 커스텀 캐릭터 호환성은 검증하지 않는다.
- 추후 완성도를 높인다면: glTF 웹 뷰어 추가, VRM 캐릭터 지원, 다중 인물 처리, 실시간 파이프라인화 등을 고려할 수 있다.

## 5. 의존성 (초안)

- Python 3.11+, `yt-dlp`, `ffmpeg-python`
- GVHMR 리포지토리 + 요구 패키지 (PyTorch, SMPL 체크포인트)
- Blender 4.x (로컬 설치, `bpy` 헤드리스 실행)
- `python-dotenv` (API 키 관리)
- 각 상용 서비스 SDK/HTTP 클라이언트 (`requests` 또는 서비스별 공식 SDK)
