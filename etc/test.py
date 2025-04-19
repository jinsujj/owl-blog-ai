from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration
import requests
import json
import time 

# 1. 토크나이저 및 모델 로드
tokenizer = PreTrainedTokenizerFast.from_pretrained('digit82/kobart-summarization')
model = BartForConditionalGeneration.from_pretrained('digit82/kobart-summarization')

# 2. 블로그 본문 크롤링 함수 
def get_blog_content(blog_id):
    api_url = f"https://backend.owl-dev.me/blogs/{blog_id}"
    response = requests.get(api_url)
    if response.status_code != 200:
        print("❌ API 요청 실패")
        return ""

    data = response.json()

    # content는 JSON 문자열 → 딕셔너리로 다시 파싱
    content_raw = data.get("content", "")
    try:
        content = json.loads(content_raw)
    except json.JSONDecodeError:
        print("❌ content 파싱 실패")
        return ""

    blocks = content.get("blocks", [])
    text_blocks = []

    for block in blocks:
        block_type = block.get("type")
        data = block.get("data", {})

        if block_type in ["paragraph", "header", "quote", "customHeader"]:
            text_blocks.append(str(data.get("text", "")))

        elif block_type == "list" or block_type == "checklist":
            items = data.get("items", [])
            for item in items:
                content = item.get("content") if isinstance(item, dict) else item
                text_blocks.append(str(content))

        elif block_type == "table":
            table_rows = data.get("content", [])
            for row in table_rows:
                row_text = ' | '.join(row)
                text_blocks.append(row_text)

    return ' '.join(text_blocks)


# 3. 블로그 URL 지정
text = get_blog_content(22)

if not text:
    print("❌ 본문이 비어 있어 요약할 수 없습니다.")
    exit()

# 4. 텍스트 전처리
text = text.replace('\n', ' ').strip()

# 5. 요약 생성
input_ids = tokenizer.encode(text, return_tensors='pt', truncation=True, max_length=1024)

# 요약 생성
for beam in [ 14, 16, 18, 20, 22]:
    print(f"== num_beams: {beam} ==")
    start_time = time.time()
    
    summary_ids = model.generate(input_ids, num_beams=beam, max_length=200, min_length=80)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 3)
    print(elapsed_time)
    print(summary)
   

