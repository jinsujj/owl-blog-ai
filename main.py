import json
import time
import threading
import requests
import re
import html

from kafka import KafkaConsumer, KafkaProducer
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration

# 모델 및 토크나이저 초기화
tokenizer = PreTrainedTokenizerFast.from_pretrained('digit82/kobart-summarization')
model = BartForConditionalGeneration.from_pretrained('digit82/kobart-summarization')

# Kafka 설정
consumer = KafkaConsumer(
    "summary-request",
    bootstrap_servers="110.8.21.243:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="summarizer",
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

producer = KafkaProducer(
    bootstrap_servers="110.8.21.243:9092",
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8")
)

# Editor.js 블록 파서
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
                row_text = " | ".join(row)
                text_blocks.append(row_text)
    return " ".join(text_blocks)

# 블로그 요약 함수 (Kafka/CLI에서 공통 사용)
def summarize_blog(blog_id):
    try:
        print(f"🔍 Processing blogId: {blog_id}")
        response = requests.get(f"https://backend.owl-dev.me/blogs/{blog_id}", timeout=10)
        response.raise_for_status()

        data = response.json()
        content_raw = data.get("content", "")
        content_dict = json.loads(content_raw)

        blocks = content_dict.get("blocks", [])
        full_text = parse_blocks(blocks).replace("\n", " ").strip()

        if not full_text:
            print(f"⚠️ Blog {blog_id} 본문이 비어 있습니다.")
            return
        
        cleand_text = clean_html(full_text)

        start_time = time.time()
        input_ids = tokenizer.encode(cleand_text, return_tensors="pt", truncation=True, max_length=1024)
        summary_ids = model.generate(input_ids, num_beams=30, max_length=300, min_length=80)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        elapsed_time = round(time.time() - start_time, 3)

        result = {
            "blogId": blog_id,
            "summary": summary,
            "elapsedTimeSec": elapsed_time
        }

        # Kafka로 응답 전송
        producer.send("summary-response", result)
        print(f"✅ Published summary for blogId {blog_id} in {elapsed_time} sec")
        print(f"\n📋 Summary:\n{summary}\n")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def clean_html(text):
    # 1. HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    # 2. HTML 엔티티 디코딩 (예: &nbsp; → 공백)
    text = html.unescape(text)
    return text

# Kafka 컨슈머 루프
def kafka_consumer_loop():
    print("📥 Kafka consumer started! Waiting for summary-request...")
    for message in consumer:
        blog_id = message.value.get("id")
        summarize_blog(blog_id)

# CLI 모드
def cli_mode():
    while True:
        blog_id = input("📝 요약할 blog_id를 입력하세요 (exit 입력 시 종료): ").strip()
        if blog_id.lower() == "exit":
            break
        if blog_id.isdigit():
            summarize_blog(int(blog_id))
        else:
            print("⚠️ 숫자 blog_id만 입력 가능합니다.")

# 진입점
if __name__ == "__main__":
    # Kafka는 백그라운드 쓰레드로 실행
    kafka_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
    kafka_thread.start()

    # CLI 모드 실행
    cli_mode()
