@echo off
cd /d "%~dp0"
if not exist "..\.venv\Scripts\python.exe" (
  echo Khong tim thay moi truong Python cua repo. Xem frontend\README.md.
  pause
  exit /b 1
)
echo Wireframe D1 dung du lieu gia lap. Mo http://localhost:8502.
"..\.venv\Scripts\python.exe" -m streamlit run wireframe_d1.py --server.address localhost --server.port 8502 --browser.gatherUsageStats false
pause
