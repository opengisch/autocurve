import math

X = 0
Y = 0
R = 10


def circular_string(midpoint_f=0.5):
    angles = [0, midpoint_f * math.pi / 2, math.pi / 2]
    points = [(X + R * math.cos(a), Y + R * math.sin(a)) for a in angles]
    points_coords = ",".join([f"{p[0]} {p[1]}" for p in points])
    return f"CircularString ({points_coords})"


WKTS_PER_TYPE = {
    "CurvePolygon": [
        f"CurvePolygon (CompoundCurve ({circular_string(0.45)},({X} {Y + R}, {X} {Y}, {X+R} {Y})))",
        f"CurvePolygon (CompoundCurve ({circular_string(0.55)},({X} {Y + R}, {X+R} {Y+R}, {X+R} {Y})))",
    ],
    "CompoundCurve": [
        f"CompoundCurve (({X+R/2} {Y}, {X+R} {Y}), {circular_string(0.45)},({X} {Y + R}, {X} {Y+R/2}))",
        f"CompoundCurve (({X+R} {Y+R/2}, {X+R} {Y}),{circular_string(0.55)},({X} {Y + R}, {X+R/2} {Y+R}))",
    ],
}

for layer_type, WKTS in WKTS_PER_TYPE.items():
    vl = QgsVectorLayer(f"{layer_type}?crs=epsg:2056", "temp", "memory")

    for WKT in WKTS:
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromWkt(WKT).forceRHR())
        print(f.geometry())
        vl.dataProvider().addFeature(f)

    QgsProject.instance().addMapLayer(vl)

    # path = os.path.join(os.path.dirname(__file__), "test_data" , f"style-{layer_type}.qml")
    path = f"D:\\Dropbox\\Code\\autocurve\\test_data\\style-{layer_type}.qml"
    vl.loadNamedStyle(path)
    vl.triggerRepaint()
