# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AutoCurve

 A QGIS plugin to run convert to curve automatically after edits
                              -------------------
        begin                : 2020-06-15
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Opengis
        email                : olivier@opengis.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os.path

import sip
from processing.gui import AlgorithmExecutor
from qgis.core import (
    QgsApplication,
    QgsFeatureRequest,
    QgsGeometry,
    QgsGeometryUtils,
    QgsMapLayerType,
    QgsPoint,
    QgsVertexId,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from . import settings
from .log import debug, log


class Plugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.auto_curve_enabled = False

    def _icon(self, name):
        return QIcon(os.path.join(os.path.dirname(__file__), "icons", name))

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.toolbar = self.iface.addToolBar("Autocurve")

        self.auto_curve_action = QAction(
            self._icon("autocurve.svg"), "Autocurve", self.toolbar
        )
        self.auto_curve_action.setCheckable(True)
        self.auto_curve_action.toggled.connect(self.toggle_auto_curve)
        self.toolbar.addAction(self.auto_curve_action)

        self.harmonize_arcs_action = QAction(
            self._icon("harmonize.svg"), "Harmonize arcs", self.toolbar
        )
        self.harmonize_arcs_action.setCheckable(True)
        self.harmonize_arcs_action.toggled.connect(self.toggle_harmonize_arcs)
        self.toolbar.addAction(self.harmonize_arcs_action)

        self.watched_layers = set()
        self._prevent_recursion = False

        self.watch_layer(self.iface.activeLayer())
        self.iface.currentLayerChanged.connect(self.watch_layer)

        self.auto_curve_action.setChecked(settings.autocurve_enabled())
        self.harmonize_arcs_action.setChecked(settings.harmonize_enabled())

    def unload(self):
        self.iface.mainWindow().removeToolBar(self.toolbar)

        for layer in self.watched_layers:
            if not sip.isdeleted(layer):
                layer.geometryChanged.disconnect(self.add_to_changelog)
                layer.featureAdded.disconnect(self.add_to_changelog)
                layer.editCommandStarted.connect(self.reset_changelog)
                layer.editCommandEnded.connect(self.run_after_edit_command)
        self.watched_layers = set()

    def toggle_auto_curve(self, checked):
        settings.set_autocurve_enabled(checked)

    def toggle_harmonize_arcs(self, checked):
        settings.set_harmonize_enabled(checked)

    def watch_layer(self, layer):
        # We watch geometryChanged and featureAdded on all layers
        if (
            layer
            and layer.type() == QgsMapLayerType.VectorLayer
            and layer not in self.watched_layers
        ):
            layer.geometryChanged.connect(self.add_to_changelog)
            layer.featureAdded.connect(self.add_to_changelog)
            layer.editCommandStarted.connect(self.reset_changelog)
            layer.editCommandEnded.connect(self.run_after_edit_command)
            self.watched_layers.add(layer)

    def reset_changelog(self):
        self.changed_fids = set()

    def add_to_changelog(self, fid, geometry=None):
        self.changed_fids.add(fid)

    def run_after_edit_command(self):
        """This is run after an edit command finished"""

        if not self.changed_fids:
            # No geometries have changed, no need to run
            return

        if self._prevent_recursion:
            # Avoiding recursion as the algorithm will also trigger geometryChanged
            return

        # Avoid recursion as the following code will trigger geometryChanged
        self._prevent_recursion = True

        # Select affected polygons
        layer = self.iface.activeLayer()
        layer.selectByIds(list(self.changed_fids))

        # Run autocurve procedure
        if settings.autocurve_enabled():
            self.curvify()

        # Run harmonize procedure
        if settings.harmonize_enabled():
            self.harmonize_arcs()

        # Remove selection
        layer.removeSelection()

        # Disable recursion prevention
        self._prevent_recursion = False

    def curvify(self):
        """Runs the convert to curves algorithm in place"""

        # Run converttocurves in-place
        alg = QgsApplication.processingRegistry().createAlgorithmById(
            "native:converttocurves"
        )
        AlgorithmExecutor.execute_in_place(
            alg, {"DISTANCE": settings.distance(), "ANGLE": settings.angle()}
        )

    def harmonize_arcs(self):
        """Iterates through all changed features and snaps arc centers to neighbouring arc centers"""

        layer = self.iface.activeLayer()

        layer.beginEditCommand("Harmonize arcs")

        debug(f"==== HARMONIZING ARCS ====")

        for feature in layer.selectedFeatures():

            debug(f"Arc snapping ft. {feature.id()}...")

            # Find all arcs points
            arcs_vertices = self._get_curve_points(feature.geometry())

            # Skip if not curved
            if not arcs_vertices:
                debug(f"-- no arc vertices segments, skipping")
                continue

            # Find all neighbours to test against
            request = QgsFeatureRequest()
            request.setDistanceWithin(feature.geometry(), settings.distance())
            neighbours = layer.getFeatures(request)

            # Iterate and check for snapping
            for arc_vertex in arcs_vertices:
                debug(f"-- Doing arc vertex {arc_vertex}")

                for neighbour in neighbours:
                    if neighbour.id() == feature.id():
                        continue

                    for nearby_arc_vertex in self._get_curve_points(
                        neighbour.geometry()
                    ):

                        debug(
                            f"---- testing against ft. {neighbour.id()} vtx. {nearby_arc_vertex}"
                        )

                        if self._can_snap(
                            feature, arc_vertex, neighbour, nearby_arc_vertex
                        ):
                            other_vertex = neighbour.geometry().vertexAt(
                                nearby_arc_vertex
                            )
                            new_geom = QgsGeometry(feature.geometry())
                            success = new_geom.moveVertex(other_vertex, arc_vertex)
                            if not success:
                                log(f"Error while snaping at {other_vertex}")
                            layer.changeGeometry(feature.id(), new_geom)
                            debug(
                                f"------ pt. {nearby_arc_vertex}: SNAPPED TO {other_vertex.asWkt()}"
                            )
                        else:
                            debug(f"------ pt. {nearby_arc_vertex}: NO SNAP")
        layer.endEditCommand()

    def _can_snap(self, feature_1, arc_vertex_1, feature_2, arc_vertex_2):
        """Returns whether both given vertices can snap."""
        # For now, we only snap if the start and end point are equal

        debug(
            f"------ CHECKING [ft. {feature_1.id()} vtx. {arc_vertex_1}] vs [ft. {feature_2.id()} vtx. {arc_vertex_2}]"
        )

        v_1a, v_1c = feature_1.geometry().adjacentVertices(arc_vertex_1)
        v_2a, v_2c = feature_2.geometry().adjacentVertices(arc_vertex_2)

        v_1a = arc_vertex_1 - 1
        v_1b = arc_vertex_1
        v_1c = arc_vertex_1 + 1
        v_2a = arc_vertex_2 - 1
        v_2b = arc_vertex_2
        v_2c = arc_vertex_2 + 1

        p1a = feature_1.geometry().vertexAt(v_1a)
        p1b = feature_1.geometry().vertexAt(v_1b)
        p1c = feature_1.geometry().vertexAt(v_1c)

        p2a = feature_2.geometry().vertexAt(v_2a)
        p2b = feature_2.geometry().vertexAt(v_2b)
        p2c = feature_2.geometry().vertexAt(v_2c)

        debug(
            f"------ COMPARING ARC [{p1a.asWkt()} {p1b.asWkt()} {p1c.asWkt()}] vs [{p2a.asWkt()} {p2b.asWkt()} {p2c.asWkt()}]"
        )

        # Test if start and end points are equal
        if not (self._almost_equal(p1a, p2a) and self._almost_equal(p1c, p2c)) and not (
            self._almost_equal(p1a, p2c) and self._almost_equal(p1c, p2a)
        ):
            debug(
                f"------ NO SNAP due to start/end point mismatch [{p1a.asWkt()} {p1c.asWkt()}] vs [{p2a.asWkt()} {p2c.asWkt()}]"
            )
            return False

        # Test if circles are equivalent (same center point within tolerance)
        _, c1x, c1y = QgsGeometryUtils.circleCenterRadius(p1a, p1b, p1c)
        _, c2x, c2y = QgsGeometryUtils.circleCenterRadius(p2a, p2b, p2c)
        if not self._almost_equal(QgsPoint(c1x, c1y), QgsPoint(c2x, c2y)):
            debug(
                f"------ NO SNAP due to center point distance above tolerance {QgsPoint(c1x, c1y).distance(QgsPoint(c2x, c2y))} [{c1x};{c1y}] vs [{c2x};{c2y}]"
            )
            return False

        return True

    def _almost_equal(self, p1, p2):
        return p1.distance(p2) <= settings.distance()

    def _get_curve_points(self, geometry):
        """Returns a list of vertex numbers that are curve points"""
        curved_vertices = []
        vertex_id = QgsVertexId()
        while True:
            found, point = geometry.constGet().nextVertex(vertex_id)
            if not found:
                break
            if vertex_id.type is QgsVertexId.VertexType.Curve:
                curved_vertices.append(geometry.vertexNrFromVertexId(vertex_id))

        return curved_vertices
