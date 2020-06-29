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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolBar

from qgis.core import QgsMessageLog, QgsApplication, QgsMapLayerType
from qgis.gui import QgsMapToolPan

from processing.gui import AlgorithmExecutor

import sip

import os.path


class Plugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.toolbar = self.iface.addToolBar("Autocurve")

        self.auto_curve_action = QAction(
            QIcon(os.path.join(self.plugin_dir, 'icon.svg')),
            'Autocurve',
            self.toolbar,
        )
        self.auto_curve_action.setCheckable(True)
        self.auto_curve_action.toggled.connect(self.toggle_auto_curve)
        self.toolbar.addAction(self.auto_curve_action)

        self.watched_layers = []
        self._prevent_recursion = False

        self.watch_layer(self.iface.activeLayer())
        self.iface.currentLayerChanged.connect(self.watch_layer)

        self.toggle_auto_curve(False)

    def unload(self):
        self.iface.mainWindow().removeToolBar(self.toolbar)

        for layer in self.watched_layers:
            if not sip.isdeleted(layer):
                layer.geometryChanged.disconnect(self.add_to_changelog)
                layer.featureAdded.disconnect(self.add_to_changelog)
                layer.editCommandStarted.connect(self.reset_changelog)
                layer.editCommandEnded.connect(self.curvify)

    def toggle_auto_curve(self, checked):
        self.auto_curve_enabled = checked

    def watch_layer(self, layer):
        # We watch geometryChanged and featureAdded on all layers
        if layer and layer.type() == QgsMapLayerType.VectorLayer and layer not in self.watched_layers:
            layer.geometryChanged.connect(self.add_to_changelog)
            layer.featureAdded.connect(self.add_to_changelog)
            layer.editCommandStarted.connect(self.reset_changelog)
            layer.editCommandEnded.connect(self.curvify)
            self.watched_layers.append(layer)

    def reset_changelog(self):
        self.changed_fids = []

    def add_to_changelog(self, fid, geometry=None):
        self.changed_fids.append(fid)

    def curvify(self):

        if not self.auto_curve_enabled:
            return

        if self._prevent_recursion:
            # Avoiding recursion as the algorithm will also trigger geometryChanged
            return

        alg = QgsApplication.processingRegistry().createAlgorithmById('native:converttocurves')
        layer = self.iface.activeLayer()
        layer.selectByIds(self.changed_fids)
        self._prevent_recursion = True
        AlgorithmExecutor.execute_in_place(alg, {})
        self._prevent_recursion = False
        layer.removeSelection()
