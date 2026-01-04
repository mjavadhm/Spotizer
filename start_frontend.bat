@echo off
echo Starting Spotizer Frontend...
echo.

cd /d "%~dp0frontend"

echo Starting HTTP server on http://localhost:8080
echo.
echo Frontend will be available at: http://localhost:8080
echo Press Ctrl+C to stop the server
echo.

python -m http.server 8080

pause
