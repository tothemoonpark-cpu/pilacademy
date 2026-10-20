@echo off
rem 작업 스케줄러에 매일 09:30 감시 작업을 등록합니다. (이미 있으면 덮어씀)
chcp 65001 >nul
set "DIR=%~dp0"
schtasks /Create /F /SC DAILY /ST 09:30 /TN "notice_watch" /TR "cmd /c cd /d \"%DIR%\" && python notice_watch.py"
if errorlevel 1 (echo 등록 실패: 관리자 권한/파이썬 경로를 확인하세요.) else (echo 등록 완료: 매일 09:30)
pause
