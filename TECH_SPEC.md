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
├── setup.sh                    # 로컬 의존성/Blender 확인 원커맨드 셋업
├── requirements.txt             # 버전 고정된 파이썬 의존성
├── .env.example                 # 필요한 API 키 목록 (실제 키는 .env, git 미추적)
├── inputs/                  # 원본/트리밍 영상 (git 추적 안 함)
├── colab/
│   └── gvhmr_inference.ipynb   # GVHMR 추론 — Colab에서 "런타임 > 모두 실행"이면 끝
├── blender/
│   ├── retarget_render.py      # bpy 헤드리스 스크립트 (단일 커맨드로 실행)
│   └── assets/                 # Mixamo FBX 캐릭터 (git 추적 안 함, 크기 큼 — download_assets.sh로 받음)
├── scripts/
│   └── download_assets.sh      # Mixamo 캐릭터 등 큰 파일 자동 다운로드
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

**GVHMR 추론은 Colab GPU를 팀 전체 기본 경로로 고정한다** (로컬 GPU 대체 안 함). 팀원마다 노트북이 맥/윈도우로 갈리고 그래픽카드 유무도 다른데, Colab을 쓰면 하드웨어와 무관하게 브라우저 + 구글 계정 + GPU 런타임 버튼 1번으로 모두 같은 경험을 갖는다. 엔비디아 GPU가 있는 윈도우 팀원이라면 로컬 실행도 이론적으로 가능하지만(WSL2 + 엔비디아 WSL 드라이버 + conda Python 3.10 환경 구성 필요), 이 경로가 Colab보다 셋업이 더 복잡해서 팀 기본값으로 채택하지 않는다 — 원하는 사람만 선택적으로 시도하는 것으로 남겨둔다.

### 2.4.1 결정 기록 — GVHMR(Colab) vs MediaPipe Pose vs 로컬 GPU

핵심 기술 1의 포즈 추정 방식을 다시 검토했으나, **GVHMR + Colab 경로를 그대로 유지**하기로 확정한다.

| 대안 | 검토 결과 |
|---|---|
| MediaPipe Pose Landmarker (완전 로컬) | 설치는 가장 쉽지만, z축(깊이) 추정이 노이즈가 커서(공식 이슈·논문에서 공통 지적) 리타겟팅용으로 부적합. 관절 **위치**만 주고 **회전값**은 안 줘서, 오히려 우리가 위치→회전 변환 로직을 직접 만들어야 해 구현 부담이 더 크다. |
| GVHMR + 로컬 GPU (엔비디아+Windows 한정) | 이론상 가능하지만 WSL2 셋업이 Colab보다 복잡하고, 엔비디아가 아닌 팀원(맥, AMD/인텔 그래픽)은 원천적으로 불가능해 팀 공통 기본값이 될 수 없다. |
| **GVHMR + Colab (채택)** | SMPL 기반이라 관절 회전값을 그대로 제공해 리타겟팅에 구조적으로 적합. 하드웨어 무관하게 팀 전체가 동일한 경험. SMPL/SMPLX 회원가입은 어느 경로를 택해도 피할 수 없는 절차라 Colab을 선택하는 데 불리한 요소가 아니다. |

### 2.5 자동화 / 재현성 (다른 사람이 쉽게 쓸 수 있게)

"나만 실행 가능한 수동 절차"가 되지 않도록, 각 단계를 아래처럼 스크립트/노트북 단위로 묶는다.

| 절차 | 자동화 방법 |
|---|---|
| 로컬 파이썬 의존성 설치 | `requirements.txt` 버전 고정 + `setup.sh` 한 번 실행 (venv 생성 → 설치 → Blender 설치 여부 체크) |
| GVHMR 추론 (Colab) | 노트북 상단에 "런타임 > 모두 실행"만 누르면 되도록 셀 순서 구성. 단, SMPL 체크포인트는 각자 라이선스 동의가 필요해 **완전 자동화가 불가능한 지점** — 노트북 안에 "여기서부터는 본인 계정으로 직접 받아야 함" 안내를 명확히 남긴다.
| Mixamo 캐릭터 등 대용량 에셋 | git에 올리지 않고 `scripts/download_assets.sh`로 받게 한다. |
| Blender 리타겟/렌더링 | `blender --background --python blender/retarget_render.py -- <입력파일>` 한 줄 커맨드로 끝. Blender GUI 조작 없음. |
| 상용 API 호출 | `.env.example`을 `.env`로 복사해 키만 채우면 바로 실행되는 스크립트. |

> 위 표에서 유일하게 완전 자동화가 안 되는 지점(SMPL 라이선스 동의)은 스파이크에서 실제로 어디까지 자동화되고 어디서부터 사람이 개입해야 하는지 확인한다.

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

### 2.6 GVHMR 셋업 스파이크 결과 (2026-09-22, Colab에서 실측)

`git clone` → `requirements.txt` 설치 → 체크포인트 준비 순서로 실제로 찔러본 결과:

| 항목 | 자동화 가능 여부 | 근거 |
|---|---|---|
| 리포 클론 | ✅ 완전 자동화 | `git clone` 그대로 동작 |
| GVHMR/HMR2/ViTPose/YOLO/DPVO 체크포인트 | ✅ 자동화 가능 | 공개 Google Drive 폴더 — 로그인 리다이렉트 없이 200 응답 확인, `gdown`으로 스크립트 다운로드 가능 |
| **SMPL·SMPLX 바디 모델** | ❌ **자동화 불가 — 사람이 반드시 개입** | `smpl.is.tue.mpg.de` / `smpl-x.is.tue.mpg.de`에서 **개인 계정으로 라이선스 동의 후** 다운로드해야 함. 각자 이메일 인증이 필요한 구조라 스크립트로 대신 받아줄 수 없다. |
| **GPU 런타임** | ⚠️ 수동 1회 설정 필요 | Colab 기본 런타임은 GPU 미연결 상태(`nvidia-smi` 없음). "런타임 > 런타임 유형 변경"에서 GPU를 코드가 아니라 **UI에서 직접** 선택해야 함. |
| **Python 버전 호환성** | ⚠️ 예상보다 손이 많이 감 | 공식 `requirements.txt`가 `pytorch3d`를 **Python 3.10(cp310) 전용 wheel**로 고정(`pytorch3d-0.7.6-cp310-cp310-...whl`). Colab 기본 Python은 3.13.15라 그대로 설치 시 `is not a supported wheel on this platform` 에러로 실패함(직접 재현 확인). `condacolab`로 Python 3.10 conda 환경을 만들어야 공식 설치 경로를 그대로 따를 수 있다. |

**결론**: "원클릭 자동화"는 리포 클론·비-바디모델 체크포인트·Python 3.10 환경 구성까지는 스크립트로 묶을 수 있지만, **SMPL/SMPLX 회원가입 + GPU 런타임 선택 2가지는 각 사용자가 최초 1회 수동으로 해야 하는 구조적 한계**다. README에 "이 2단계는 자동화 대상이 아니다"라고 명시하고, 나머지는 `colab/gvhmr_inference.ipynb`에 셀 순서로 자동화한다.

### 2.6.1 2차 스파이크 결과 — GPU 런타임에서 실제 설치 진행 (2026-09-22)

GPU 런타임으로 전환 후(전환 시 VM이 초기화되어 클론부터 재실행 필요) 실제 설치를 진행하며 추가로 확인한 내용:

| 항목 | 결과 | 근거 |
|---|---|---|
| Python 3.10 환경 구성 | ✅ 자동화 가능 | `condacolab` 패키지로 conda(miniforge) 설치 → `conda create -n gvhmr python=3.10` 순서를 노트북 셀로 그대로 자동화 가능. `condacolab.install()` 실행 시 커널이 1회 자동 재시작되는 점만 노트북 안내문에 명시하면 됨. |
| `chumpy` 설치 실패 | ⚠️ 알려진 함정, 우회 방법 확인 | 기본 `pip install`(build isolation 켜짐)은 chumpy 빌드용 임시 환경에 최신 numpy가 깔려 `numpy.distutils`가 없어서 실패. **`numpy==1.23.5`를 먼저 설치한 뒤 `pip install --no-build-isolation`으로 chumpy만 따로 설치**하면 해결됨(직접 재현·해결 확인). `requirements.txt` 전체 설치 스크립트에 이 순서를 반영해야 한다. |
| 나머지 의존성(torch 등) 설치 | 🔄 확인 중 | 용량이 커서 설치에 몇 분 소요 — 이 문서 갱신 시점 기준 진행 중, 결과 확인되는 대로 본 표에 추가 예정. |

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
