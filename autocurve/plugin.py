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
from typing import List

import sip
from processing.gui import AlgorithmExecutor
from qgis.core import (
    QgsApplication,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMapLayerType,
    QgsVertexId,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from . import settings
from .utils import MiniIndex, SnapCurvePoint


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
        self.changed_fids = set()
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

        if not layer or not layer.isSpatial():
            return

        layer.beginEditCommand("Harmonize arcs")

        for feature in layer.selectedFeatures():

            # Find all arcs points
            snap_points = self._get_snap_points(feature)

            # Skip if not curved
            if not snap_points:
                continue

            # Find all neighbours to test against
            request = QgsFeatureRequest()
            request.setDistanceWithin(feature.geometry(), settings.distance())
            neighbours = list(layer.getFeatures(request))

            # Keep candidate snapping arcs
            index = MiniIndex(tolerance=settings.distance())
            nearby_snap_points = []
            for neighbour in neighbours:

                if neighbour.id() == feature.id():
                    # don't compare about itself
                    continue

                for nearby_snap_point in self._get_snap_points(neighbour):
                    nearby_snap_points.append(nearby_snap_point)
                    index.add_snap_point(nearby_snap_point)

            # This will hold the new geometry if it needs changes
            new_geom = None

            # Iterate on all arc vertics, combinined will all neighbouring arc vertices
            for snap_point in snap_points:

                for nearby_snap_point in index.get_neighbours(snap_point):

                    # Perform the actual snapping test
                    if snap_point.snaps_to(nearby_snap_point):

                        # Clone the geometry if not already cloned
                        if new_geom is None:
                            new_geom = QgsGeometry(feature.geometry())

                        success = new_geom.moveVertex(
                            nearby_snap_point.vertex, snap_point.vertex_nr
                        )
                        assert success

            # Apply the changed geometry
            if new_geom is not None:
                layer.changeGeometry(feature.id(), new_geom)

        layer.endEditCommand()

    def _get_snap_points(self, feature):
        """Returns a list of snap points for the given feature"""

        curved_vertices: List[SnapCurvePoint] = []
        vertex_id = QgsVertexId()
        while True:
            found, point = feature.geometry().constGet().nextVertex(vertex_id)
            if not found:
                break
            if vertex_id.type is QgsVertexId.VertexType.Curve:
                vertex_nr = feature.geometry().vertexNrFromVertexId(vertex_id)
                curved_vertices.append(SnapCurvePoint(feature, vertex_nr, point))

        return curved_vertices
