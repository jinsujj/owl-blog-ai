FROM python:3.10-slim

# 기본 패키지 설치
RUN apt update && apt install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    libblas-dev \
    g++ \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt .
COPY main.py .
COPY patch/ ./patch/
COPY wheels/torch-1.13.1-*.whl ./wheels/

# pip 업그레이드 및 requirements 설치 (torch 제외!)
RUN pip install --upgrade pip && \
    grep -v "torch" requirements.txt > temp.txt && \
    pip install --no-cache-dir -r temp.txt

# torch wheel 수동 설치
RUN pip install --no-cache-dir ./wheels/torch-1.13.1-*.whl

# transformers 내부 패치 적용
COPY patch/ ./patch/
RUN python -c "\
import shutil, transformers;\
shutil.copyfile('./patch/transformers/modeling_bart.py', transformers.__path__[0] + '/models/bart/modeling_bart.py');\
shutil.copyfile('./patch/transformers/modeling_utils.py', transformers.__path__[0] + '/modeling_utils.py')"


# FastAPI 서버 포트 노출
EXPOSE 8000

# FastAPI 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

