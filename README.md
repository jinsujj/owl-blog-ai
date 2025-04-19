## how to execute
docker compose build --no-cache

## how to send api
curl -X 'GET' 'https://ai.owl-dev.me/summarize/22' -H 'accept: */*'






# KoBART 요약 API - Raspberry Pi 5 환경 구성

이 프로젝트는 `digit82/kobart-summarization` 모델을 Raspberry Pi 5 (ARMv8, 64bit) 환경에서 사용할 수 있도록 Docker 기반으로 구성한 FastAPI 요약 API 서버입니다.

## 📦 프로젝트 구조

llm/
├── Dockerfile                       # 도커 이미지 정의
├── docker-compose.yml              # 도커 컴포즈로 앱 실행 자동화
├── main.py                         # FastAPI 기반 kobart 요약 API
├── patch/                          # transformers 내부 파일 덮어쓰기용 패치
│   └── transformers/
│       ├── modeling_bart.py        # BART 모델 내부 수정 파일
│       └── modeling_utils.py       # 관련 유틸 수정 파일
├── readmd.md                       # 프로젝트 구조 및 설명 파일
├── requirements.txt                # 필요한 Python 패키지 목록
└── wheels/
    └── torch-1.13.1-...aarch64.whl # ARM64용 PyTorch 수동 설치 파일


## 🐧 왜 이렇게 구성했을까?

### ✅ Raspberry Pi 5 + Linux ARM64 환경의 제약

- HuggingFace `transformers` 라이브러리의 최신 버전은 ARM 아키텍처(PyTorch)에서 일부 오류 발생
- `torch.distributed.tensor` 또는 `torch.compiler` 관련 AttributeError 이슈
- 따라서 transformers 일부 파일을 수동으로 패치해 적용

### ✅ PyTorch 설치 이슈

- 공식 PyPI에서는 ARM64용 PyTorch를 제공하지 않음
- [https://torch.kmtea.eu](https://torch.kmtea.eu) 사이트에서 Raspberry Pi 전용 `torch-1.13.1` 버전 `.whl` 파일을 수동 다운로드하여 설치

### ✅ 컨테이너화의 목적

- 복잡한 의존성 문제를 Docker로 격리
- 다른 동일한 Raspberry Pi 장비에서도 빠르게 재사용 가능
- FastAPI 서버 형태로 RESTful API 제공

---

## 🚀 실행 방법

```bash
# 1. 도커 이미지 빌드 및 실행
docker-compose up --build

# 2. 서버 확인
curl https://ai.owl-dev.me           # Health Check
curl -X POST https://ai.owl-dev.me/summarize -H "Content-Type: application/json" -d '{"id": 22}'

# owl-blog-ai
# owl-blog-ai
