import math
import os
from datetime import datetime

from qgis.core import (
    QgsApplication,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.testing import start_app, unittest
from qgis.utils import iface

headless = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

if headless:
    start_app()


class TestAutocurve(unittest.TestCase):
    def setUp(self):
        if headless:
            return
        iface.messageBar().pushMessage(
            "Info",
            f"Running test `{self._testMethodName}`",
            duration=0,
        )

    def tearDown(self):
        if headless:
            return
        self._sleep()
        iface.messageBar().clearWidgets()

    def _sleep(self, seconds=5):
        if headless:
            return
        t = datetime.now()
        while (datetime.now() - t).total_seconds() < seconds:
            QgsApplication.processEvents()

    def test_center_points(self):
        # Create two shapes that have a common arc with a different center point
        CP_A = [math.cos(math.radians(30)), math.sin(math.radians(30))]
        CP_B = [math.cos(math.radians(60)), math.sin(math.radians(60))]
        WKT_A = f"CURVEPOLYGON( COMPOUNDCURVE( (0 0, 0 1), CIRCULARSTRING(0 1, {CP_A[0]} {CP_A[1]}, 1 0), (1 0, 0 0) ) )"
        WKT_B = f"CURVEPOLYGON( COMPOUNDCURVE( (1 1, 0 1), CIRCULARSTRING(0 1, {CP_B[0]} {CP_B[1]}, 1 0), (1 0, 1 1) ) )"

        # Add them to a layer
        vl = QgsVectorLayer(f"curvepolygon?crs=epsg:2056", "temp", "memory")
        for WKT in [WKT_A, WKT_B]:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromWkt(WKT).forceRHR())
            vl.dataProvider().addFeature(feat)
        QgsProject.instance().addMapLayer(vl)

        # Select the layer
        iface.setActiveLayer(vl)

        # The center points are different
        self.assertNotEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # Edit a feature with harmonize_arcs disabled
        # plugins["autocurve"].toggle_harmonize_arcs(checked=False)  # TODO: somehow load the plugin
        vl.startEditing()
        vl.moveVertex(-0.1, -0.1, 1, 0)
        vl.triggerRepaint()
        vl.commitChanges()

        # The center points should still be different
        self.assertNotEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # Edit a feature with harmonize_arcs disabled
        # plugins["autocurve"].toggle_harmonize_arcs(checked=True)  # TODO: somehow load the plugin
        vl.startEditing()
        vl.moveVertex(-0.2, -0.2, 1, 0)
        vl.triggerRepaint()
        vl.commitChanges()

        # The center points should now be the same
        self.assertEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )


if __name__ == "__main__":
    unittest.main()
