# motion-retarget-poc

영상 속 인물의 동작을 뽑아서 다른 3D 캐릭터에 옮겨보는 기술 검증(POC) 프로젝트.

- 요구사항: [PRD.md](PRD.md)
- 기술 설계: [TECH_SPEC.md](TECH_SPEC.md)

## 상태

**핵심 기술 1 전체 파이프라인(영상 → 3D 모션 → Mixamo 캐릭터 리타겟팅) end-to-end 검증 완료.** GVHMR 셋업부터 [colab/gvhmr_inference.ipynb](colab/gvhmr_inference.ipynb)로 자동화되고, 그 결과(`hmr4d_results.pt`)를 [Motius](https://github.com/ZeyuLing/Motius) 라이브러리로 Mixamo 캐릭터 FBX에 리타겟팅한 뒤 Blender 헤드리스 렌더로 실제 동작하는 캐릭터를 눈으로 확인했다(테니스 스윙 영상 → 캐릭터가 같은 스윙 동작 재현).

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
