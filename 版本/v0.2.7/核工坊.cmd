@echo off
chcp 65001 >nul
setlocal
set "HERE=%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%HERE%核.py" 工坊 %*
    goto :END
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%HERE%核.py" 工坊 %*
    goto :END
)
py -3 "%HERE%核.py" 工坊 %*
:END
endlocal
