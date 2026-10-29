@echo off
rem 统一控制台编码为 UTF-8，保证日志中文不乱码
chcp 65001 >nul
rem 固定 Python 标准输出编码为 UTF-8，避免日志乱码
set "PYTHONIOENCODING=utf-8"
cd /d D:\mydigit_sign
echo ============================================ >> sign_log.txt
echo [%date% %time%] 开始运行 >> sign_log.txt
"C:\Program Files\Python\Python312\python.exe" -u mydigit_sign.py >> sign_log.txt 2>&1
echo [%date% %time%] 运行结束 >> sign_log.txt
