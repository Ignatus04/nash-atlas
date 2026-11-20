"""Build the site's ODbL boundary database from Terrae's OSM release.

Usage: python scripts/build_osm_borders.py --sources DIRECTORY --node NODE
Requires shapely==2.1.2; download the pinned GeoPackages listed in the source
manifest. Large upstream files remain outside the repository.
"""
import argparse, hashlib, json, sqlite3, subprocess
from pathlib import Path
from shapely import from_wkb, make_valid, get_num_coordinates
from shapely.geometry import shape, mapping, MultiPolygon, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polygonize

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026.10'
BASE_URL = 'https://huggingface.co/buckets/geodataset/terrae/resolve/'
SOURCE_FILES = {
    'reference': ('atlas-osm-medium.gpkg', 'adm0/2026.10/world/terrae-adm0-2026.10-medium-reference-polygons.gpkg', '563757e658a9df6e3ef7fa1dce45e23ef4305023ca488a3d6a4ea9630587d0d5'),
    'land': ('atlas-osm-high-lines.gpkg', 'full/adm0/2026.10/world/terrae-adm0-2026.10-high-reference-lines.gpkg', '73d28af5ea883361181d9914bce8a3bbc64f1b1c137ea5c9ff2d76d1164d85d2'),
    'coast': ('atlas-osm-medium-lines.gpkg', 'adm0/2026.10/world/terrae-adm0-2026.10-medium-reference-lines.gpkg', '402706a947808711c4936345a2d63ea8fcd6c702e7f73ec4127e20273c19417c'),
    'de_facto': ('atlas-osm-defacto-high.gpkg', 'full/adm0/2026.10/world/terrae-adm0-2026.10-high-de_facto-polygons.gpkg', '53355ed117b1171b5d27dc5025301ca4c69b55471324a1f40a3222cccbbd2acb'),
    'disputes': ('atlas-osm-disputes-high.gpkg', 'full/adm0/2026.10/world/terrae-adm0-2026.10-high-disputes-polygons.gpkg', 'd2e3d3a8577a158ebfb6d06406bdc2433b8b95a31f52c6e998b8729c94c682eb'),
}

def polys(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if not hasattr(g, 'geoms'):
        return []
    return [p for child in g.geoms for p in polys(child)]

def polygonal(g):
    return MultiPolygon(polys(make_valid(g)))

def read_gpkg(path, table, key, where=''):
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    result = {}
    for row in conn.execute('SELECT * FROM ' + table + (' WHERE ' + where if where else '')):
        props = dict(row)
        blob = props.pop('geom')
        # GeoPackage binary header followed by standard WKB (OGC 12-128r18).
        assert blob[:2] == b'GP'
        envelope = (blob[3] >> 1) & 7
        offset = 8 + {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[envelope]
        result[props[key]] = (props, from_wkb(blob[offset:]))
    conn.close()
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--node', default='node')
    parser.add_argument('--topo-server', default=str(ROOT / 'scripts/geodata-tools/node_modules/topojson-server'))
    parser.add_argument('--mapshaper', default=str(ROOT / 'scripts/geodata-tools/node_modules/mapshaper/bin/mapshaper'))
    args = parser.parse_args()
    legacy_path = ROOT / 'scripts/src/countries_legacy.topo.json'
    assert legacy_path.exists(), 'The pinned legacy assignment masks are required'
    script = "const fs=require('fs'),tc=require('./node_modules/topojson-client');const t=JSON.parse(fs.readFileSync(process.argv[1]));process.stdout.write(JSON.stringify(tc.feature(t,t.objects[Object.keys(t.objects)[0]])));"
    legacy = json.loads(subprocess.check_output([args.node, '-e', script, str(legacy_path)], cwd=ROOT))['features']
    old_props, old_geom = {}, {}
    for f in legacy:
        k = f['properties']['k']
        if k not in old_props or (old_props[k].get('small') and not f['properties'].get('small')):
            old_props[k] = f['properties']
        old_geom.setdefault(k, []).append(polygonal(shape(f['geometry'])))
    old_geom = {k: polygonal(unary_union(gs)) for k, gs in old_geom.items()}
    sources = {}
    for table, (filename, url, expected) in SOURCE_FILES.items():
        path = args.sources / filename
        h = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        if expected:
            assert h == expected, f'Source checksum mismatch: {filename}'
        sources[table] = {'url': BASE_URL + url, 'sha256': h}
    print('Reading pinned OSM partitions', flush=True)
    ref = read_gpkg(args.sources / SOURCE_FILES['reference'][0], 'reference', 'unit_key')
    land = read_gpkg(args.sources / SOURCE_FILES['land'][0], 'reference_lines', 'line_id', "line_kind='land_boundary'")
    coast = read_gpkg(args.sources / SOURCE_FILES['coast'][0], 'reference_lines', 'line_id', "line_kind='coastline'")
    detail = read_gpkg(args.sources / SOURCE_FILES['de_facto'][0], 'de_facto', 'feature_key', "feature_kind='authority'")
    disputes = read_gpkg(args.sources / SOURCE_FILES['disputes'][0], 'disputes', 'area_id')
    seams = unary_union([LineString([[-180,-90],[-180,90]]), LineString([[180,-90],[180,90]])])
    # The publisher's detail levels retain the same junctions. Reassemble each
    # country from the high-detail land lines and the medium coastline, sharing
    # the exact same land line with its neighbour. No independent border thinning.
    for key, (props, original) in list(ref.items()):
        if key == 'ATA':
            continue
        lines = [g for p,g in coast.values() if p['side_a'] == key]
        lines += [g for p,g in land.values() if key in (p['side_a'],p['side_b'])]
        lines.append(original.boundary.intersection(seams))
        faces = [p for p in polygonize(unary_union(lines)) if original.covers(p.representative_point())]
        rebuilt = MultiPolygon(faces)
        if not rebuilt.is_valid:
            rebuilt = polygonal(unary_union(faces))
        assert rebuilt.is_valid and abs(rebuilt.area/original.area - 1) < .03, f'Open or invalid country ring: {key}'
        ref[key] = (props, rebuilt)
    print('Reassembled countries with shared high-detail land borders', flush=True)
    geoms = {}
    unmatched = []
    for key, (p, g) in ref.items():
        k = p['code_a2']
        if k == 'UM':
            k = 'US'
        if k == 'TK':
            k = 'NZ'
        if k in old_props:
            geoms.setdefault(k, []).append(g)
        else:
            unmatched.append((key, g))
    geoms = {k: polygonal(gs[0] if len(gs) == 1 else MultiPolygon([p for g in gs for p in polys(g)])) for k, gs in geoms.items()}
    print('Matched country codes; assigning special areas', flush=True)
    # Small unassigned/special areas keep the previous site's assignment. Their
    # land contours are OSM; only the assignment mask comes from the old map.
    for key, g in unmatched:
        print('Special area: ' + key, flush=True)
        remaining = g
        for k, mask in sorted(old_geom.items(), key=lambda kv: -kv[1].intersection(g).area):
            if k.startswith('~') or remaining.is_empty:
                continue
            part = polygonal(remaining.intersection(mask))
            if part.is_empty:
                continue
            geoms[k] = polygonal(unary_union([geoms.get(k, MultiPolygon()), part]))
            remaining = polygonal(remaining.difference(part))
        if not remaining.is_empty:
            # Documented fallback: closest existing territory, never drop land.
            k = min((k for k in old_geom if not k.startswith('~')), key=lambda k: old_geom[k].distance(remaining))
            geoms[k] = polygonal(unary_union([geoms.get(k, MultiPolygon()), remaining]))
    # Keep the current de facto identities and worldview rules. Recognized state
    # boundaries come from the same source partition, so neighbours share edges.
    authorities = {'XA': ('GE', 'DF-ABKHAZIA'), 'XO': ('GE', 'DF-SOUTH-OSSETIA'),
                   'XN': ('CY', 'DF-NORTHERN-CYPRUS'), 'XT': ('MD', 'DF-TRANSNISTRIA'),
                   'XS': ('SO', 'DF-SOMALILAND')}
    for k, (host, source) in authorities.items():
        part = polygonal(geoms[host].intersection(detail[source][1]))
        assert not part.is_empty, k
        geoms[k] = part
        geoms[host] = polygonal(geoms[host].difference(part))
    print('Applying existing territory masks', flush=True)
    # The existing control line is deliberately retained, rather than silently
    # replacing safety-related geography with an older OSM snapshot.
    control_mask = unary_union([old_geom['XU'], *[g for k,g in old_geom.items() if old_props[k].get('host') == 'XU']])
    part = polygonal(geoms['UA'].intersection(control_mask))
    geoms['XU'] = part
    geoms['UA'] = polygonal(geoms['UA'].difference(part))
    # Clipperton is filed under France in this source but has its own site card.
    cp = polygonal(geoms['FR'].intersection(old_geom['CP'].buffer(.05)))
    if not cp.is_empty:
        geoms['CP'] = cp
        geoms['FR'] = polygonal(geoms['FR'].difference(cp))
    else:
        geoms['CP'] = old_geom['CP']
    # Western Sahara: preserve the site's two holders, using the source berm.
    west = polygonal(geoms['EH'].intersection(disputes['WS-WEST'][1]))
    geoms['~W. Sahara'] = west
    geoms['EH'] = polygonal(geoms['EH'].difference(west))
    source_masks = {'~Aksai Chin': 'AKSAI-CHIN', '~Arunachal Pradesh': 'ARUNACHAL',
                    '~Shaksam Valley': 'SHAKSGAM', '~Golan Heights': 'GOLAN',
                    '~Kuril Is.': 'KURILS', '~Siachen Glacier': 'SIACHEN'}
    mask_notes = []
    for k, p in old_props.items():
        if not k.startswith('~') or k == '~W. Sahara':
            continue
        host = p['host']
        mask = old_geom[k]
        if k in source_masks:
            candidate = disputes[source_masks[k]][1]
            overlap = candidate.intersection(mask).area / max(candidate.union(mask).area, 1e-12)
            if overlap > .90:
                mask = candidate
            else:
                mask_notes.append(k)
        else:
            mask_notes.append(k)
        # The reference partition assigns the Golan to Syria; the existing
        # piece records Israel as its de facto holder, separately from its view.
        hosts = [host, 'SY'] if k == '~Golan Heights' else [host]
        part = polygonal(unary_union([geoms[h].intersection(mask) for h in hosts]))
        geoms[k] = part
        for h in hosts:
            geoms[h] = polygonal(geoms[h].difference(part))
    assert set(old_props) <= set(geoms), sorted(set(old_props) - set(geoms))
    # D3 uses clockwise exterior rings, opposite to RFC 7946's default.
    features = []
    for k, g in geoms.items():
        assert not g.is_empty, f'Empty country/piece: {k}'
        assert g.is_valid, k
        g = MultiPolygon([orient(p, sign=-1) for p in polys(g)])
        features.append({'type': 'Feature', 'properties': old_props[k], 'geometry': mapping(g)})
    output = args.sources / 'atlas-osm-partition.geojson'
    output.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False, separators=(',', ':')))
    metadata = {'source': 'Terrae ADM0 2026.10, derived from OpenStreetMap', 'snapshot': '2026-09-28',
                'license': 'ODbL-1.0', 'licenseUrl': 'https://opendatacommons.org/licenses/odbl/1-0/',
                'attribution': '© OpenStreetMap contributors; Terrae', 'sources': sources,
                'adaptations': ['Site territory codes and existing worldview assignment masks', 'Shared-arc overview simplification; high-detail land borders and medium coastline reassembled at common source junctions'],
                'legacyMasks': sorted(mask_notes), 'controlLine': 'Previous site dataset, unchanged',
                'upstreamSimplificationToleranceM': 15, 'coastlineSimplificationToleranceM': 150,
                'isolatedRingAreaFilterDeg2': {'overview': .01, 'detailed': .00001},
                'preservedRings': 'Largest exterior of each territory and all shared land-border rings',
                'geometryRepair': 'mapshaper 0.8.6 topology cleaning; overview simplification with intersection repair; Shapely valid-output snap rounding on a common 1e-8 degree grid',
                'coordinateGridDegrees': 1e-8,
                'features': len(features), 'inputVertices': sum(int(get_num_coordinates(g)) for g in geoms.values())}
    (ROOT / 'site/data/boundary-sources.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps({'features': len(features), 'vertices': metadata['inputVertices'], 'legacyMasks': mask_notes}), flush=True)
    subprocess.run([args.node, '--max-old-space-size=10000', str(ROOT / 'scripts/build_osm_topology.cjs'), str(output), args.topo_server, args.mapshaper], cwd=ROOT, check=True)
    from validate_osm_geometry import run as validate_geometry
    validate_geometry(args.node,args.topo_server,args.sources)
    for level in ('countries', 'countries-detail'):
        final = json.loads(subprocess.check_output([args.node, '-e', script, str(ROOT / 'site/data' / (level + '.json'))], cwd=ROOT))['features']
        assert {f['properties']['k'] for f in final} == set(old_props), 'A territory code was lost'
        invalid = [f['properties']['k'] for f in final if not f['geometry'] or not shape(f['geometry']).is_valid]
        assert not invalid, f'Invalid {level} geometry: {invalid}'
        print(json.dumps({'level': level, 'validFeatures': len(final)}), flush=True)
    subprocess.run([args.node, str(ROOT / 'scripts/pack_osm_borders.cjs')], cwd=ROOT, check=True)

if __name__ == '__main__':
    main()
