"""Weather Agent - Connects to Remote MCP Server (Local or Cloud Run).

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720
"""

import logging
import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mặc định: server chạy local. Deploy lên Cloud Run thì đặt MCP_SERVER_URL trong .env
# (ví dụ: https://<service>.run.app/mcp). verify_setup.py đọc cùng biến này.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

logger.info("🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

AGENT_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thông minh, chính xác và thân thiện. "
    "Sử dụng các công cụ thời tiết được kết nối qua giao thức MCP để tra cứu thời tiết hiện tại và dự báo. "
    "Luôn đưa ra câu trả lời rõ ràng, có cấu trúc, kèm lời khuyên hữu ích và emoji thời tiết phù hợp (🌧️, 🌤️, ☀️, ❄️, 🌡️)."
)

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )

    # Create the MCP toolset - this will connect to the remote server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")

    # Create the agent with remote MCP tools
    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        description="Trợ lý thời tiết kết nối MCP server để tra cứu thời tiết và dự báo thời tiết toàn cầu.",
        instruction=AGENT_INSTRUCTION,
        tools=[weather_tools],
    )
    logger.info("✅ Weather agent initialized with remote MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("🎉 Remote MCP connection successful!")

except Exception as e:
    logger.error(f"❌ Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()

    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model="gemini-2.5-flash",
        description="Trợ lý thời tiết (chế độ dự phòng khi chưa kết nối MCP).",
        instruction=AGENT_INSTRUCTION,
    )
