@echo off
rem i2v-gateway 启动脚本（本机 127.0.0.1:8300）
rem NO_PROXY：规避 Windows 系统代理拦截 localhost 回环流量（见 doc/v1/03-验证记录.md Task 11 异常节）
set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost
cd /d "%~dp0"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8300
