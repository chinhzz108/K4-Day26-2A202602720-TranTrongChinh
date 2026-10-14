# BÁO CÁO NỘP BÀI LAB — DAY 26: MODEL CONTEXT PROTOCOL (MCP) & TOOLS INTEGRATION

**Họ và tên:** Trần Trọng Chinh  
**Mã học viên:** `2A202602720`  
**Khóa học:** VinUni AI20k — Level 3: Advanced Agentic Systems  
**LLM Engine:** Groq Cloud (`qwen/qwen3.8-27b`) & Google Gemini  
**Ngày hoàn thành:** 14/10/2026  
**Kết quả kiểm thử:** 6/6 bài kiểm thử PASSED (`python verify_all.py`)

---

## 1. Tổng quan bài Lab và Cấu trúc dự án

Dự án gồm 4 phần thể hiện lộ trình từ **Function Calling truyền thống** đến **Model Context Protocol (MCP)** và triển khai production, hỗ trợ **Groq Cloud** và **Google Gemini**:

```
day26-mcp/
├── README.md                          # Hướng dẫn tổng thể + Thông tin học viên
├── SUBMISSION.md                      # Báo cáo chi tiết bài làm & kiểm thử
├── verify_all.py                      # Script tự động chạy kiểm thử toàn diện 6/6 test
├── requirements.txt                   # Danh mục thư viện Python (mcp>=2.0, google-genai, ...)
├── .env                               # Cấu hình Groq API key và endpoint
│
├── 01-function-calling/               # Bước 1: Function Calling thuần
│   ├── README.md
│   ├── weather_function_calling.py         # Gemini SDK + Groq auto-detect
│   └── weather_groq_function_calling.py    # Function Calling trực tiếp với Groq (qwen/qwen3.8-27b)
│
├── 02-mcp-basics/                     # Bước 2: MCP server + client độc lập qua stdio
│   ├── README.md
│   ├── weather_server.py              # MCPServer tự công bố tool qua @mcp.tool()
│   └── weather_client.py              # Client khám phá tool (list_tools) & gọi (call_tool)
│
├── 03-production/                     # Bước 3: Sản xuất (Auth, Registry, Versioning)
│   ├── README.md
│   ├── auth_server.py                 # Streamable HTTP + StaticTokenVerifier (Bearer token)
│   ├── auth_client.py                 # Client gửi Bearer token qua header HTTP
│   ├── registry.json                  # Tool Registry tập trung dạng tool-centric
│   ├── registry_client.py             # Agent tìm tool theo tag, so sánh semantic version
│   ├── versioned_server.py            # Backward compatibility (v1 + v2 + resource metadata)
│   └── versioned_client.py            # Client tương thích ngược & đọc server://info
│
└── 04-lab/                            # Bước 4: Weather Agent với Remote MCP Server
    ├── README.md
    ├── mcp-server/                    # FastMCP Server (Streamable HTTP port 8085)
    │   ├── weather.py                 # Tool get_current_weather, get_forecast, health_check
    │   ├── Dockerfile                 # Container image phục vụ deploy Cloud Run
    │   ├── pyproject.toml             # Quản lý môi trường uv
    │   └── .env.example
    └── mcp-client/                    # Weather Agent Client
        ├── weather_agent/
        │   ├── agent.py               # Google ADK Agent dùng McpToolset
        │   └── __init__.py
        ├── weather_groq_agent.py      # Groq MCP Agent (qwen/qwen3.8-27b + FastMCP Server)
        ├── verify_setup.py            # Script xác thực 5 thành phần của Agent
        ├── pyproject.toml
        ├── .env.example
        └── .env
```

---

## 2. Tích hợp Groq Cloud (`qwen/qwen3.8-27b`)

Dự án đã được cấu hình và kiểm thử trực tiếp với **Groq API**:
1. **Function Calling với Groq (`01-function-calling/weather_groq_function_calling.py`)**:
   - Định nghĩa schema tool theo format OpenAI / Groq.
   - Gửi prompt: `"Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"`.
   - Mô hình `qwen/qwen3.8-27b` tự động sinh 2 tool calls `get_weather(city='Hà Nội')` và `get_weather(city='Đà Nẵng')`.
   - App thực thi hàm Python thật và trả kết quả để Groq tổng hợp câu trả lời tự nhiên bằng tiếng Việt kèm emoji và lời khuyên thời tiết thực tế.

2. **Groq MCP Agent Client (`04-lab/mcp-client/weather_groq_agent.py`)**:
   - Kết nối tới Remote FastMCP Server qua Streamable HTTP (`http://localhost:8085/mcp`).
   - Tự động gọi `session.list_tools()` để khám phá công cụ runtime (`get_current_weather`, `get_forecast`, `health_check`).
   - Chuyển đổi linh hoạt schema từ MCP sang Groq/OpenAI Function Calling format.
   - Tích hợp cơ chế tự động chờ hồi phục Rate Limit (HTTP 429 TPM) với exponential backoff.
   - Thực thi trọn vẹn chu trình: **User Question $\rightarrow$ Groq Tool Calling $\rightarrow$ Remote MCP Server execution $\rightarrow$ Groq Synthesis Response**.

---

## 3. Các vấn đề kỹ thuật đã phát hiện và hoàn thiện (Bugfixes & Enhancements)

1. **Khắc phục lỗi Unicode/Encoding trên Windows**:
   - `03-production/registry_client.py`: Khi đọc `registry.json`, lệnh `open(path)` thiếu `encoding="utf-8"` gây lỗi `UnicodeDecodeError: 'charmap'` do Windows mặc định dùng CP1252. Đã sửa thành `open(path, encoding="utf-8")`.
   - Bổ sung tự động reconfigure `sys.stdout` và `sys.stderr` sang `utf-8` trên nền tảng Windows (`win32`) trên toàn bộ codebase, tránh lỗi `UnicodeEncodeError`.

2. **Cơ chế Fallback thông minh cho Remote MCP Server (`04-lab/mcp-server/weather.py`)**:
   - Sửa lỗi kiểm tra `is_standalone = sys.stdin.isatty()`: Khắc phục tình trạng server bị rơi vào chế độ `stdio` khi chạy ngầm trên Windows. Server hiện mặc định chạy `Streamable HTTP` trên port 8085 đúng chuẩn Lab 04.
   - Tích hợp bộ dữ liệu Mock Offline cho các thành phố lớn (Hà Nội, Đà Nẵng, Hải Phòng, Sydney, Brisbane, Melbourne, ...): Khi chưa có `WEATHERAPI_KEY` (hoặc mạng chập chờn), server tự động phục vụ dữ liệu demo hoàn chỉnh. Khi có key, server kết nối trực tiếp WeatherAPI live.

3. **Cải tiến Google ADK Agent (`04-lab/mcp-client/weather_agent/agent.py`)**:
   - Thêm `instruction` và `description` chi tiết cho `root_agent` giúp sinh câu trả lời tiếng Việt mạch lạc, sinh động.
   - Cấu hình file [`.env.example`](04-lab/mcp-client/.env.example) và [`.env`](04-lab/mcp-client/.env) giúp script `verify_setup.py` đạt 100% PASS trên cả 5 hạng mục.

4. **Script kiểm thử tự động toàn diện (`verify_all.py`)**:
   - Kiểm tra tích hợp end-to-end 6/6 kịch bản trên toàn bộ repository chỉ với 1 lệnh duy nhất.

---

## 4. Bảng so sánh cốt lõi: Function Calling vs Model Context Protocol (MCP)

| Tiêu chí | Function Calling (Bước 1) | Model Context Protocol - MCP (Bước 2, 3, 4) |
|---|---|---|
| **Bản chất** | Khả năng của mô hình LLM (Model Capability) | Giao thức truyền thông Client-Server mở (Protocol) |
| **Khai báo Schema** | Lập trình viên phải viết tay schema JSON/Type cho từng app | Server tự sinh schema từ `@mcp.tool()` qua type hints & docstring |
| **Nơi thực thi Tool** | Ngay trong runtime của ứng dụng gọi LLM | Chạy độc lập trên MCP Server (stdio hoặc Streamable HTTP) |
| **Khám phá Tool** | Bị hard-code cố định trong danh sách tools gửi lên model | Động tại runtime: Client hỏi server `list_tools()` hoặc tra Tool Registry |
| **Khả năng tái sử dụng** | Kém: Muốn dùng cho app khác phải copy mã nguồn schema & hàm | Rất cao: Viết 1 lần, mọi MCP Client (ADK, Groq Agent, Claude Code, Cursor) đều cắm vào được |
| **Bảo mật & Quản trị** | Khó quản lý tập trung quyền hạn | Hỗ trợ Bearer Token, OAuth, Scopes và Tool Versioning chuyên biệt |

---

## 5. Hướng dẫn chạy kiểm thử

### Cách 1: Chạy toàn bộ kiểm thử bằng 1 lệnh duy nhất
```powershell
python verify_all.py
```

### Cách 2: Chạy trực tiếp Function Calling với Groq
```powershell
cd 01-function-calling
python weather_groq_function_calling.py
```

### Cách 3: Chạy Groq MCP Agent kết nối Remote MCP Server (Lab 04)
```powershell
# Terminal 1: Khởi động MCP Server (cổng 8085)
cd 04-lab/mcp-server
uv run python weather.py

# Terminal 2: Chạy Groq MCP Agent
cd 04-lab/mcp-client
uv run python weather_groq_agent.py "Thời tiết và dự báo ngày mai ở Hà Nội?"
```

### Cách 4: Chạy Google ADK Web Interface
```powershell
cd 04-lab/mcp-client
uv run python verify_setup.py
uv run adk web
# Mở trình duyệt tại http://localhost:8000
```
