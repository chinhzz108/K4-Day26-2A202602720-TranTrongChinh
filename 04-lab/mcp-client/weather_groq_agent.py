"""Weather Agent powered by Groq LLM (qwen/qwen3.8-27b) & Remote MCP Server.

Agent này đóng vai trò MCP Client:
1. Kết nối tới Remote FastMCP Server qua Streamable HTTP (http://localhost:8085/mcp).
2. Tự động khám phá danh sách tools từ MCP Server bằng session.list_tools().
3. Chuyển đổi schema MCP tools sang chuẩn OpenAI / Groq tool schema.
4. Gửi câu hỏi và tools cho Groq (qwen/qwen3.8-27b).
5. Khi Groq yêu cầu gọi tool, agent gửi lệnh session.call_tool() tới MCP Server.
6. Gửi kết quả thực thi về Groq để tổng hợp câu trả lời cuối cùng bằng tiếng Việt.

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720

Cách chạy:
    uv run python weather_groq_agent.py
    hoặc: uv run python weather_groq_agent.py "Thời tiết Hà Nội và Đà Nẵng?"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1") + "/chat/completions"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

SYSTEM_PROMPT = (
    "Bạn là trợ lý thời tiết AI thông minh, nhiệt tình và chính xác. "
    "Bạn sử dụng các công cụ thời tiết được cung cấp qua giao thức MCP (Model Context Protocol). "
    "Hãy luôn trả lời chi tiết, có cấu trúc rõ ràng bằng tiếng Việt tự nhiên, "
    "kèm theo các biểu tượng cảm xúc (emoji) phù hợp và lời khuyên hữu ích cho người hỏi."
)

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client


def convert_mcp_tool_to_groq(mcp_tool) -> dict:
    """Chuyển đổi tool schema từ MCP sang chuẩn Groq/OpenAI Function Calling."""
    schema = mcp_tool.inputSchema if hasattr(mcp_tool, "inputSchema") else {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": schema,
        },
    }


async def _post_with_retry(http: httpx.AsyncClient, url: str, headers: dict, payload: dict, max_retries: int = 5) -> dict:
    """Gửi request tới Groq kèm retry tự động khi gặp Rate Limit (429 TPM)."""
    payload.setdefault("max_tokens", 600)
    for attempt in range(max_retries):
        resp = await http.post(url, headers=headers, json=payload)
        if resp.status_code == 429:
            # Parse reset time from Groq headers
            reset_header = resp.headers.get("x-ratelimit-reset-tokens") or resp.headers.get("retry-after")
            wait_time = 4.0 * (attempt + 1)
            if reset_header:
                try:
                    clean = reset_header.rstrip("s")
                    wait_time = max(float(clean) + 0.5, 3.0)
                except Exception:
                    pass
            print(f"  ⏳ Groq Rate Limit (429). Đang chờ {wait_time:.1f}s để hồi token bucket (lần {attempt + 1}/{max_retries})...")
            await asyncio.sleep(wait_time)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()


async def ask_agent(session: ClientSession, groq_tools: list[dict], user_prompt: str) -> str:
    """Điều phối vòng lặp Function Calling giữa Groq LLM và MCP Server."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    print(f"\n👤 User: {user_prompt}")
    print(f"🤖 Đang gửi yêu cầu tới Groq ({GROQ_MODEL}) cùng {len(groq_tools)} MCP tools...")

    async with httpx.AsyncClient(timeout=45.0) as http:
        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "tools": groq_tools,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 500,
        }

        data = await _post_with_retry(http, GROQ_URL, headers, payload)
        message = data["choices"][0]["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            return message.get("content", "")

        print(f"⚙️ Groq yêu cầu thực thi {len(tool_calls)} MCP tool call(s):")
        for tc in tool_calls:
            call_id = tc["id"]
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            print(f"  👉 [Groq Request]  {fn_name}({fn_args})")

            # Gọi tool trực tiếp trên MCP Server qua giao thức MCP
            result = await session.call_tool(fn_name, fn_args)
            result_text = result.content[0].text if result.content else ""
            summary_line = result_text.strip().splitlines()[0] if result_text else "(trống)"
            print(f"  📥 [MCP Server Rep] -> {summary_line}")

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": fn_name,
                "content": result_text,
            })

        print(f"📝 Đang gửi kết quả cho Groq ({GROQ_MODEL}) để tổng hợp câu trả lời...")
        payload_final = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 600,
        }
        data_final = await _post_with_retry(http, GROQ_URL, headers, payload_final)
        final_answer = data_final["choices"][0]["message"]["content"]
        return final_answer


async def main() -> None:
    print("=" * 70)
    print("GROQ-POWERED WEATHER AGENT WITH REMOTE MCP SERVER")
    print(f"Học viên: Trần Trọng Chinh (2A202602720)")
    print(f"LLM     : Groq Cloud ({GROQ_MODEL})")
    print(f"Server  : {MCP_SERVER_URL}")
    print("=" * 70)

    print(f"\n🔌 Đang kết nối tới MCP Server tại {MCP_SERVER_URL}...")

    async with create_mcp_http_client() as http_client:
        async with streamable_http_client(MCP_SERVER_URL, http_client=http_client) as (read, write, *_):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Kết nối giao thức MCP thành công!")

                # 1. Khám phá tools tự động từ MCP server
                tools_result = await session.list_tools()
                groq_tools = [convert_mcp_tool_to_groq(t) for t in tools_result.tools]
                print(f"🛠️  Server cung cấp {len(groq_tools)} công cụ:")
                for t in tools_result.tools:
                    print(f"   • {t.name}: {t.description.splitlines()[0] if t.description else ''}")

                # 2. Xác định câu hỏi cần xử lý
                if len(sys.argv) > 1:
                    question = " ".join(sys.argv[1:])
                else:
                    question = "Thời tiết ở Sydney và Brisbane hôm nay thế nào? Có mưa không và nên mặc gì?"

                answer = await ask_agent(session, groq_tools, question)
                print(f"\n💬 Trả lời từ Groq Agent:\n{answer}\n")
                print("=" * 70)
                print("🎉 Hoàn tất chu trình: User -> Groq Function Calling -> MCP Server -> Groq Synthesis!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
    except Exception as e:
        print(f"\n❌ Lỗi thực thi: {e}")
        print("Đảm bảo MCP Server đang chạy: cd 04-lab/mcp-server && uv run python weather.py")
