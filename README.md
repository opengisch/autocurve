# Autocurve for QGIS

Adds a toggle that automatically runs the new ConvertToCurves algorithm after edit commands such as split or merge.

![screenast](readme.gif)

This requires QGIS 3.14 or newer.

WARNING : QGIS doesn't support curved geometry operations, which is why by default geometries are segmentized when using features such as split or merge. This means intersections aren't geometrically accurate. The ConvertToCurve just transforms successive points back into curves for easier subsequent editing.
