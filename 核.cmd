@echo off
chcp 65001 >nul
setlocal
set "HERE=%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%HERE%核.py" %*
    goto :END
)
python "%HERE%核.py" %*
:END
endlocal
