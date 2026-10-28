@echo off
setlocal
rem Gi* + peta QGIS memakai Python bawaan QGIS di Windows (padanan run_hotspot_macos.sh).
rem Jalankan dari mana saja:
rem   src\spatial\run_hotspot_windows.bat --install   pasang esda/libpysal ke .venv\hotspot (sekali saja)
rem   src\spatial\run_hotspot_windows.bat             analisis + ekspor ke reports\gis\outputs
rem   src\spatial\run_hotspot_windows.bat --verify    cek ulang output
rem Kalau QGIS tidak di "C:\Program Files\QGIS 3.x", set dulu:  set "QGIS_ROOT=D:\Apps\QGIS 3.44"
rem Peta untuk paper TIDAK butuh QGIS: python src\spatial\peta_hotspot.py

set "ROOT=%~dp0..\.."
if not defined QGIS_ROOT for /d %%D in ("C:\Program Files\QGIS 3*") do set "QGIS_ROOT=%%~fD"
if not defined QGIS_ROOT if exist "C:\OSGeo4W\bin" set "QGIS_ROOT=C:\OSGeo4W"
set "PYQGIS=%QGIS_ROOT%\bin\python-qgis.bat"
if not exist "%PYQGIS%" set "PYQGIS=%QGIS_ROOT%\bin\python-qgis-ltr.bat"
if not exist "%PYQGIS%" (
  echo Python QGIS tidak ditemukan di "%QGIS_ROOT%". Set QGIS_ROOT ke folder instalasi QGIS.
  exit /b 1
)
set "NUMBA_CACHE_DIR=%ROOT%\.venv\numba-cache"

if /i "%~1"=="--install" (
  call "%PYQGIS%" -m pip install --target "%ROOT%\.venv\hotspot" --no-deps -r "%ROOT%\src\spatial\requirements-hotspot.txt"
  exit /b %errorlevel%
)
set "SCRIPT=%ROOT%\src\spatial\kecamatan_hotspot_analysis.py"
if /i "%~1"=="--verify" set "SCRIPT=%ROOT%\src\spatial\verify_hotspot_outputs.py"
call "%PYQGIS%" "%SCRIPT%"
exit /b %errorlevel%
