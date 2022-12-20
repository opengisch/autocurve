import math
import os
import timeit
from datetime import datetime
from pathlib import Path
from random import uniform

from qgis.core import (
    QgsApplication,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsSnappingConfig,
    QgsVectorLayer,
)
from qgis.gui import QgsMapCanvasTracer, QgsMapMouseEvent
from qgis.PyQt.QtCore import QEvent, QPoint, Qt
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

        self.__feedback_step += 1
        if not message:
            message = f"step {self.__feedback_step}"

        iface.messageBar().clearWidgets()
        iface.messageBar().pushMessage(
            "Info",
            f"Test `{self._testMethodName}`: {message}",
            duration=0,
        )

        if VISUAL_FEEDBACK:
            t = datetime.now()
            while (datetime.now() - t).total_seconds() < seconds:
                QgsApplication.processEvents()
        QgsApplication.processEvents()

    def _move_vertex(self, vl, feat_id, vtx_id, x, y, toggle_editing=True):
        """Helper to mimic a move vertex interaction"""
        if toggle_editing:
            vl.startEditing()
        vl.beginEditCommand("moving vertex")
        vl.moveVertex(x, y, feat_id, vtx_id)
        vl.endEditCommand()
        if toggle_editing:
            vl.commitChanges()

    def _segmented_arc(self, from_angle, to_angle, step):
        """Helper that returns a segmented arc (list of vertex) at given angle on the unit circle in WKT notation"""
        return ",".join(
            self._vtx_at_angle(a) for a in range(from_angle, to_angle + step, step)
        )

    def _vtx_at_angle(self, angle: int, radius=1) -> str:
        """Helper that returns a vertex at given angle on the unit circle in WKT notation"""
        angle = angle % 360
        return f"{radius*math.cos(math.radians(angle))} {radius*math.sin(math.radians(angle))}"

    def _make_layer(self, wkt_geoms, geom_type="curvepolygon") -> QgsVectorLayer:
        """Helper that adds a styled vector layer with the given geometries to the project and returns it"""
        vl = QgsVectorLayer(f"{geom_type}?crs=epsg:2056", "temp", "memory")
        for wkt_geom in wkt_geoms:
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromWkt(wkt_geom))
            vl.dataProvider().addFeature(feat)

        plugin_path = Path(QgsApplication.qgisSettingsDirPath())
        styles_path = plugin_path / "python" / "plugins" / "autocurve" / "tests"
        vl.loadNamedStyle(str(str(styles_path / f"{geom_type}.qml")))
        QgsProject.instance().addMapLayer(vl)
        return vl

    def test_center_points(self):
        # Disable the actions
        plugins["autocurve"].auto_curve_action.setChecked(False)
        plugins["autocurve"].harmonize_arcs_action.setChecked(False)

        # Create two shapes that have a common arc with a different center point
        vl = self._make_layer(
            [
                f"CURVEPOLYGON( COMPOUNDCURVE( (0 0, 0 1), CIRCULARSTRING(0 1, {self._vtx_at_angle(30)}, 1 0), (1 0, 0 0) ) )",
                f"CURVEPOLYGON( COMPOUNDCURVE( (1 1, 0 1), CIRCULARSTRING(0 1, {self._vtx_at_angle(60)}, 1 0), (1 0, 1 1) ) )",
            ],
        )

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

    def test_autocurve_basic(self):
        # Disable the actions
        plugins["autocurve"].auto_curve_action.setChecked(False)
        plugins["autocurve"].harmonize_arcs_action.setChecked(False)

        # Create a segmented shape
        vl = self._make_layer(
            [f"POLYGON(( 0 0, {self._segmented_arc(0, 90, 1)}, 0 0 ))"],
        )

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

    def test_autocurve_and_center_when_tracing(self):
        # Enable the actions
        plugins["autocurve"].auto_curve_action.setChecked(True)
        plugins["autocurve"].harmonize_arcs_action.setChecked(True)

        # Enable snapping
        snap_config = QgsSnappingConfig(QgsProject.instance())
        snap_config.setEnabled(True)
        QgsProject.instance().setSnappingConfig(snap_config)

        # Enable tracing
        tracer = QgsMapCanvasTracer.tracerForCanvas(iface.mapCanvas())
        tracer.actionEnableTracing().trigger()

        # Create an arc shape shape
        vl = self._make_layer(
            [
                f"CURVEPOLYGON( COMPOUNDCURVE( (0 0, 0 1), CIRCULARSTRING(0 1, {self._vtx_at_angle(30)}, 1 0), (1 0, 0 0) ) )",
            ],
        )

        self.feedback()

        # Select the layer
        iface.setActiveLayer(vl)

        # Start editing
        vl.startEditing()

        self.feedback()
        iface.actionAddFeature().trigger()
        tool = iface.mapCanvas().mapTool()

        self.feedback()
        tool.addVertex(QgsPointXY(1, 1))
        self.feedback()
        tool.addVertex(QgsPointXY(1, 0))
        self.feedback()
        tool.addVertex(QgsPointXY(0, 1))
        self.feedback()
        tool.cadCanvasReleaseEvent(
            QgsMapMouseEvent(
                iface.mapCanvas(),
                QEvent.Type.MouseButtonRelease,
                QPoint(),
                Qt.RightButton,
            )
        )

        self.feedback()
        vl.commitChanges()

        # The center points should now be the same
        self.assertEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # The second feature should be curvified
        self.assertEqual(vl.getFeature(2).geometry().constGet().nCoordinates(), 5)

    def test_harmonize_arcs_performance(self):

        step = 1
        iterations = 5

        # Create a test half sun :-)
        neighbours = []
        polygon_part = []
        for a in range(0, 180, step):
            polygon_part.append(
                f"CIRCULARSTRING({self._vtx_at_angle(a)}, {self._vtx_at_angle(a+2/3*step)}, {self._vtx_at_angle(a+step)})"
            )
            neighbours.append(
                f"CURVEPOLYGON(COMPOUNDCURVE(({self._vtx_at_angle(a, 2)}, {self._vtx_at_angle(a)}), CIRCULARSTRING({self._vtx_at_angle(a)}, {self._vtx_at_angle(a+1/3*step)}, {self._vtx_at_angle(a+step)}), ({self._vtx_at_angle(a+step)}, {self._vtx_at_angle(a+step, 2)}, {self._vtx_at_angle(a, 2)}))"
            )

        vl = self._make_layer(
            [
                f"CURVEPOLYGON(COMPOUNDCURVE((0 0, 1 0), {','.join(polygon_part)}, (-1 0, 0 0)))",
                *neighbours,
            ],
        )

        # Edit a feature with harmonize_arcs enabled
        plugins["autocurve"].harmonize_arcs_action.setChecked(True)

        def do():
            self._move_vertex(
                vl,
                feat_id=1,
                vtx_id=0,
                x=uniform(-0.1, 0.1),
                y=uniform(-0.1, 0.1),
                toggle_editing=False,
            )

        vl.startEditing()
        performance = timeit.timeit(do, number=iterations)
        vl.commitChanges()

        # The center points should now be the same
        self.assertEqual(
            vl.getFeature(1).geometry().vertexAt(2),
            vl.getFeature(2).geometry().vertexAt(2),
        )

        # Performance should be acceptable
        print(f"Ran {iterations} times in {performance:.4f}s")
        self.assertLess(
            performance,
            2.0 * iterations,
            "Performance is too bad !",
        )


if __name__ == "__console__":
    # Run from within QGIS console
    VISUAL_FEEDBACK = True
    unittest.main(IntegrationTest(), exit=False)
