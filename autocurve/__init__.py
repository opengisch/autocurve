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


def classFactory(iface):
    from .plugin import Plugin

    return Plugin(iface)
