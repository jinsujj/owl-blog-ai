from kafka import KafkaConsumer, KafkaProducer
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration
import json
import time

# 모델 및 토크나이저 초기화
tokenizer = PreTrainedTokenizerFast.from_pretrained('digit82/kobart-summarization')
model = BartForConditionalGeneration.from_pretrained('digit82/kobart-summarization')

# Kafka 설정
consumer = KafkaConsumer(
    "summary-request",
    bootstrap_servers="kafka:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="summarizer",
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

# 블로그 요약 처리 루프
print("📥 Kafka consumer started! Waiting for blog-summarize-request...")

for message in consumer:
    try:
        blog_id = message.value.get("id")
        print(f"🔍 Received request for blogId: {blog_id}")

        # 블로그 API 요청
        response = requests.get(f"https://backend.owl-dev.me/blogs/{blog_id}", timeout=10)
        response.raise_for_status()

        data = response.json()
        content_raw = data.get("content", "")
        content_dict = json.loads(content_raw)

        blocks = content_dict.get("blocks", [])
        full_text = parse_blocks(blocks).replace("\n", " ").strip()

        if not full_text:
            print(f"⚠️ Blog {blog_id} 본문이 비어 있습니다.")
            continue

        start_time = time.time()
        input_ids = tokenizer.encode(full_text, return_tensors="pt", truncation=True, max_length=1024)
        summary_ids = model.generate(input_ids, num_beams=18, max_length=200, min_length=80)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        elapsed_time = round(time.time() - start_time, 3)

        result = {
            "blogId": blog_id,
            "summary": summary,
            "elapsedTimeSec": elapsed_time
        }

        # 결과 전송
        producer.send("summary-response", result)
        print(f"✅ Published summary for blogId {blog_id} in {elapsed_time} sec")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
