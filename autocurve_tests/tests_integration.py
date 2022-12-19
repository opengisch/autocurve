import math
import os
from datetime import datetime
from pathlib import Path

from qgis.core import (
    QgsApplication,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.testing import unittest
from qgis.utils import iface, plugins

VISUAL_FEEDBACK = os.environ.get("AUTOCURVE_VISUAL_FEEDBACK") == "true"


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.__feedback_step = 0
        self.feedback("starting")

    def tearDown(self):
        self.feedback("finished")
        iface.messageBar().clearWidgets()
        QgsProject.instance().removeAllMapLayers()
        QgsProject.instance().setDirty(False)

    def feedback(self, message=None, seconds=1):
        """Waits a little so we can see what happens when running the tests with GUI"""
        if not VISUAL_FEEDBACK:
            return

        self.__feedback_step += 1
        if not message:
            message = f"step {self.__feedback_step}"

        iface.messageBar().clearWidgets()
        iface.messageBar().pushMessage(
            "Info",
            f"Test `{self._testMethodName}`: {message}",
            duration=0,
        )

        t = datetime.now()
        while (datetime.now() - t).total_seconds() < seconds:
            QgsApplication.processEvents()

    def _move_vertex(self, vl, feat_id, vtx_id, x, y):
        vl.startEditing()
        vl.beginEditCommand("moving vertex")
        vl.moveVertex(x, y, feat_id, vtx_id)
        vl.endEditCommand()
        vl.commitChanges()

    def _vtx_at_angle(self, angle: int) -> str:
        """Returns a vertex at given angle in WKT notation"""
        return f"{math.cos(math.radians(angle))} {math.sin(math.radians(angle))}"

    def test_center_points(self):
        # Disable the actions
        plugins["autocurve"].auto_curve_action.setChecked(False)
        plugins["autocurve"].harmonize_arcs_action.setChecked(False)

        # Create two shapes that have a common arc with a different center point
        WKT_A = f"CURVEPOLYGON( COMPOUNDCURVE( (0 0, 0 1), CIRCULARSTRING(0 1, {self._vtx_at_angle(30)}, 1 0), (1 0, 0 0) ) )"
        WKT_B = f"CURVEPOLYGON( COMPOUNDCURVE( (1 1, 0 1), CIRCULARSTRING(0 1, {self._vtx_at_angle(60)}, 1 0), (1 0, 1 1) ) )"

        # Add them to a layer
        vl = QgsVectorLayer(f"curvepolygon?crs=epsg:2056", "temp", "memory")
        for WKT in [WKT_A, WKT_B]:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromWkt(WKT).forceRHR())
            vl.dataProvider().addFeature(feat)

        vl.loadNamedStyle(str(Path(__file__).parent / "curvepolygon.qml"))
        QgsProject.instance().addMapLayer(vl)

        self.feedback()

        # Select the layer
        iface.setActiveLayer(vl)

        # The center points are different
        self.assertNotEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # Edit a feature with harmonize_arcs disabled
        self._move_vertex(vl, feat_id=1, vtx_id=0, x=-0.1, y=-0.1)

        self.feedback()

        # The center points should still be different
        self.assertNotEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # Edit a feature with harmonize_arcs enabled
        plugins["autocurve"].harmonize_arcs_action.setChecked(True)
        self._move_vertex(vl, feat_id=1, vtx_id=0, x=-0.2, y=-0.2)

        self.feedback()

        # The center points should now be the same
        self.assertEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

    def test_autocurve(self):
        # Disable the actions
        plugins["autocurve"].auto_curve_action.setChecked(False)
        plugins["autocurve"].harmonize_arcs_action.setChecked(False)

        # Create a segmented shape
        SEGMENTED_ARC = ",".join(self._vtx_at_angle(a) for a in range(0, 90, 1))
        WKT = f"POLYGON(( 0 0, {SEGMENTED_ARC}, 0 0 ))"

        # Add them to a layer
        vl = QgsVectorLayer(f"curvepolygon?crs=epsg:2056", "temp", "memory")
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromWkt(WKT).forceRHR())
        vl.dataProvider().addFeature(feat)

        vl.loadNamedStyle(str(Path(__file__).parent / "curvepolygon.qml"))
        QgsProject.instance().addMapLayer(vl)

        self.feedback()

        # Select the layer
        iface.setActiveLayer(vl)

        # The arc is still segmented
        self.assertGreater(vl.getFeature(1).geometry().constGet().nCoordinates(), 5)

        # Edit a feature with harmonize_arcs disabled
        self._move_vertex(vl, feat_id=1, vtx_id=0, x=-0.1, y=-0.1)

        self.feedback()

        # The arc should still be segmented
        self.assertGreater(vl.getFeature(1).geometry().constGet().nCoordinates(), 5)

        # Edit a feature with harmonize_arcs enabled
        plugins["autocurve"].auto_curve_action.setChecked(True)
        self._move_vertex(vl, feat_id=1, vtx_id=0, x=-0.2, y=-0.2)

        self.feedback()

        # The arc should now be curvified
        self.assertEqual(vl.getFeature(1).geometry().constGet().nCoordinates(), 5)
