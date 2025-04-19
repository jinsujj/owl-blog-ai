from fastapi import FastAPI
from pydantic import BaseModel
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration
import requests
import time
import json
import uvicorn

# 모델 및 토크나이저 로드
tokenizer = PreTrainedTokenizerFast.from_pretrained('digit82/kobart-summarization')
model = BartForConditionalGeneration.from_pretrained('digit82/kobart-summarization')

app = FastAPI()


def parse_blocks(blocks):
    text_blocks = []

    for block in blocks:
        block_type = block.get("type")
        data = block.get("data", {})

        if block_type in ["paragraph", "header", "quote", "customHeader"]:
            text_blocks.append(str(data.get("text", "")))
        elif block_type in ["list", "checklist"]:
            for item in data.get("items", []):
                content = item.get("content") if isinstance(item, dict) else item
                text_blocks.append(str(content))
        elif block_type == "table":
            for row in data.get("content", []):
                row_text = ' | '.join(row)
                text_blocks.append(row_text)

    return ' '.join(text_blocks)


@app.get("/summarize/{blog_id}")
async def summarize(blog_id: int):
    # 1. 외부 API 요청
    api_url = f"https://backend.owl-dev.me/blogs/{blog_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"❌ API 요청 실패: {e}"}

    # 2. content 파싱
    try:
        data = response.json()
        content_raw = data.get("content", "")
        content_dict = json.loads(content_raw)
    except Exception as e:
        return {"error": f"❌ content 파싱 실패: {e}"}

    blocks = content_dict.get("blocks", [])
    full_text = parse_blocks(blocks).replace('\n', ' ').strip()

    if not full_text:
        return {"error": "본문이 비어 있어 요약할 수 없습니다."}

    # 3. 요약 수행
    start_time = time.time()
    input_ids = tokenizer.encode(full_text, return_tensors='pt', truncation=True, max_length=1024)
    summary_ids = model.generate(input_ids, num_beams=18, max_length=200, min_length=80)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    elapsed_time = round(time.time() - start_time, 3)

    return {
        "summary": summary,
        "elapsed_time_sec": elapsed_time
    }


@app.get("/")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

