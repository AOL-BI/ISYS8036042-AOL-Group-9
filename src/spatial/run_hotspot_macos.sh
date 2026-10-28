#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"  # src/spatial -> repo root
QGIS_APP="${QGIS_APP:-/Applications/QGIS.app}"
export PYTHONHOME="$QGIS_APP/Contents/Frameworks"
export PYTHONPATH="$QGIS_APP/Contents/Resources/qgis/python:$ROOT/.venv/hotspot${PYTHONPATH:+:$PYTHONPATH}"
export PROJ_DATA="$QGIS_APP/Contents/Resources/qgis/proj"
export GDAL_DATA="$QGIS_APP/Contents/Resources/qgis/gdal"
export QT_QPA_PLATFORM=offscreen
export NUMBA_CACHE_DIR="$ROOT/.venv/numba-cache"
if [[ "${1:-}" == "--verify" ]]; then
  SCRIPT="$ROOT/src/spatial/verify_hotspot_outputs.py"
else
  SCRIPT="$ROOT/src/spatial/kecamatan_hotspot_analysis.py"
fi
exec "$QGIS_APP/Contents/MacOS/python3.12" "$SCRIPT"
