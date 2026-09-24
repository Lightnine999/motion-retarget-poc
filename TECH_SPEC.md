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
| 나머지 의존성(torch 등) 설치 | ✅ 완료 확인 | `torch 2.3.0+cu121`, `cuda available: True`, `torchvision 0.18.0+cu121`, `pytorch3d 0.7.6`, `smplx`/`chumpy`/`ultralytics`까지 전부 import 성공. `pip install -e .`로 `hmr4d` 패키지도 정상 설치. |
| 비-바디모델 체크포인트(gvhmr/hmr2/vitpose/dpvo/yolo) 다운로드 | ⚠️ 원래 경로(Google Drive)는 실패, 대체 경로로 해결 | 공식 문서의 Drive 링크가 **공유 쿼터 초과**로 실제 막혀 있음(`gdown`으로 재현: "Cannot retrieve the public link" / "Too many users have viewed or downloaded this file recently"). 대신 커뮤니티 HuggingFace 미러(`camenduru/GVHMR`)에서 동일 체크포인트를 5.1GB, 약 40초 만에 전부 받음. `yolov8x.pt`는 애초에 GVHMR 전용이 아니라 Ultralytics 공식 배포본이라 `YOLO('yolov8x.pt')` 한 줄로 자체 다운로드됨 — Drive를 거칠 필요 자체가 없었음. |
| SMPL/SMPLX 회원가입 → 파일 확보 | ❌ 여전히 자동화 불가 (최초 1회 한정) | 실제 다운로드 페이지 확인 결과, 필요한 건 각 사이트의 "**SMPL/SMPL-X 파이썬 코드베이스용**" 메인 패키지 하나뿐 — UV맵·VPoser·Homogenus·Blender 애드온·Unity 패키지 등 나머지 항목은 불필요. `gender="neutral"`이 기본값이라 `SMPL_NEUTRAL.pkl` + `SMPLX_NEUTRAL.npz` **2개 파일**만 있으면 된다(성별별 6개 전부 불필요). |
| 전체 파이프라인 실행 | ✅ [colab/gvhmr_inference.ipynb](../colab/gvhmr_inference.ipynb)로 정리 완료 | 위 모든 셀을 하나의 노트북으로 정리. **사람이 개입하는 지점은 "GPU 런타임 선택"과 "SMPL/SMPLX 업로드" 딱 2곳(둘 다 사용자당 최초 1회)** 뿐이고, 그 사이는 전부 `런타임 > 모두 실행`으로 자동 진행된다. |

**재사용성에 대한 결론**: "자동화 안 되는 POC는 쓸모없다"는 우려는 타당하지만, 실제로 남는 수동 작업은 **사용자당 최초 1회, 총 2곳**(GPU 런타임 클릭 1번 + SMPL/SMPLX 계정가입·업로드 1번)뿐이다. SMPL/SMPLX 회원가입은 GVHMR뿐 아니라 SMPL 기반 인체 모델을 쓰는 어떤 도구도 피할 수 없는 라이선스 구조라, 이걸 없애려면 애초에 GVHMR(SMPL 기반)을 포기하고 MediaPipe로 돌아가야 하는데 — 그건 이미 리타겟팅 품질 문제로 기각한 선택지다([§2.4.1](#241-결정-기록--gvhmrcolab-vs-mediapipe-pose-vs-로컬-gpu) 참고). 한 번 계정을 만들고 파일을 받아두면(본인 Drive 등에 보관), 이후 영상을 몇 개를 돌리든 매번 새로 할 필요는 없다.

### 2.7 Motius 리타겟팅 함정 — 트위스트 미보정 (2026-09-22)

두 번째 테니스 영상으로 리타겟팅했을 때 "글로벌 회전값과 타겟 캐릭터의 로컬 피봇 기준이 안 맞아 팔다리가 이상한 방향으로 꺾이거나 뒤틀리는" 문제가 발생해, `Motius` 소스(`motius/motion/fbx/_blender.py`, `_fbxsdk.py`)를 직접 읽어 원인을 확인했다.

**원인**: 두 백엔드 모두 각 본의 회전을 `SMPL 글로벌 회전 × 타겟 본의 로컬 레스트 피봇(matrix_local)`으로 계산한다. 이 계산은 타겟 캐릭터의 레스트 포즈가 SMPL의 T포즈와 같다는 전제 위에 있는데, 전제가 깨지면(Mixamo를 기본 포즈=A포즈로 받으면) 어긋남이 그대로 회전값에 섞인다. 팔 체인(어깨~손목, `_REST_POSE_DIRECTION_CHILD`/`_ARM_DIRECTION_CHILD` 딕셔너리에 정의된 6개 본)에 한해서만 `rotation_difference`로 방향(swing, 3자유도 중 2자유도)을 사후 보정하는데, **나머지 1자유도(비틀림/roll)는 애초에 보정 대상이 아니고, 팔 체인 바깥(척추·목·다리·손)은 방향 보정조차 없다.** `backend="fbxsdk"`와 `backend="blender"`는 이 구조가 완전히 동일해서, 백엔드를 바꿔도 결과는 달라지지 않는다(직접 소스 대조 확인).

**대응**:
1. Mixamo에서 캐릭터를 받을 때 **"T-pose with skin"** 옵션을 선택한다. Motius 자체 문서도 "T포즈가 어깨 보정 오차를 최소화한다"고 명시한다.
2. 리타겟 결과와 함께 생성되는 `<output>.fbx.json`의 `retarget_diagnostics.arm_chain_direction_error_deg_mean/p95/max`를 매번 확인한다. 최초 검증 케이스(핵심 기술 1 완료 시점)의 팔 방향 오차 평균은 8.8°였다 — 이보다 크게 벌어지면 레스트 포즈 불일치를 의심한다.
3. T포즈로 받아도 비틀림이 남으면, 이는 Motius의 구조적 한계(비틀림 미보정)이므로 후처리 스크립트로 말단 본(손목·발목 등)의 트위스트를 별도 재계산하는 보정이 추가로 필요하다 — 아직 미구현.

### 2.8 GVHMR은 GPU 없이 실행 불가 — `.cuda()` 하드코딩 (2026-09-23)

Colab GPU 무료 쿼터가 소진돼 CPU 런타임으로 전환해 봤으나 `tools/demo/demo.py`가 추론 시작 37초 만에 크래시했다(`RuntimeError: Found no NVIDIA driver`). 원인을 grep으로 확인한 결과, **DPVO/SLAM 문제가 아니라 훨씬 근본적인 문제**였다.

**원인**: `demo.py:309`에서 `torch.cuda.get_device_name()`을 조건 없이 호출하는 것을 시작으로, 실행 경로에 걸리는 `.cuda()`/`device="cuda"` 하드코딩이 최소 14개 파일에 퍼져 있다 — `tools/demo/demo.py`, `hmr4d/utils/preproc/{vitfeat_extractor,vitpose,slam}.py`, 그리고 핵심 추론 모델인 `hmr4d/model/gvhmr/gvhmr_pl_demo.py`까지 포함된다. `-s`(`--static_cam`) 옵션이 DPVO(SLAM)는 건너뛰어 주지만, 그 외 경로는 GPU가 없으면 아예 실행되지 않도록 짜여 있다. **로컬 Mac(Apple Silicon MPS)도 "NVIDIA GPU가 아니다"라는 점에서 동일하게 막힌다** — CPU/MPS 둘 다 이 하드코딩을 device-agnostic하게 고치지 않는 한 원천 차단.

**판단**: 14개 파일(그중 일부는 모델 forward pass 내부)에 흩어진 하드코딩을 전부 고치는 건 "패치 몇 줄"이 아니라 숨은 CUDA 전용 연산이 더 나올 수 있는 두더지잡기 리스크가 있어, 소요 시간을 예측할 수 없다고 보고 **패치 트랙은 보류**했다(사용자 판단, 2026-09-23).

**대응 — Kaggle 무료 GPU로 전환**: 코드를 고치는 대신 실제 NVIDIA GPU를 무료로 확보하는 쪽을 택했다. Kaggle 노트북은 T4 x2 또는 P100 GPU를 **주 30시간**(Colab 무료 쿼터보다 넉넉하고 리셋 주기가 명확함) 제공하고, 이미지에 `/opt/conda`가 기본 포함돼 있어 `condacolab` 우회 없이 바로 conda 환경을 만들 수 있다. Colab 버전과 완전히 동일한(패치 없는) 파이프라인을 그대로 재사용하도록 [kaggle/gvhmr_inference_kaggle.ipynb](../kaggle/gvhmr_inference_kaggle.ipynb)를 작성했다. 차이점은 셋업 방식뿐: `condacolab` 대신 이미 있는 `/opt/conda` 사용, SMPL/SMPL-X/캐릭터 FBX는 Colab의 Google Drive 마운트 대신 **Kaggle Dataset**(최초 1회 업로드 후 Add Input으로 재사용)으로 공급한다.

로컬 Mac 환경(conda `gvhmr`, Python 3.10, torch 2.3.0 + MPS 인식, `pytorch3d` 0.7.8 소스 빌드 — macOS SDK 비호환 이슈는 `-Wno-invalid-specialization` 컴파일러 플래그로 우회)은 이미 구성해뒀다. GPU 확보 전략이 바뀌거나(예: 로컬에 eGPU/외장 NVIDIA를 붙이는 등) `.cuda()` 패치를 다시 시도할 필요가 생기면 이 환경을 그대로 재사용할 수 있다.

### 2.9 리타겟팅 최종 파이프라인 — 재현 가이드 (2026-09-24)

§2.7의 Motius 트위스트 미보정 문제와 [RETARGETING_JITTER_INVESTIGATION.md](RETARGETING_JITTER_INVESTIGATION.md) §3~§7의 긴 시행착오(스무딩 제거, 좌표축 변환, Blender depsgraph 갱신 버그) 끝에 확정된 **현재 가장 깨끗한 경로**를 순서대로 정리한다. 실패로 끝난 경로(Rokoko 디스파이크, Unreal IK Retargeter)는 여기서 뺐다 — 그 기록은 investigation 문서에 그대로 남아 있다.

| # | 스크립트 | 실행 환경 | 입력 | 출력 | 핵심 주의점 |
|---|---|---|---|---|---|
| 1 | [kaggle/gvhmr_inference_kaggle.ipynb](kaggle/gvhmr_inference_kaggle.ipynb) | Kaggle GPU | 영상 클립 | `hmr4d_results.pt` | §2.8 참고, GPU 필수 |
| 2 | `scripts/compute_smpl_fk.py` | conda `gvhmr` 환경 (torch+scipy) | `hmr4d_results.pt` | `smpl_params_raw.npz`, `smpl_params_fk.npz`, `smpl_params_fk_zup.npz` | **Motius를 거치지 않고** 직접 axis-angle → 부모체인 FK 합성. 스무딩이 전혀 섞이지 않는 게 핵심(§7.0) |
| 3 | `scripts/export_smpl_source.py` (최초 1회만) | conda `gvhmr` (Motius) | `hmr4d_results.pt` | `smpl_source_clean.fbx` | 이 파일의 **애니메이션 자체는 쓰지 않는다** — 4번 단계에서 본 계층/레스트포즈(rest_basis)만 재사용하는 뼈대 소스로 임포트함 |
| 4 | `scripts/rebuild_smpl_fbx_fk.py` | Blender `--background --python` | `smpl_params_fk_zup.npz` + `smpl_source_clean.fbx`(레스트포즈용) | `smpl_source_fk.fbx`, `fk_preview/*.png`(검증용 스크린샷) | `pose_bone.matrix = 절대행렬` 대입 직후 **반드시 `bpy.context.view_layer.update()`를 호출**할 것 — 안 하면 Blender가 자식 본 계산 시 부모의 갱신 전 상태를 참조해 몸 전체가 붕괴한다(§7.4, 이번 파이프라인에서 가장 잘 놓치는 지점) |
| 5 | `scripts/retarget_onto_mixamo_blender.py` | Blender `--background --python` | `smpl_params_fk.npz`(Y-up 원본, zup 아님) + `blender/assets/mixamo_character.fbx` | `mixamo_character_fk_retarget.fbx`, `mixamo_fk_preview/*.png` | 대상 리그 오브젝트에 자체 회전/스케일 보정이 걸려있을 수 있다(Mixamo가 그렇다 — 90°+×0.01). **`pose_bone.matrix`는 월드 공간이 아니라 그 오브젝트의 로컬 공간**이므로, 좌표를 세계 공간으로 미리 변환하지 말고 리그의 원본 로컬 컨벤션(Y-up)을 그대로 쓸 것(§7.9) |
| 6 | `scripts/render_stills_fk_retarget.py` | Blender `--background --python` | `mixamo_character_fk_retarget.fbx` | `frames_fk_retarget/frame_%04d.png` | 카메라를 고정값으로 두지 말고 메시 바운딩박스를 전체 프레임에서 샘플링해 자동으로 맞출 것 — 캐릭터 스케일/루트 위치가 파이프라인마다 달라 고정 카메라는 쉽게 프레임 밖으로 나간다 |
| 7 | `ffmpeg` (PNG 시퀀스 → mp4, 원본과 hstack) | 셸 | `frames_fk_retarget/`, 원본 테니스 영상 | `side_by_side_fk_retarget.mp4` | `ffmpeg -y -framerate 30 -i frames_fk_retarget/frame_%04d.png -c:v libx264 -pix_fmt yuv420p mixamo_fk_retarget_render.mp4` 후 `ffmpeg -i <위 결과> -i <원본> -filter_complex "[1:v]scale=-2:480[a];[0:v]scale=-2:480[b];[a][b]hstack=inputs=2" side_by_side_fk_retarget.mp4` |

**알려진 한계**: 2~7번 스크립트 전부 파일 상단에 입출력 경로가 **하드코딩**돼 있다(새 영상으로 돌리려면 각 스크립트 상단의 경로 상수를 직접 고쳐야 함) — CLI 인자화는 아직 안 돼 있다. 결과 비교 영상: [media/mixamo_fk_clean_comparison.mp4](media/mixamo_fk_clean_comparison.mp4).

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
