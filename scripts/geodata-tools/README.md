# Rebuilding the open boundary database

The generated boundary data is © OpenStreetMap contributors; Terrae, ODbL 1.0.
Source URLs, snapshot dates, SHA-256 hashes and adaptations are recorded in
`site/data/boundary-sources.json`. Large upstream GeoPackages are not committed.

Install the tools in this directory, outside the website's runtime dependencies:

```sh
npm install --prefix scripts/geodata-tools --ignore-scripts
python3 -m pip install -r scripts/geodata-tools/requirements.txt
```

Download the pinned source GeoPackages into a separate directory. Their local
filenames and expected hashes are listed in `scripts/build_osm_borders.py`.
Then run:

```sh
python3 scripts/build_osm_borders.py --sources /path/to/source-files
python3 scripts/build_web.py
node tests/osm-boundaries.mjs
```

The build preserves existing territory codes and worldview assignment masks.
It combines the publisher's high-detail shared land boundaries with its medium
coastline at common junctions, filters small isolated rings, and uses Mapshaper's
topology repair and intersection-aware simplification. Shapely then repairs and
validates every feature on a common 1e-8 degree grid before the final topology
is encoded; this prevents rounding from creating microscopic crossings. The detailed generated
master is not committed: reproducible compressed country groups in
`site/geodata/borders/` are the distributed source database. The web build
decompresses them and offers the full adapted database in `borders-odbl.zip`.

The Pieniny fixture is native OSM geometry from Terrae 2026.10 and is also ODbL.
It tests actual geometric improvement against the previous Natural Earth map.
