"""Reproducible Jakarta Gi* analysis and PyQGIS cartography. See docs/qgis_hotspot_workflow.md."""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
# Dependencies live in the repository, never in the QGIS application bundle.
if (ROOT / '.venv/hotspot').exists():
    sys.path.insert(0, str(ROOT / '.venv/hotspot'))
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from shapely.validation import explain_validity
from scipy.stats import norm, skew
from libpysal.weights import Queen, KNN, W
from libpysal import io as weights_io
from esda import G_Local
import esda, libpysal
from qgis.core import (
    Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsFillSymbol, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsLayoutExporter, QgsCoordinateReferenceSystem,
    QgsRectangle, QgsUnitTypes, QgsLegendStyle, QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling, QgsReferencedRectangle,
)
from qgis.PyQt.QtGui import QFont

OUT = ROOT / 'reports/gis/outputs'
SEED, PERMUTATIONS, ALPHA = 20261028, 9999, .05
VARIABLES = [('per100rb_kejadian', 'rate'), ('per100rb_tinggi', 'high'), ('n_kejadian', 'count')]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bh(p):
    """Benjamini-Hochberg adjusted p-values, one family per input variable."""
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    adjusted = np.minimum.accumulate((p[order] * len(p) / np.arange(1, len(p)+1))[::-1])[::-1]
    result = np.empty(len(p)); result[order] = np.minimum(adjusted, 1)
    return result


def classify(q, z):
    return np.where(q > ALPHA, 'Not significant', np.where(z > 0,
        np.where(q <= .01, 'Hotspot (q <= 0.01)', 'Hotspot (q <= 0.05)'),
        np.where(q <= .01, 'Coldspot (q <= 0.01)', 'Coldspot (q <= 0.05)')))


def validate():
    source = ROOT / 'reports/gis/kecamatan_hotspot_input.geojson'
    table = ROOT / 'reports/tables/ranking_kecamatan.csv'
    g = gpd.read_file(source).sort_values('pcode').reset_index(drop=True)
    c = pd.read_csv(table).sort_values('pcode_kecamatan').reset_index(drop=True)
    require(len(g) == len(c) == 42, 'Expected 42 mainland kecamatan')
    require(g.pcode.is_unique and c.pcode_kecamatan.is_unique, 'Duplicate geographic IDs')
    require(g.pcode.tolist() == c.pcode_kecamatan.tolist(), 'CSV/GeoJSON IDs differ')
    require(g.pcode.str.match(r'ID317[1-5]\d{3}$').all(), 'Unexpected area/Seribu ID')
    require(g.crs.to_epsg() == 4326, 'Expected WGS84/CRS84 source')
    require(not g.geometry.is_empty.any() and not g.geometry.isna().any(), 'Empty geometry')
    compare = [x for x in c.columns if x not in ('pcode_kecamatan', 'kecamatan', 'kota')]
    for col in compare:
        require(np.allclose(g[col].astype(float), c[col].astype(float), equal_nan=True), f'Mismatch: {col}')
    require(g.kecamatan.equals(c.kecamatan), 'Kecamatan names differ for matching IDs')
    require((g.kota.str.replace('Kota ', '', regex=False) == c.kota.str.replace('Kota ', '', regex=False)).all(), 'City mismatch')
    require(not c.drop(columns='ranking').isna().any().any(), 'Unexpected missing attributes')
    for col in ['n_tweet','n_kejadian','n_tinggi','n_sedang','n_rendah']:
        require(((g[col] >= 0) & (g[col] % 1 == 0)).all(), f'Invalid counts: {col}')
    require((g.penduduk_2025_est > 0).all(), 'Invalid population')
    require((g.n_kejadian == g[['n_tinggi','n_sedang','n_rendah']].sum(axis=1)).all(), 'Incident totals inconsistent')
    require((g.n_tweet >= g.n_kejadian).all(), 'Tweets below incidents')
    for suffix in ['kejadian','tinggi','sedang','rendah']:
        require(np.allclose(g[f'per100rb_{suffix}'], (g[f'n_{suffix}']/g.penduduk_2025_est*100000).round(2), atol=.00001), 'Rate mismatch')
    require((g.data_cukup.astype(bool) == (g.n_kejadian >= 5)).all(), 'Eligibility mismatch')
    require(g.ranking.isna().equals(~g.data_cukup.astype(bool)), 'Unexpected missing ranks')
    ranked = c[c.data_cukup].sort_values('ranking')
    scores = list(ranked[['per100rb_tinggi','per100rb_sedang','per100rb_rendah']].itertuples(index=False, name=None))
    require(scores == sorted(scores, reverse=True), 'Ranking disagrees with lexicographic urgency rates')
    require(ranked.ranking.tolist() == list(range(1,len(ranked)+1)), 'Rank gaps')
    # CSV is authoritative for ranking; already enriched attributes are not joined again.
    g['ranking'] = c.ranking.to_numpy()
    reference = ROOT / 'data/external/batas-wilayah/jakarta_adm3.geojson'
    require(reference.exists(), 'Boundary reference missing')
    ref = gpd.read_file(reference).set_index('adm3_pcode')
    require(set(ref.index) == set(g.pcode), 'Boundary reference IDs differ')
    require(all(row.geometry.equals(ref.loc[row.pcode].geometry) for row in g.itertuples()), 'Boundaries differ from repository reference')
    repairs = []
    for i in g.index[~g.is_valid]:
        before = g.loc[i, 'geometry']
        repaired = shapely.make_valid(before)
        if repaired.geom_type == 'GeometryCollection':
            repaired = shapely.union_all([x for x in repaired.geoms if x.geom_type in ('Polygon','MultiPolygon')])
        require(repaired.geom_type in ('Polygon','MultiPolygon') and repaired.is_valid, 'Repair failed')
        areas = gpd.GeoSeries([before, repaired], crs=g.crs).to_crs(32748).area
        repairs.append({'pcode':g.loc[i,'pcode'], 'kecamatan':g.loc[i,'kecamatan'], 'reason':explain_validity(before), 'area_change_m2':float(areas.iloc[1]-areas.iloc[0])})
        g.loc[i,'geometry'] = repaired
    report = {'source_sha256': {str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [source,table,reference]},
        'geojson_schema':{x:str(t) for x,t in g.dtypes.items()}, 'csv_schema':{x:str(t) for x,t in c.dtypes.items()},
        'source_crs':str(g.crs), 'output_crs':'EPSG:32748', 'features':len(g), 'numeric_mismatches':0,
        'join_required':False, 'city_difference':'CSV prefixes city names with Kota; IDs and remaining names match',
        'missing_values':{x:int(v) for x,v in g.isna().sum().items()}, 'geometry_repairs':repairs,
        'boundary_reference_match':True, 'eligible_for_ranking':int(g.data_cukup.sum()),
        'analysis_scope':'All 42 kecamatan, including low/zero counts; data_cukup governs ranking only',
        'versions':{'qgis':Qgis.QGIS_VERSION,'numpy':np.__version__,'geopandas':gpd.__version__,'shapely':shapely.__version__,'esda':esda.__version__,'libpysal':libpysal.__version__}}
    return g.to_crs(32748), report


def assign_priority(g, report):
    """User-approved relative priority across all 42 areas; source ranking is preserved."""
    order = g.sort_values(
        ['per100rb_tinggi', 'per100rb_sedang', 'per100rb_rendah', 'pcode'],
        ascending=[False, False, False, True], kind='stable').index
    require(len(g) == 42, 'Priority terciles require the validated 42-area study')
    g['priority_order'] = 0
    g['priority_label'] = ''
    for start, label in [(0, 'Tinggi'), (14, 'Sedang'), (28, 'Rendah')]:
        g.loc[order[start:start+14], 'priority_label'] = label
    g.loc[order, 'priority_order'] = np.arange(1, 43)
    report['priority'] = {
        'method': 'Relative thirds of all 42 areas, sorted descending by high, medium, low urgency rates; pcode ascending breaks exact ties',
        'scope': 'Includes all 25 data_cukup=False areas by user instruction; source ranking and eligibility unchanged',
        'class_counts': g.priority_label.value_counts().to_dict(),
        'ranges': {'Tinggi': [1,14], 'Sedang': [15,28], 'Rendah': [29,42]},
        'boundary_ties': [],
    }
    fields = ['per100rb_tinggi','per100rb_sedang','per100rb_rendah']
    for cut in (14, 28):
        left, right = g.loc[order[cut-1]], g.loc[order[cut]]
        if all(left[x] == right[x] for x in fields):
            report['priority']['boundary_ties'].append([left.pcode, right.pcode])
    require(set(g.priority_label) == {'Rendah','Sedang','Tinggi'}, 'Priority classes incomplete')
    return g


def statistics(g, report):
    ids = g.pcode.tolist()
    w = Queen.from_dataframe(g, ids=ids)
    report['queen'] = {'components':int(w.n_components), 'islands':list(w.islands), 'neighbors':w.neighbors}
    # Do not silently ignore disconnected units: use symmetric 4-nearest centroid neighbors.
    if w.n_components > 1 or w.islands:
        coords = np.column_stack((g.geometry.centroid.x, g.geometry.centroid.y))
        w = KNN.from_array(coords, k=4, ids=ids).symmetrize()
        require(w.n_components == 1 and not w.islands, 'KNN fallback remains disconnected')
        report['weights_method'] = 'Symmetric KNN k=4, projected polygon centroids (Queen disconnected)'
    else:
        report['weights_method'] = 'Queen contiguity, binary weights'
    report['selected_neighbors'] = w.neighbors
    # GAL is a contiguity graph without self-links; star=True adds the focal unit.
    gal = weights_io.open(str(OUT/'kecamatan_queen_order1.gal'), 'w')
    gal.write(w); gal.close()
    report['variables'] = {}
    for variable, prefix in VARIABLES:
        y = g[variable].to_numpy(float)
        require(len(y) >= 30 and np.unique(y).size > 1 and y.sum() > 0, 'Insufficient variation')
        # Fresh weights object: G_Local sets diagonal and transformation internally.
        local = G_Local(y, W(w.neighbors, id_order=ids), star=True, transform='B',
            permutations=PERMUTATIONS, seed=SEED, n_jobs=1, keep_simulations=True, alternative='two-sided')
        p = np.asarray(local.p_sim, dtype=float)
        require(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(), 'Invalid permutation probabilities')
        q = bh(p)
        require(np.isfinite(local.Zs).all() and np.isfinite(local.z_sim).all(), 'Nonfinite Gi*')
        # Check analytic Gi* Z against the explicit focal-inclusive formula.
        matrix = w.full()[0].copy(); np.fill_diagonal(matrix,1)
        n = len(y); s = y.std(ddof=0); rowsums = matrix.sum(axis=1)
        z = (matrix@y-y.mean()*rowsums)/(s*np.sqrt((n*(matrix**2).sum(axis=1)-rowsums**2)/(n-1)))
        require(np.allclose(local.Zs,z), 'Gi* focal-inclusive formula check failed')
        g[f'{prefix}_gi_star'] = local.Gs
        g[f'{prefix}_z'] = local.Zs
        g[f'{prefix}_z_perm'] = local.z_sim
        g[f'{prefix}_p_norm_2s'] = np.minimum(2*norm.sf(np.abs(local.Zs)),1)
        g[f'{prefix}_p_perm_2s'] = p
        g[f'{prefix}_q_bh'] = q
        g[f'{prefix}_q_norm_bh'] = bh(g[f'{prefix}_p_norm_2s'])
        g[f'{prefix}_significant'] = (q <= ALPHA).astype(int)
        # Conditional permutations hold the focal value fixed: direction uses that null mean.
        g[f'{prefix}_class'] = classify(q, local.z_sim)
        g[f'{prefix}_raw_class'] = np.where(p > ALPHA,'Not significant',np.where(local.z_sim>0,'Hotspot','Coldspot'))
        report['variables'][variable] = {'summary':g[variable].describe().to_dict(), 'zero_count':int((y==0).sum()),
            'unique_values':int(np.unique(y).size), 'skewness':float(skew(y)),
            'raw_significant':int((p<=ALPHA).sum()), 'fdr_significant':int((q<=ALPHA).sum()),
            'minimum_p':float(p.min()),'minimum_q':float(q.min()),
            'raw_areas':g.loc[p<=ALPHA,['pcode','kecamatan',f'{prefix}_raw_class']].to_dict('records'),
            'fdr_areas':g.loc[q<=ALPHA,['pcode','kecamatan',f'{prefix}_class']].to_dict('records')}
    g['neighbor_count'] = [len(w.neighbors[i]) for i in ids]
    report.update(seed=SEED, permutations=PERMUTATIONS, alpha=ALPHA,
        significance='Conditional two-sided permutation p, Benjamini-Hochberg FDR per variable; direction from z_perm',
        changed_raw_classifications=int((g.rate_raw_class != g.count_raw_class).sum()),
        changed_fdr_classifications=int((g.rate_class != g.count_class).sum()),
        rate_vs_high_changed_raw=int((g.rate_raw_class != g.high_raw_class).sum()),
        rate_vs_high_changed_fdr=int((g.rate_class != g.high_class).sum()))
    pd.crosstab(g.rate_raw_class,g.count_raw_class).to_csv(OUT/'sensitivity_raw_comparison.csv')
    with (OUT/'spatial_weights.csv').open('w') as f:
        writer=csv.writer(f); writer.writerow(['pcode','neighbor_pcode','weight'])
        for i in ids:
            for j in w.neighbors[i]+[i]: writer.writerow([i,j,1])
    return g


def renderer(layer, field, categories):
    items=[]
    for value, color, label in categories:
        symbol=QgsFillSymbol.createSimple({'color':color,'outline_color':'#ffffff','outline_width':'0.22'})
        items.append(QgsRendererCategory(value,symbol,label))
    layer.setRenderer(QgsCategorizedSymbolRenderer(field,items))


def label(layout, text, x, y, width, height, size=10, bold=False):
    item=QgsLayoutItemLabel(layout); item.setText(text); item.setFont(QFont('Arial',size,QFont.Bold if bold else QFont.Normal))
    layout.addLayoutItem(item); item.attemptMove(QgsLayoutPoint(x,y)); item.attemptResize(QgsLayoutSize(width,height))
    return item


def make_layout(project, layer, name, title, subtitle, note, filename, significance_field=None):
    layout=QgsPrintLayout(project); layout.initializeDefaults(); layout.setName(name)
    # Explicit landscape A4 avoids dependence on UI defaults.
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(297,210))
    label(layout,title,10,6,280,12,17,True)
    label(layout,subtitle,10,20,280,10,10)
    map_item=QgsLayoutItemMap(layout); layout.addLayoutItem(map_item)
    map_item.attemptMove(QgsLayoutPoint(10,34)); map_item.attemptResize(QgsLayoutSize(185,152))
    map_item.setCrs(QgsCoordinateReferenceSystem('EPSG:32748')); map_item.setLayers([layer]); map_item.setKeepLayerSet(True)
    extent=QgsRectangle(layer.extent()); extent.scale(1.10); map_item.zoomToExtent(extent)
    legend=QgsLayoutItemLegend(layout); layout.addLayoutItem(legend); legend.setTitle('Map legend')
    legend.setAutoUpdateModel(False); legend.model().rootGroup().clear(); legend.model().rootGroup().addLayer(layer)
    legend.setLinkedMap(map_item); legend.setStyleFont(QgsLegendStyle.SymbolLabel,QFont('Arial',9)); legend.attemptMove(QgsLayoutPoint(201,38))
    label(layout,'N\n↑',179,36,14,22,19,True)
    bar=QgsLayoutItemScaleBar(layout); layout.addLayoutItem(bar); bar.setStyle('Single Box'); bar.setLinkedMap(map_item)
    bar.applyDefaultSize(); bar.setUnits(QgsUnitTypes.DistanceKilometers); bar.setUnitsPerSegment(2); bar.setNumberOfSegments(3); bar.setNumberOfSegmentsLeft(0)
    bar.setUnitLabel('km'); bar.setFont(QFont('Arial',9)); bar.setUnitsPerSegment(2)
    bar.attemptMove(QgsLayoutPoint(15,174))
    if significance_field:
        significant = sum(int(f[significance_field]) for f in layer.getFeatures())
        result_note = ('No significant clusters' if significant == 0 else f'{significant} significant areas') + '\nafter FDR correction'
        label(layout,result_note,201,91,87,16,11,True)
    label(layout,note,201,112,87,70,9)
    label(layout,'Sources: project complaint aggregates; BPS / OCHA HDX boundaries (2020); estimated population 2025.\nMainland DKI Jakarta · 42 kecamatan · WGS 84 / UTM zone 48S (EPSG:32748)',10,191,280,13,8)
    project.layoutManager().addLayout(layout)
    settings=QgsLayoutExporter.ImageExportSettings(); settings.dpi=220
    result=QgsLayoutExporter(layout).exportToImage(str(OUT/filename),settings)
    require(result == QgsLayoutExporter.Success, f'Map export failed: {filename}')
    return map_item


def cartography(report):
    project=QgsProject.instance(); project.clear(); project.setCrs(QgsCoordinateReferenceSystem('EPSG:32748'))
    gpkg=OUT/'kecamatan_hotspot_results.gpkg'
    priority=QgsVectorLayer(str(gpkg)+'|layername=kecamatan_hotspot','Prioritas perbaikan','ogr')
    require(priority.isValid(),'Cannot read results GeoPackage')
    renderer(priority, 'priority_label', [
        ('Rendah','#fee0d2','Rendah'),
        ('Sedang','#fc9272','Sedang'),
        ('Tinggi','#b30000','Tinggi'),
    ])
    project.addMapLayer(priority)
    pal=QgsPalLayerSettings(); pal.fieldName='priority_label'
    fmt=QgsTextFormat(); fmt.setFont(QFont('Arial',7)); fmt.setSize(7); pal.setFormat(fmt)
    priority.setLabeling(QgsVectorLayerSimpleLabeling(pal)); priority.setLabelsEnabled(True)
    make_layout(project,priority,'Prioritas perbaikan','Prioritas Perbaikan Infrastruktur — DKI Jakarta',
        '42 kecamatan · tiga kelompok prioritas relatif: Rendah, Sedang, Tinggi',
        'Urutan laju per 100.000 jiwa:\nurgensi tinggi, lalu sedang,\nlalu rendah.\n\nTinggi: urutan 1–14\nSedang: urutan 15–28\nRendah: urutan 29–42\n\nSemua wilayah diberi kelas,\ntermasuk yang datanya terbatas.\nIni bukan kelas signifikansi Gi*.',
        'kecamatan_priority_map.png')
    colors=[('Hotspot (q <= 0.01)','#99000d','Hotspot · q ≤ 0.01'),('Hotspot (q <= 0.05)','#ef3b2c','Hotspot · 0.01 < q ≤ 0.05'),('Not significant','#e5e7eb','Not significant · q > 0.05'),('Coldspot (q <= 0.05)','#4292c6','Coldspot · 0.01 < q ≤ 0.05'),('Coldspot (q <= 0.01)','#084594','Coldspot · q ≤ 0.01')]
    maps = [
        ('count','Incident count sensitivity','Absolute incident counts · supplementary sensitivity','kecamatan_gistar_count_map.png'),
        ('high','Gi* laju urgensi tinggi','High-urgency incidents per 100,000 residents','kecamatan_gistar_tinggi_map.png'),
        ('rate','Gi* laju kejadian','All incidents per 100,000 residents','kecamatan_gistar_hotspot_map.png'),
    ]
    for prefix, name, subtitle, filename in maps:
        layer=QgsVectorLayer(str(gpkg)+'|layername=kecamatan_hotspot',name,'ogr')
        renderer(layer,f'{prefix}_class',colors); project.addMapLayer(layer)
        make_layout(project,layer,name,'Statistically Significant Complaint Hotspots — DKI Jakarta',
            subtitle+' · Getis-Ord Gi*',
            ('Queen order 1 + focal unit' if report['weights_method'].startswith('Queen') else 'Symmetric KNN k=4 + focal unit')+
            f'\nBinary weights; {PERMUTATIONS} permutations\nTwo-sided tests; seed {SEED}\nBH FDR within each variable\n\nColors use adjusted p (q) ≤ 0.05.\nDark colors use q ≤ 0.01.\nDirection uses permutation Z.\n\nGray areas lack evidence of\nclustering under this test; they\nmay still have high complaints.',
            filename, significance_field=f'{prefix}_significant')
    # Keep lower-layer labels and upper Gi* fills from overlapping in the canvas.
    for node in project.layerTreeRoot().findLayers():
        node.setItemVisibilityChecked(node.layerId() == priority.id())
    extent=QgsRectangle(priority.extent()); extent.scale(1.10)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent,project.crs()))
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    project.setFileName(str(OUT/'kecamatan_hotspot_project.qgz'))
    require(project.write(),'QGIS project save failed')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    app=None
    if QgsApplication.instance() is None:
        app=QgsApplication([],False); app.initQgis()
    g, report=validate(); g=assign_priority(g,report); g=statistics(g,report)
    gpkg=OUT/'kecamatan_hotspot_results.gpkg'
    pending=OUT/'kecamatan_hotspot_results.pending.gpkg'
    if pending.exists(): pending.unlink()
    g.to_file(pending,layer='kecamatan_hotspot',driver='GPKG')
    pending.replace(gpkg)
    for prefix, filename in [('rate','hasil_gistar_kejadian.geojson'), ('high','hasil_gistar_tinggi.geojson')]:
        columns=['pcode','kecamatan','kota','priority_label','priority_order','data_cukup','ranking',
                 'per100rb_kejadian','per100rb_tinggi'] + [x for x in g.columns if x.startswith(prefix+'_')] + ['geometry']
        g[columns].to_crs(4326).to_file(OUT/filename, driver='GeoJSON')
    g.drop(columns='geometry')[['pcode','kecamatan','kota','priority_label','priority_order','ranking',
        'data_cukup','n_kejadian','per100rb_tinggi','per100rb_sedang','per100rb_rendah']].sort_values(
        'priority_order').to_csv(OUT/'kecamatan_priority_labels.csv',index=False)
    g.drop(columns='geometry').to_csv(OUT/'kecamatan_hotspot_statistics.csv',index=False)
    (OUT/'validation_and_analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    cartography(report)
    print(json.dumps({'weights':report['weights_method'],'variables':report['variables']},indent=2))
    # Retain standalone QgsApplication until the process ends; avoid teardown races.
    return app


if __name__ == '__main__':
    _qgis_app=main()
