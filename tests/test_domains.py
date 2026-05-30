"""Unit tests for synthetic domain boundary generators."""

import numpy as np
import pytest

from quadmesh.domains import onion_polygon


class TestOnionPolygon:
    """Test suite for onion_polygon generator."""

    def test_shape_and_dtype(self):
        """Default onion_polygon() returns (240,2) float64. close=True returns (241,2) with row 0 == row -1."""
        poly = onion_polygon()
        assert poly.shape == (240, 2)
        assert poly.dtype == np.float64

        poly_closed = onion_polygon(close=True)
        assert poly_closed.shape == (241, 2)
        assert np.allclose(poly_closed[0], poly_closed[-1])

    def test_ccw(self):
        """Signed shoelace area > 0 (counter-clockwise)."""
        poly = onion_polygon()
        # Shoelace formula: 0.5 * sum((x[i] * y[i+1] - x[i+1] * y[i]))
        x = poly[:, 0]
        y = poly[:, 1]
        # Wrap around: append first point to close the ring for shoelace.
        x_closed = np.append(x, x[0])
        y_closed = np.append(y, y[0])
        signed_area = 0.5 * np.sum(x_closed[:-1] * y_closed[1:] - x_closed[1:] * y_closed[:-1])
        assert signed_area > 0

    def test_no_duplicate_consecutive(self):
        """With close=False, no two consecutive rows equal; first row != last row."""
        poly = onion_polygon(close=False)
        # Check no consecutive duplicates.
        for i in range(len(poly) - 1):
            assert not np.allclose(poly[i], poly[i + 1])
        # First row != last row.
        assert not np.allclose(poly[0], poly[-1])

    def test_no_self_intersection(self):
        """Brute-force O(n^2) segment-intersection check over closed ring."""

        def ccw(A, B, C):
            """Counter-clockwise orientation test. Returns positive if CCW, negative if CW, ~0 if collinear."""
            return (C[1] - A[1]) * (B[0] - A[0]) - (B[1] - A[1]) * (C[0] - A[0])

        def segments_intersect(p1, p2, p3, p4):
            """Check if segment (p1, p2) intersects segment (p3, p4)."""
            d1 = ccw(p3, p4, p1)
            d2 = ccw(p3, p4, p2)
            d3 = ccw(p1, p2, p3)
            d4 = ccw(p1, p2, p4)

            # Standard orientation test (general case).
            if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
                (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
            ):
                return True

            # Collinear overlaps treated as intersections.
            if (
                abs(d1) < 1e-12
                and min(p3[0], p4[0]) <= p1[0] <= max(p3[0], p4[0])
                and min(p3[1], p4[1]) <= p1[1] <= max(p3[1], p4[1])
            ):
                return True
            if (
                abs(d2) < 1e-12
                and min(p3[0], p4[0]) <= p2[0] <= max(p3[0], p4[0])
                and min(p3[1], p4[1]) <= p2[1] <= max(p3[1], p4[1])
            ):
                return True
            if (
                abs(d3) < 1e-12
                and min(p1[0], p2[0]) <= p3[0] <= max(p1[0], p2[0])
                and min(p1[1], p2[1]) <= p3[1] <= max(p1[1], p2[1])
            ):
                return True
            if (
                abs(d4) < 1e-12
                and min(p1[0], p2[0]) <= p4[0] <= max(p1[0], p2[0])
                and min(p1[1], p2[1]) <= p4[1] <= max(p1[1], p2[1])
            ):
                return True

            return False

        poly = onion_polygon(close=False)
        n = len(poly)
        intersection_count = 0

        for i in range(n):
            for j in range(i + 2, n):
                # Skip adjacent segments: (i, i+1) is adjacent to (i+1, i+2) and (i-1, i).
                if j == (i + 1) % n or i == (j + 1) % n:
                    continue
                # Wrap around for the closed ring.
                seg1_start = poly[i]
                seg1_end = poly[(i + 1) % n]
                seg2_start = poly[j]
                seg2_end = poly[(j + 1) % n]

                if segments_intersect(seg1_start, seg1_end, seg2_start, seg2_end):
                    intersection_count += 1

        assert intersection_count == 0

    def test_oblate_wider_than_tall(self):
        """(x.max - x.min) > (y.max - y.min)."""
        poly = onion_polygon()
        x = poly[:, 0]
        y = poly[:, 1]
        width = x.max() - x.min()
        height = y.max() - y.min()
        assert width > height

    def test_stem_nub_present(self):
        """y.max() > b + 0.5*stem_height, and the x at argmax(y) is centered (abs(x) < 0.15)."""
        b = 0.70
        stem_height = 0.08
        poly = onion_polygon(b=b, stem_height=stem_height)
        y = poly[:, 1]
        x = poly[:, 0]
        max_y = y.max()
        # Nub should push max above b.
        assert max_y > b + 0.5 * stem_height
        # Nub should be centered at x=0.
        x_at_max_y = x[np.argmax(y)]
        assert abs(x_at_max_y) < 0.15

    def test_root_plate_dimple(self):
        """Root dimple: center y > -b + 0.5*root_depth, and global minimum is off-center."""
        b = 0.70
        root_depth = 0.04
        root_width_frac = 0.30
        a = 1.0
        poly = onion_polygon(a=a, b=b, root_depth=root_depth, root_width_frac=root_width_frac)
        y = poly[:, 1]
        x = poly[:, 0]

        # Bottom points in the dimple region: y < 0 and |x| < 0.05 (center).
        center_mask = (y < 0) & (np.abs(x) < 0.05)
        if center_mask.any():
            center_max_y = y[center_mask].max()
            # Dimple should indent upward by at least half.
            assert center_max_y > -b + 0.5 * root_depth

        # Global minimum should be off-center (not at the dimple).
        global_min_y = y.min()
        x_at_min = x[np.argmin(y)]
        assert global_min_y < (center_max_y if center_mask.any() else -b)
        # Off-center means not in the narrow dimple region.
        assert abs(x_at_min) > 0.05

    def test_deterministic(self):
        """Two calls with identical args are np.array_equal."""
        poly1 = onion_polygon(n=150, a=1.2, b=0.6, stem_height=0.1, stem_width=0.2)
        poly2 = onion_polygon(n=150, a=1.2, b=0.6, stem_height=0.1, stem_width=0.2)
        assert np.array_equal(poly1, poly2)
