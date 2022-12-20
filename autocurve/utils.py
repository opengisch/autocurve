from dataclasses import dataclass

from qgis.core import QgsFeature, QgsGeometryUtils, QgsPoint

from . import settings


def _almost_equal(p1, p2):
    """Test point equality with tolerance"""
    return p1.distance(p2) <= settings.distance()


@dataclass
class SnappingVertexPoint:
    feature: QgsFeature
    vertex_nr: int
    vertex: QgsPoint

    def snaps_to(self, other: "SnappingVertexPoint"):

        if self.feature.id() == other.feature.id():
            return False

        # Get the 3 points that form both arcs
        v_1b = self.vertex_nr
        v_2b = other.vertex_nr
        v_1a, v_1c = self.feature.geometry().adjacentVertices(v_1b)
        v_2a, v_2c = other.feature.geometry().adjacentVertices(v_2b)

        p1a = self.feature.geometry().vertexAt(v_1a)
        p1b = self.feature.geometry().vertexAt(v_1b)
        p1c = self.feature.geometry().vertexAt(v_1c)

        p2a = other.feature.geometry().vertexAt(v_2a)
        p2b = other.feature.geometry().vertexAt(v_2b)
        p2c = other.feature.geometry().vertexAt(v_2c)

        # Test if start and end points are equal
        if not (_almost_equal(p1a, p2a) and _almost_equal(p1c, p2c)) and not (
            _almost_equal(p1a, p2c) and _almost_equal(p1c, p2a)
        ):
            return False

        # Test if circles are equivalent (same center point within tolerance)
        _, c1x, c1y = QgsGeometryUtils.circleCenterRadius(p1a, p1b, p1c)
        _, c2x, c2y = QgsGeometryUtils.circleCenterRadius(p2a, p2b, p2c)
        if not _almost_equal(QgsPoint(c1x, c1y), QgsPoint(c2x, c2y)):
            return False

        return True
