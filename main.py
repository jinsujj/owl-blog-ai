import json
import time
import threading
import requests
import re
import html

from kafka import KafkaConsumer, KafkaProducer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tokenizer = AutoTokenizer.from_pretrained("lcw99/t5-base-korean-text-summary")
model = AutoModelForSeq2SeqLM.from_pretrained("lcw99/t5-base-korean-text-summary")


# Kafka 설정
consumer = KafkaConsumer(
    "summary-request",
    bootstrap_servers="kafka:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="summarizer",
    max_poll_interval_ms=360000, #10 분
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

producer = KafkaProducer(
    bootstrap_servers="kafka:9092",
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
        
        input_text = "summarize: 이 내용을 독자가 이해할 수 있도록 설명하듯 요약해줘. 내용: ..." + clean_html(full_text)

        start_time = time.time()
        input_ids = tokenizer.encode(input_text, return_tensors="pt", truncation=True, max_length=1024)
        summary_ids = model.generate(input_ids, num_beams=8, max_length=500, min_length=200)
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

def kafka_consumer_loop():
    print("📥 Kafka consumer started! Waiting for summary-request...")
    for message in consumer:
        blog_id = message.value.get("id")
        summarize_blog(blog_id)

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
    kafka_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
    kafka_thread.start()

    # Docker 컨테이너에서는 CLI 모드 비활성화
    import os
    if os.environ.get("ENABLE_CLI", "false").lower() == "true":
        cli_mode()
    else:
        # Kafka만 돌리고 컨테이너는 계속 살아 있게 유지
        while True:
            time.sleep(60)
