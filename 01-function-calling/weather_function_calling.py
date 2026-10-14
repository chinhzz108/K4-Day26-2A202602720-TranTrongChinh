"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

import json
import os
import sys

from pathlib import Path
from dotenv import load_dotenv

# Load root .env
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }

    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run_live(prompt: str, client: genai.Client) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while resp.function_calls:
        # Thêm phản hồi của model vào lịch sử hội thoại
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            result = get_weather(**fc.args)  # <-- app chạy, không phải model
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )

    # 5. Model tổng hợp câu trả lời cuối
    return resp.text


def run_mock_simulation(prompt: str) -> str:
    """Mô phỏng 5 bước của Function Calling khi không có API key trực tiếp."""
    print("ℹ️  [Chế độ Demo / Offline] Mô phỏng vòng lặp Function Calling:")
    print("   Bước 1: App chuẩn bị tool declaration (name='get_weather', param='city').")
    print(f"   Bước 2: Gửi câu hỏi cho Gemini: '{prompt}'")
    print("   Bước 3: Model phân tích prompt và yêu cầu gọi 2 function calls:")
    
    cities = ["Hà Nội", "Đà Nẵng"]
    results = {}
    for city in cities:
        print(f"     [model yêu cầu] get_weather(city='{city}')")
        res = get_weather(city)
        print(f"     [app thực thi]  -> {res}")
        results[city] = json.loads(res)
        
    print("   Bước 4: App đóng gói kết quả thực thi gửi lại cho Model.")
    print("   Bước 5: Model tổng hợp câu trả lời cuối cho người dùng:\n")
    
    answer = (
        f"🌧️ Hôm nay tại Hà Nội nhiệt độ khoảng {results['Hà Nội']['nhiệt_độ']}, "
        f"{results['Hà Nội']['thời_tiết']}, độ ẩm {results['Hà Nội']['độ_ẩm']}. "
        "Bạn nhớ mang ô hoặc áo mưa khi ra ngoài nhé!\n"
        f"🌤️ Trong khi đó tại Đà Nẵng, thời tiết {results['Đà Nẵng']['thời_tiết']} với nhiệt độ {results['Đà Nẵng']['nhiệt_độ']}, "
        "khá dễ chịu cho các hoạt động ngoài trời."
    )
    return answer


def run(prompt: str) -> str:
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            return run_live(prompt, client)
        except Exception as e:
            print(f"⚠️ Không thể kết nối Gemini API ({e}).")

    if groq_key:
        try:
            from weather_groq_function_calling import run_groq_function_calling
            return run_groq_function_calling(prompt)
        except Exception as e:
            print(f"⚠️ Không thể kết nối Groq API ({e}).")

    return run_mock_simulation(prompt)


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:\n", run(question))

