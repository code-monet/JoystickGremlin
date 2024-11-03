# -*- coding: utf-8; -*-

# Copyright (C) 2015 - 2024 Lionel Ott
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import abc
import collections
from typing import List, Tuple

from gremlin import util


# Typing alias
type CoordinateList = List[Tuple[float, float]]


class Point2D:

    def __init__(self, x, y):
        self.x = x
        self.y = y


class AbstractCurve(abc.ABC):

    """Base class for all curves, providing a common interface."""

    def __init__(self):
        pass

    @abc.abstractmethod
    def control_points(self) -> List:
        """Returns the list of all control points.

        Returns:
            List of all control points.
        """
        pass

    @abc.abstractmethod
    def add_control_point(self, x: float, y: float) -> None:
        """Adds a new control point to the curve.

        Args:
            x: x-coordinate of the control point
            y: y-coordinate of the control point
        """
        pass

    @abc.abstractmethod
    def __call__(self, x: float) -> float:
        """Evaluates the curve at the given location.

        Args:
            x: location at which to evaluate the curve

        Returns:
            Function value of the curve at the given location
        """
        pass



class PiecewiseLinear(AbstractCurve):

    def __init__(self, points: CoordinateList):
        """Creates a piece wise linear curve.

        Args:
            points: collection of (x, y) coordinates defining the curve
        """
        self.points = [Point2D(pt[0], pt[1]) for pt in
                       sorted(points, key=lambda pt: pt[0])]

    def control_points(self) -> List:
        return self.points

    def add_control_point(self, x: float, y: float) -> None:
        self.points.append(Point2D(x, y))
        self.points = sorted(self.points, key=lambda pt: pt.x)

    def __call__(self, x: float) -> float:
        """Returns the linearly interpolated value for the given position.

        Args:
            x the location at which to evaluate the spline

        Returns:
            linearly interpolated value for the provided position
        """
        x = util.clamp(x, -1.0, 1.0)

        if x <= self.points[0].x:
            return self.points[0].y
        elif x >= self.points[-1].x:
            return self.points[-1].y
        else:
            for i in range(len(self.points) - 1):
                a = self.points[i]
                b = self.points[i + 1]
                if a.x <= x < b.x:
                    return a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x)


class CubicSpline:

    """Creates a new cubic spline based interpolation.

    The methods requires a set of control points which are used to
    create a C2 spline which passes through all of them.
    """

    def __init__(self, points):
        """Creates a new CubicSpline object.

        :param points the set of (x, y) control points
        """
        # Order the points by increasing x coordinate to guarantee proper
        # functioning of the spline code
        ordered_points = sorted(points, key=lambda x: x[0])

        self.x = [v[0] for v in ordered_points]
        self.y = [v[1] for v in ordered_points]
        self.z = [0] * len(points)

        self._fit()

    def _fit(self):
        """Computes the second derivatives for the control points."""
        n = len(self.x)-1

        if n < 2:
            return

        h = [0] * n
        b = [0] * n
        u = [0] * n
        v = [0] * n

        for i in range(n):
            h[i] = self.x[i+1] - self.x[i]
            b[i] = (self.y[i+1] - self.y[i]) / h[i]

        u[1] = 2 * (h[0] + h[1])
        v[1] = 6 * (b[1] - b[0])
        for i in range(2, n):
            u[i] = 2 * (h[i] + h[i-1]) - h[i-1]**2 / u[i-1]
            v[i] = 6 * (b[i] - b[i-1]) - (h[i-1] * v[i-1]) / u[i-1]

        self.z[n] = 0.0
        for i in range(n-1, 0, -1):
            self.z[i] = (v[i] - h[i] * self.z[i+1]) / u[i]
        self.z[0] = 0.0

    def __call__(self, x):
        """Returns the function value at the desired position.

        :param x the location at which to evaluate the function
        :return function value at the provided position
        """
        n = len(self.x)

        i = 0
        for i in range(n-1):
            if self.x[i] <= x <= self.x[i+1]:
                break

        h = self.x[i+1] - self.x[i]
        tmp = (self.z[i] / 2.0) + (x - self.x[i]) * \
            (self.z[i+1] - self.z[i]) / (6 * h)
        tmp = -(h/6.0) * (self.z[i+1] + 2 * self.z[i]) + \
            (self.y[i+1] - self.y[i]) / h + (x - self.x[i]) * tmp

        return self.y[i] + (x - self.x[i]) * tmp


class CubicBezierSpline:

    """Implementation of cubic Bezier splines."""

    def __init__(self, points):
        """Creates a new CubicBezierSpline object.

        :param points the set of (x, y) knots and control points
        """
        self.x = [v[0] for v in points]
        self.y = [v[1] for v in points]

        self.knots = [pt for pt in points[::3]]

        self._lookup = []
        self._generate_lookup()

    def _generate_lookup(self):
        """Generates the lookup table mapping x to t values."""
        assert len(self.x) == len(self.y)
        assert (len(self.x) - 4) % 3 == 0

        # Iterate over all spline groups part of the curve
        for i in range(int((len(self.x) - 4) / 3) + 1):
            offset = i * 3
            points = [
                Point2D(self.x[offset], self.y[offset]),
                Point2D(self.x[offset + 1], self.y[offset + 1]),
                Point2D(self.x[offset + 2], self.y[offset + 2]),
                Point2D(self.x[offset + 3], self.y[offset + 3])
            ]

            # Get t -> coordinate mappings
            step_size = 1.0 / 100
            self._lookup.append([])
            for j in range(0, 101):
                t = j * step_size
                self._lookup[-1].append((t, self._value_at_t(points, t)))

    def _value_at_t(self, points, t):
        """Returns the x and y coordinate for the spline at time t.

        :param points the control points of the curve
        :param t the time point
        :return x and y coordinate corresponding to the given time point
        """
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        return Point2D(
            points[0].x * mt3
                + 3 * points[1].x * mt2 * t
                + 3 * points[2].x * mt * t2
                + points[3].x * t3,
            points[0][1] * mt3
                + 3 * points[1].y * mt2 * t
                + 3 * points[2].y * mt * t2
                + points[3].y * t3
        )

    def __call__(self, x):
        """Returns the function value at the desired position.

        :param x the location at which to evaluate the function
        :return function value at the provided position
        """
        # Ensure we have a valid value for x
        x = gremlin.util.clamp(x, -1.0, 1.0)

        # Determine spline group to use
        index = 0
        if self.knots[0][0] > x:
            index = 0
        elif self.knots[-1][0] <= x:
            index = len(self._lookup)-1
        else:
            segment_count = int((len(self.x) - 4) / 3) + 1
            for i in range(segment_count):
                offset = i * 3
                if self.x[offset] <= x <= self.x[offset+3]:
                    index = i
                    break

        # Linearly interpolate the lookup table data
        interval = [0, len(self._lookup[index])]
        searching = True
        while searching:
            distance = interval[1] - interval[0]
            if distance == 1:
                searching = False
                break

            center_index = interval[0] + int(distance / 2.0)
            if self._lookup[index][center_index][1][0] < x:
                interval[0] = center_index
            else:
                interval[1] = center_index

        low = self._lookup[index][interval[0]][1]
        high = self._lookup[index][interval[1]][1]

        return low.y + (x - low.x) * ((high.y - low.y) / (high.x - low.x))
