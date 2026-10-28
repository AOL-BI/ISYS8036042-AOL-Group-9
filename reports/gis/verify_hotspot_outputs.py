"""Check actual saved GIS outputs and rerun statistics to verify reproducibility."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.venv/hotspot'))
import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal import io as weights_io
from qgis.core import QgsApplication, QgsProject, QgsLayoutItemScaleBar, QgsUnitTypes, QgsLayoutItemMap
from qgis.PyQt.QtGui import QImage

OUT = ROOT / 'reports/gis/outputs'
app = QgsApplication([], False)
app.initQgis()
report = json.loads((OUT / 'validation_and_analysis.json').read_text())
assert report['permutations'] == 9999 and report['alpha'] == .05
for filename, digest in report['source_sha256'].items():
    assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest

g = gpd.read_file(OUT / 'kecamatan_hotspot_results.gpkg')
t = pd.read_csv(OUT / 'kecamatan_hotspot_statistics.csv')
assert len(g) == len(t) == 42 and g.is_valid.all() and g.crs.to_epsg() == 32748
assert t.priority_label.value_counts().to_dict() == {'Sedang':14, 'Rendah':14, 'Tinggi':14}
assert set(t.priority_order) == set(range(1,43))
ordered = t.sort_values('priority_order')
scores = list(ordered[['per100rb_tinggi','per100rb_sedang','per100rb_rendah']].itertuples(index=False,name=None))
assert scores == sorted(scores, reverse=True)
assert ordered.priority_label.tolist() == ['Tinggi']*14 + ['Sedang']*14 + ['Rendah']*14
source = pd.read_csv(ROOT/'reports/tables/ranking_kecamatan.csv').set_index('pcode_kecamatan').sort_index()
result = t.set_index('pcode').sort_index()
assert np.allclose(source.ranking,result.ranking,equal_nan=True)
assert np.array_equal(source.data_cukup,result.data_cukup.astype(bool))
labels = pd.read_csv(OUT/'kecamatan_priority_labels.csv')
assert labels.pcode.tolist() == ordered.pcode.tolist()

project = QgsProject.instance()
assert project.read(str(OUT/'kecamatan_hotspot_project.qgz'))
assert len(project.mapLayers()) == 4 and len(project.layoutManager().layouts()) == 4
visible = []
for node in project.layerTreeRoot().findLayers():
    layer = node.layer()
    assert layer.isValid() and layer.featureCount() == 42
    if node.isVisible(): visible.append(layer.name())
    if layer.name() == 'Prioritas perbaikan':
        assert layer.renderer().classAttribute() == 'priority_label'
        assert {c.value() for c in layer.renderer().categories()} == {'Rendah','Sedang','Tinggi'}
        assert layer.labeling().settings().fieldName == 'priority_label'
assert visible == ['Prioritas perbaikan']
for layout in project.layoutManager().layouts():
    bars = [x for x in layout.items() if isinstance(x,QgsLayoutItemScaleBar)]
    assert len(bars)==1 and bars[0].units()==QgsUnitTypes.DistanceKilometers
    maps = [x for x in layout.items() if isinstance(x,QgsLayoutItemMap)]
    assert len(maps)==1 and maps[0].keepLayerSet() and len(maps[0].layers())==1
for name in ['kecamatan_priority_map.png','kecamatan_gistar_hotspot_map.png','kecamatan_gistar_tinggi_map.png','kecamatan_gistar_count_map.png']:
    img = QImage(str(OUT/name))
    assert not img.isNull() and img.width()==2572 and img.height()==1818
for prefix, filename in [('rate','hasil_gistar_kejadian.geojson'),('high','hasil_gistar_tinggi.geojson')]:
    geo = gpd.read_file(OUT/filename)
    assert len(geo)==42 and geo.is_valid.all() and geo.crs.to_epsg()==4326
    assert np.allclose(geo[f'{prefix}_z'],t[f'{prefix}_z'])
gal = weights_io.open(str(OUT/'kecamatan_queen_order1.gal'))
w = gal.read(); gal.close()
assert w.n == 42 and not w.islands and w.n_components == 1
assert {k:sorted(v) for k,v in w.neighbors.items()} == {k:sorted(v) for k,v in report['selected_neighbors'].items()}

spec = importlib.util.spec_from_file_location('hotspot',OUT/'kecamatan_hotspot_analysis.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
assert np.allclose(mod.bh([.01,.04,.03,.002]), [.02,.04,.04,.008])
g2,r2 = mod.validate(); mod.assign_priority(g2,r2); mod.statistics(g2,r2)
assert np.array_equal(g2.priority_label,t.priority_label)
for _,prefix in mod.VARIABLES:
    for suffix in ['z','z_perm','p_perm_2s','q_bh']:
        assert np.allclose(g2[f'{prefix}_{suffix}'],t[f'{prefix}_{suffix}'])
    assert t[f'{prefix}_p_perm_2s'].between(0,1).all()
    assert np.array_equal(t[f'{prefix}_significant'],(t[f'{prefix}_q_bh']<=.05).astype(int))
    assert np.array_equal(t[f'{prefix}_class'],mod.classify(t[f'{prefix}_q_bh'],t[f'{prefix}_z_perm']))
print('PASS: 42 areas, 14/14/14 labels, original ranks, four valid layers/layouts, priority-only default, PNG/GeoJSON/GAL outputs, unchanged sources, and deterministic 9999-permutation statistics.')
