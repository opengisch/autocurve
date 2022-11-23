import math

X = 2600000
Y = 1200000
R = 1000


def circular_string(midpoint_f=0.5):
    angles = [0, midpoint_f * math.pi / 2, math.pi / 2]
    points = [(X + R * math.cos(a), Y + R * math.sin(a)) for a in angles]
    points_coords = ",".join([f"{p[0]} {p[1]}" for p in points])
    return f"CircularString ({points_coords})"


vl = QgsVectorLayer("CurvePolygon?crs=epsg:2056", "temp", "memory")

WKTS = [
    f"CurvePolygon (CompoundCurve ({circular_string(0.25)},({X} {Y + R}, {X} {Y}, {X+R} {Y})))",
    f"CurvePolygon (CompoundCurve ({circular_string(0.75)},({X} {Y + R}, {X+R} {Y+R}, {X+R} {Y})))",
]
for WKT in WKTS:
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(WKT))
    print(f.geometry())
    vl.dataProvider().addFeature(f)

QgsProject.instance().addMapLayer(vl)

# path = os.path.join(os.path.dirname(__file__), "test_layer_style.qml")
path = r"D:\Dropbox\Code\autocurve\test_data\test_layer_style.qml"
vl.loadNamedStyle(path)
vl.triggerRepaint()
