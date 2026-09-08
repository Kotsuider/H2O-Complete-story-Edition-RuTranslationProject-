@echo off
chcp 65001 >nul
echo [1/2] Processing translation table...
python ru_f_translate.py h2o_full_ruf.xlsx -o h2o_ruf.xlsx
if errorlevel 1 (
    echo Error during translation processing!
    pause
    exit /b %errorlevel%
)

echo.
echo [2/2] Patching Ethornell scripts...
python ethornell_tool.py insertlocal h2o_der h2o_ruf.xlsx h2o_OUT sjis_ext.bin --wrapper monospace --line-width 48
if errorlevel 1 (
    echo Error during script patching!
    pause
    exit /b %errorlevel%
)

echo.
echo Done! All scripts successfully patched.
pause
