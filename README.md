# Curved splig&merge for QGIS

Split&merge map tools that support curved geometries.

![screenast](readme.gif)

This just wraps the split&merge tools with the new ConvertToCurves geometries algorithm that exists since QGIS 3.14.

WARNING : QGIS doesn't support curved geometry operations. which is why by default geometries are segmentized when using split or merge. This means intersections aren't geometrically accurate. The ConvertToCurve just transforms successive points back into curves for easier subsequent editting.