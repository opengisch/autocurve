from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from qgis.core import QgsFeature, QgsGeometryUtils, QgsPoint

from . import settings


def _almost_equal(p1, p2):
    """Test point equality with tolerance"""
    return p1.distance(p2) <= settings.distance()


@dataclass
class SnapCurvePoint:
    """Helper class to represents a curve point on which we can snap."""

    feature: QgsFeature
    vertex_nr: int
    vertex: QgsPoint

    @property
    def arc_nrs(self):
        # Get the 3 points indices that form the arcs
        v_b = self.vertex_nr
        v_a, v_c = self.feature.geometry().adjacentVertices(v_b)
        return (v_a, v_b, v_c)

    @property
    def arc_points(self):
        # Get the 3 QgsPoints that form the arcs
        v_a, v_b, v_c = self.arc_nrs
        return (
            self.feature.geometry().vertexAt(v_a),
            self.feature.geometry().vertexAt(v_b),
            self.feature.geometry().vertexAt(v_c),
        )

    def snaps_to(self, other: "SnapCurvePoint"):
        # Dont snap the feature against itself
        if self.feature.id() == other.feature.id():
            return False

        p1a, p1b, p1c = self.arc_points
        p2a, p2b, p2c = other.arc_points

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


class MiniIndex:
    """Specialized index that indexes arcs by start/endpoint for fast retrieval"""

    def __init__(self, tolerance):
        self.tolerance = tolerance
        self.index: Dict[Tuple[int, int, int, int], List[SnapCurvePoint]] = defaultdict(
            list
        )

    def _make_key(self, snap_point: SnapCurvePoint):
        p_a, _, p_c = snap_point.arc_points

        # Sort the start/endpoint so index ignores segment direction
        if (p_c.x(), p_c.y()) < (p_a.x(), p_a.y()):
            p_a, p_c = p_c, p_a

        return (
            int(p_a.x() // self.tolerance),
            int(p_a.y() // self.tolerance),
            int(p_c.x() // self.tolerance),
            int(p_c.y() // self.tolerance),
        )

    def add_snap_point(self, snap_point: SnapCurvePoint):
        key = self._make_key(snap_point)
        self.index[key].append(snap_point)

    def get_neighbours(self, snap_point: SnapCurvePoint) -> List[SnapCurvePoint]:
        key = self._make_key(snap_point)
        return self.index[key]
