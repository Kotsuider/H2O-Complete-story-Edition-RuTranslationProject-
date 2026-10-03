@echo off
chcp 65001 >nul
echo [1/3] Processing translation table...
python ru_f_translate.py h2o_full_ruf.xlsx -o h2o_ruf.xlsx
if errorlevel 1 (
    echo Error during translation processing!
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Patching Ethornell scripts...
python ethornell_tool.py insertlocal h2o_der h2o_ruf.xlsx h2o_OUT sjis_ext.bin --wrapper monospace --line-width 48
if errorlevel 1 (
    echo Error during script patching!
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Patching choices...
if exist choices.md (
    python choices_tool.py insert h2o_OUT h2o_OUT choices.md
    if errorlevel 1 (
        echo Error during choices patching!
        pause
        exit /b %errorlevel%
    )
) else (
    echo [Notice] choices.md not found, skipping choices patching.
)

echo.
echo Done! All scripts successfully patched.
pause
