"""Minh hoạ FUNCTION CALLING thuần với Groq Cloud (Model: qwen/qwen3.8-27b).

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720

Tool `get_weather` được định nghĩa schema thủ công và thực thi ngay trong app.
Groq LLM quyết định gọi tool nào và sinh JSON tham số; app là nơi chạy hàm thật.

Cách chạy:
    python weather_groq_function_calling.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import httpx

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đọc key từ environment hoặc .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1") + "/chat/completions"

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧 🌡️). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo khoác, nhiệt độ dễ chịu...)."
)

# 1. App tự định nghĩa schema của tool (OpenAI / Groq format)
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Lấy thông tin thời tiết hiện tại của một thành phố",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Tên thành phố (ví dụ: Hà Nội, Đà Nẵng, Hồ Chí Minh)"
                }
            },
            "required": ["city"]
        }
    }
}

TOOLS = [WEATHER_TOOL]


# 2. App tự thực thi tool (hàm Python thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của city."""
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


def run_groq_function_calling(prompt: str) -> str:
    """Gửi prompt tới Groq, xử lý Function Calling và trả về câu trả lời."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]

    print(f"▶ Gửi prompt tới Groq ({GROQ_MODEL}): '{prompt}'")

    # 3. Bước 1: Gửi prompt + tools tới Groq
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(GROQ_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        message = data["choices"][0]["message"]
        messages.append(message)

        # 4. Bước 2: Kiểm tra nếu Groq yêu cầu gọi tools
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            return message.get("content", "")

        print(f"\n🔍 Groq yêu cầu thực hiện {len(tool_calls)} tool call(s):")
        for tc in tool_calls:
            call_id = tc["id"]
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            print(f"  [Model quyết định] Gọi hàm '{fn_name}' với tham số: {fn_args}")

            # App tự chạy hàm thật
            if fn_name == "get_weather":
                result = get_weather(**fn_args)
            else:
                result = json.dumps({"error": f"Unknown tool {fn_name}"})

            print(f"  [App thực thi]     -> {result}")

            # Đóng gói kết quả gửi lại cho Groq
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": fn_name,
                "content": result,
            })

        # 5. Bước 3: Gửi kết quả tool lại cho Groq để tổng hợp câu trả lời cuối
        print(f"\n▶ Gửi kết quả thực thi về Groq ({GROQ_MODEL}) để tổng hợp...")
        payload_final = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.3,
        }
        resp_final = client.post(GROQ_URL, headers=headers, json=payload_final)
        resp_final.raise_for_status()
        final_answer = resp_final.json()["choices"][0]["message"]["content"]
        return final_answer


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print("=" * 65)
    print("FUNCTION CALLING THUẦN VỚI GROQ (qwen/qwen3.8-27b)")
    print("Học viên: Trần Trọng Chinh (2A202602720)")
    print("=" * 65)
    print(f"\nUser: {question}\n")
    answer = run_groq_function_calling(question)
    print(f"\n💡 Câu trả lời từ Groq:\n{answer}")
