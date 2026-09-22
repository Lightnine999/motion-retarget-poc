# motion-retarget-poc

영상 속 인물의 동작을 뽑아서 다른 3D 캐릭터에 옮겨보는 기술 검증(POC) 프로젝트.

- 요구사항: [PRD.md](PRD.md)
- 기술 설계: [TECH_SPEC.md](TECH_SPEC.md)

## 상태

핵심 기술 1(GVHMR 3D 모션 추정) 셋업 자동화 검증 완료. [colab/gvhmr_inference.ipynb](colab/gvhmr_inference.ipynb)를 열면 GPU 런타임 선택 + SMPL/SMPLX 업로드(둘 다 최초 1회) 외에는 `런타임 > 모두 실행`으로 끝까지 진행된다.

## 셋업 (최초 1회, 사용자당)

1. Colab에서 [colab/gvhmr_inference.ipynb](colab/gvhmr_inference.ipynb) 열고 `런타임 > 런타임 유형 변경`에서 GPU 선택
2. [smpl.is.tue.mpg.de](https://smpl.is.tue.mpg.de/) / [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de/)에서 무료 가입 후 "파이썬 코드베이스용" 모델 다운로드 (자세한 안내는 노트북 4번 셀 참고)
3. `런타임 > 모두 실행`

## 결과물 (진행 중)

- 핵심 기술 1 (오픈소스 3D 리타겟팅): Colab 셋업 자동화 완료, Blender 리타겟팅/렌더링 단계는 다음 작업
- 핵심 기술 2 (상용 서비스 비교): _TBD_
