# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CurvedSplitAndMerge
                                 A QGIS plugin
 Helper to run split and merge on curved geometries
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
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

# Initialize Qt resources from file resources.py
from .resources_rc import *
import os.path


class Plugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CurvedSplitAndMerge_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CurvedSplitAndMerge', message)


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.toolbar = self.iface.addToolBar(self.tr(u"Curved Split and Merge"))

        self.split_action = QAction(
            QIcon(':/plugins/curved_split_merge/icons/CurvedActionSplitFeatures.svg'),
            self.tr(u'Split and curvify'),
            self.toolbar,
        )
        self.split_action.triggered.connect(self.split)
        self.toolbar.addAction(self.split_action)

        self.merge_action = QAction(
            QIcon(':/plugins/curved_split_merge/icons/CurvedActionMergeFeatures.svg'),
            self.tr(u'Merge and curvify'),
            self.toolbar,
        )
        self.merge_action.triggered.connect(self.merge)
        self.toolbar.addAction(self.merge_action)

        self.watched_layers = []
        self.curvify_enabled = False
        self.previous_maptool = None

        self.watch_layer(self.iface.activeLayer())
        self.iface.currentLayerChanged.connect(self.watch_layer)
        self.refresh_enabled()

    def unload(self):
        self.iface.mainWindow().removeToolBar(self.toolbar)

        for layer in self.watched_layers:
            if not sip.isdeleted(layer):
                layer.editCommandEnded.disconnect(self.curvify)
                layer.editingStarted.disconnect(self.refresh_enabled)
                layer.editingStopped.disconnect(self.refresh_enabled)


    def watch_layer(self, layer):
        # We watch editCommandEnded on all layers
        if layer and layer.type() == QgsMapLayerType.VectorLayer and layer not in self.watched_layers:
            layer.editCommandEnded.connect(self.curvify)
            layer.editingStarted.connect(self.refresh_enabled)
            layer.editingStopped.connect(self.refresh_enabled)
            self.watched_layers.append(layer)

    def refresh_enabled(self):
        layer = self.iface.activeLayer()
        enabled = layer and layer.isEditable()
        self.split_action.setEnabled(bool(enabled))
        self.merge_action.setEnabled(bool(enabled))

    def split(self):
        self.curvify_enabled = True
        self.previous_maptool = self.iface.mapCanvas().mapTool()
        action = self.iface.actionSplitFeatures()
        action.trigger()

    def merge(self):
        self.curvify_enabled = True
        self.previous_maptool = None
        # action = self.iface.actionMergeFeatures()  # this is missing in the API :-/
        action = next(a for a in self.iface.advancedDigitizeToolBar().actions() if a.objectName()=='mActionMergeFeatures')
        action.trigger()


    def curvify(self):

        if not self.curvify_enabled:
            # Avoiding recursion as the algorithm will also trigger editCommandEnded
            return
        self.curvify_enabled = False

        alg = QgsApplication.processingRegistry().createAlgorithmById('native:converttocurves')
        layer = self.iface.activeLayer()
        layer.removeSelection()
        AlgorithmExecutor.execute_in_place(alg, {'INPUT': layer})
        layer.removeSelection()

        if self.previous_maptool:
            self.iface.mapCanvas().setMapTool( self.previous_maptool )
            self.previous_maptool = None
