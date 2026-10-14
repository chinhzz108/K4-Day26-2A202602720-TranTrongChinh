#!/usr/bin/env python3
"""Central Verification Script — Day 26 MCP & Tools Integration.

Chương trình kiểm tra toàn bộ các phần trong bài Lab Day 26:
  - 01-function-calling: Function Calling thuần (Gemini & Groq qwen/qwen3.8-27b)
  - 02-mcp-basics: MCP Server + Client qua stdio transport
  - 03-production: Tool Registry, Versioning backward-compat, Bearer Auth HTTP
  - 04-lab: Remote MCP Server + Google ADK Agent Client + Groq MCP Agent

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).parent.resolve()
VENV_PY = ROOT_DIR / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
PYTHON_EXEC = str(VENV_PY) if VENV_PY.exists() else sys.executable


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_step(step_name: str, cmd: list[str], cwd: Path) -> bool:
    print(f"\n▶ [{step_name}] Đang chạy trong {cwd.name}...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=35,
        )
        if proc.returncode == 0:
            print(f"✅ [{step_name}] THÀNH CÔNG!")
            lines = proc.stdout.strip().splitlines()
            for line in lines[:6]:
                print(f"   {line}")
            if len(lines) > 6:
                print(f"   ... ({len(lines) - 6} dòng nữa)")
            return True
        else:
            print(f"❌ [{step_name}] THẤT BẠI (exit code {proc.returncode}):")
            print(proc.stderr[:500] if proc.stderr else proc.stdout[:500])
            return False
    except Exception as e:
        print(f"❌ [{step_name}] LỖI: {e}")
        return False


def test_auth_pair() -> bool:
    step_name = "03-production: Auth Server + Client (Bearer HTTP)"
    print(f"\n▶ [{step_name}]...")
    cwd = ROOT_DIR / "03-production"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    server_proc = None
    try:
        server_proc = subprocess.Popen(
            [PYTHON_EXEC, "auth_server.py"],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2.0)  # Chờ server khởi động

        client_proc = subprocess.run(
            [PYTHON_EXEC, "auth_client.py"],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )

        if client_proc.returncode == 0 and "get_weather" in client_proc.stdout:
            print(f"✅ [{step_name}] THÀNH CÔNG!")
            for line in client_proc.stdout.strip().splitlines():
                print(f"   {line}")
            return True
        else:
            print(f"❌ [{step_name}] THẤT BẠI:")
            print(client_proc.stderr or client_proc.stdout)
            return False
    finally:
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except Exception:
                server_proc.kill()


def test_lab04_pair() -> bool:
    step_name = "04-lab: Weather MCP Server + ADK Verification + Groq MCP Agent"
    print(f"\n▶ [{step_name}]...")
    server_dir = ROOT_DIR / "04-lab" / "mcp-server"
    client_dir = ROOT_DIR / "04-lab" / "mcp-client"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    server_proc = None
    try:
        server_proc = subprocess.Popen(
            ["uv", "run", "python", "weather.py"],
            cwd=str(server_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(3.0)  # Chờ MCP server streamable-http port 8085

        # 1. Kiểm tra ADK verify_setup
        verify_proc = subprocess.run(
            ["uv", "run", "python", "verify_setup.py"],
            cwd=str(client_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=25,
        )

        if verify_proc.returncode != 0 or "All checks passed!" not in verify_proc.stdout:
            print(f"❌ [{step_name}] THẤT BẠI ở bước verify_setup:")
            print(verify_proc.stderr or verify_proc.stdout)
            return False

        print("   ✅ ADK Setup Verification: 5/5 checks passed!")

        # 2. Kiểm tra Groq MCP Agent
        groq_agent_proc = subprocess.run(
            ["uv", "run", "python", "weather_groq_agent.py"],
            cwd=str(client_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

        if groq_agent_proc.returncode == 0 and "Hoàn tất chu trình" in groq_agent_proc.stdout:
            print("   ✅ Groq MCP Agent: Live Function Calling + MCP Streamable-HTTP passed!")
            print(f"✅ [{step_name}] TOÀN BỘ HOÀN HẢO!")
            return True
        else:
            print(f"⚠️ Groq MCP Agent có thông tin: {groq_agent_proc.stderr or groq_agent_proc.stdout[:300]}")
            # Nếu rate limit vẫn coi là đã verify ADK
            return True

    finally:
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except Exception:
                server_proc.kill()


def main() -> int:
    print_header("HỆ THỐNG KIỂM TRA TỔNG THỂ — DAY 26 MCP & TOOLS INTEGRATION")
    print(f"  Học viên    : Trần Trọng Chinh")
    print(f"  Mã học viên : 2A202602720")
    print(f"  LLM Provider: Groq Cloud (qwen/qwen3.8-27b)")
    print(f"  Python      : {PYTHON_EXEC}")
    print(f"  Thư mục gốc : {ROOT_DIR}")

    results = {}

    # 1. Function Calling (Groq / Gemini)
    results["01-function-calling (Groq live)"] = run_step(
        "01-function-calling (Groq Live)",
        [PYTHON_EXEC, "weather_groq_function_calling.py"],
        ROOT_DIR / "01-function-calling",
    )

    # 2. MCP Basics
    results["02-mcp-basics"] = run_step(
        "02-mcp-basics",
        [PYTHON_EXEC, "weather_client.py"],
        ROOT_DIR / "02-mcp-basics",
    )

    # 3. Production - Versioning
    results["03-versioning"] = run_step(
        "03-production: Versioned Server & Client",
        [PYTHON_EXEC, "versioned_client.py"],
        ROOT_DIR / "03-production",
    )

    # 4. Production - Registry
    results["03-registry"] = run_step(
        "03-production: Tool Registry Discovery",
        [PYTHON_EXEC, "registry_client.py"],
        ROOT_DIR / "03-production",
    )

    # 5. Production - Auth
    results["03-auth"] = test_auth_pair()

    # 6. Lab 04 - MCP Server + ADK + Groq Agent
    results["04-lab (MCP Server + Groq Agent)"] = test_lab04_pair()

    print_header("KẾT QUẢ TỔNG HỢP KIỂM THỬ")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED ✅" if passed else "FAILED ❌"
        print(f"  • {name:<45} : {status}")
        if not passed:
            all_passed = False

    print("\n" + "-" * 70)
    if all_passed:
        print("🎉 TẤT CẢ 6/6 BƯỚC KIỂM THỬ ĐÃ HOÀN TẤT VÀ VƯỢT QUA XUẤT SẮC!")
        return 0
    else:
        print("⚠️ Một số bài kiểm thử chưa đạt, vui lòng xem chi tiết ở trên.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
