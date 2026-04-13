Recommended workflow:

1. Use an `*.mbtiles` file for offline imagery.
2. Load it from the UI with `Select MBTiles`, or install it into `data/offline.mbtiles`.
3. Switch the map mode to `Offline`.

The built-in local tile server reads tiles from MBTiles and exposes them to Leaflet.

If you still want to use raw tiles, keep the standard slippy-map layout:

`{z}/{x}/{y}.png`
