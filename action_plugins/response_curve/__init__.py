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

from __future__ import annotations

from typing import Any, List, Optional, TYPE_CHECKING
from xml.etree import ElementTree

from PySide6 import QtCore, QtGui, QtQml
from PySide6.QtCore import Property, Signal, Slot, QCborTag

from action_plugins.description import DescriptionData
from gremlin import event_handler, spline, util
from gremlin.base_classes import AbstractActionData, AbstractFunctor, \
    DataCreationMode, Value
from gremlin.error import GremlinError
from gremlin.profile import Library
from gremlin.types import ActionProperty, InputType, PropertyType

from gremlin.ui.action_model import SequenceIndex, ActionModel
from gremlin.util import clamp

if TYPE_CHECKING:
    from gremlin.ui.profile import InputItemBindingModel


QML_IMPORT_NAME = "Gremlin.ActionPlugins"
QML_IMPORT_MAJOR_VERSION = 1


class ResponseCurveFunctor(AbstractFunctor):

    """Implements the function executed of the Description action at runtime."""

    def __init__(self, action: DescriptionData):
        super().__init__(action)

    def __call__(
        self,
        event: event_handler.Event,
        value: Value
    ) -> None:
        """Processes the provided event.

        Args:
            event: the input event to process
            value: the potentially modified input value
        """
        pass



@QtQml.QmlElement
class Deadzone(QtCore.QObject):

    changed = Signal()
    lowModified = Signal(float)
    centerLowModified = Signal(float)
    centerHighModified = Signal(float)
    highModified = Signal(float)

    def __init__(self, data: AbstractActionData, parent=QtCore.QObject):
        super().__init__(parent)

        self._data = data

    def _get_value(self, index: int) -> float:
        return self._data.deadzone[index]

    def _set_value(self, index: int, value: float) -> None:
        lookup = {
            0: self.lowModified,
            1: self.centerLowModified,
            2: self.centerHighModified,
            3: self.highModified
        }
        if value != self._data.deadzone[index]:
            self._data.deadzone[index] = value
            print(self._data.deadzone)
            lookup[index].emit(value)

    low = Property(
        float,
        fget=lambda cls: Deadzone._get_value(cls, 0),
        fset=lambda cls, value: Deadzone._set_value(cls, 0, value),
        notify=lowModified
    )

    centerLow = Property(
        float,
        fget=lambda cls: Deadzone._get_value(cls, 1),
        fset=lambda cls, value: Deadzone._set_value(cls, 1, value),
        notify=centerLowModified
    )

    centerHigh = Property(
        float,
        fget=lambda cls: Deadzone._get_value(cls, 2),
        fset=lambda cls, value: Deadzone._set_value(cls, 2, value),
        notify=centerHighModified
    )

    high = Property(
        float,
        fget=lambda cls: Deadzone._get_value(cls, 3),
        fset=lambda cls, value: Deadzone._set_value(cls, 3, value),
        notify=highModified
    )


class ControlPoint(QtCore.QObject):

    changed = Signal()

    def __init__(
            self,
            center: Optional[QtCore.QPointF]=None,
            handle_left: Optional[QtCore.QPointF]=None,
            handle_right: Optional[QtCore.QPointF]=None,
            parent: Optional[QtCore.QtCore.QPointF]=None
    ):
        super().__init__(parent)
        self._center = center
        self._handle_left = handle_left
        self._handle_right = handle_right

    @Property(QtCore.QPointF, notify=changed)
    def center(self) -> QtCore.QPointF:
        return self._center

    @Property(QtCore.QPointF, notify=changed)
    def handleLeft(self) -> QtCore.QPointF:
        return self._handle_left

    @Property(QtCore.QPointF, notify=changed)
    def handleRight(self) -> QtCore.QPointF:
        return self._handle_right

    @Property(bool, notify=changed)
    def hasHandles(self) -> bool:
        return self._handle_left is not None or self._handle_right is not None


class ResponseCurveModel(ActionModel):

    changed = Signal()
    deadzoneChanged = Signal()
    curveChanged = Signal()
    controlPointChanged = Signal()

    def __init__(
            self,
            data: AbstractActionData,
            binding_model: InputItemBindingModel,
            action_index: SequenceIndex,
            parent_index: SequenceIndex,
            parent: QtCore.QObject
    ):
        super().__init__(data, binding_model, action_index, parent_index, parent)

        self.widget_size = 400

    def _qml_path_impl(self) -> str:
        return "file:///" + QtCore.QFile(
            "core_plugins:response_curve/ResponseCurveAction.qml"
        ).fileName()

    def _icon_string_impl(self) -> str:
        return ResponseCurve.icon

    @Property(Deadzone, notify=deadzoneChanged)
    def deadzone(self) -> Deadzone:
        return Deadzone(self._data, self)

    @Slot(float, float)
    def addControlPoint(self, x: float, y: float) -> None:
        self._data.curve.add_control_point(
            clamp(x, -1.0, 1.0),
            clamp(y, -1.0, 1.0)
        )
        self.controlPointChanged.emit()
        self.curveChanged.emit()

    @Slot(float, float, int)
    def setControlPoint(self, x: float, y: float, idx: int) -> None:
        points = self._data.curve.control_points()
        points[idx].x = x
        points[idx].y = y
        if self._data.curve.is_symmetric:
            points[len(points)-idx-1].x = -x
            points[len(points)-idx-1].y = -y
        self._data.curve.fit()
        self.curveChanged.emit()

    @Slot(float, float, int, str)
    def setControlHandle(self, x: float, y: float, idx: int, handle: str) -> None:
        points = self._data.curve.control_points()
        control = points[idx]
        if handle == "left":
            control.handle_left.x = x
            control.handle_left.y = y
        elif handle == "right":
            control.handle_right.x = x
            control.handle_right.y = y
        self._data.curve.fit()
        self.curveChanged.emit()

    @Slot(int)
    def setWidgetSize(self, size: int) -> None:
        self.widget_size = size
        self.curveChanged.emit()
        self.controlPointChanged.emit()

    @Slot()
    def invertCurve(self) -> None:
        self._data.curve.invert()
        self.curveChanged.emit()
        self.controlPointChanged.emit()

    def _get_line_points(self) -> List[QtCore.QPointF]:
        points = []
        scaling_factor = self.widget_size / 2.0
        for i in range(-100, 101):
            points.append(QtCore.QPointF(
                (i / 100.0 + 1) * scaling_factor,
                self.widget_size - (self._data.curve(i / 100.0) + 1) * scaling_factor
            ))
        return points

    def _get_control_points(self) -> List[ControlPoint]:
        if type(self._data.curve) in [spline.PiecewiseLinear, spline.CubicSpline]:
            return [
                ControlPoint(center=QtCore.QPointF(p.x, p.y), parent=self) for
                p in self._data.curve.control_points()
            ]
        elif isinstance(self._data.curve, spline.CubicBezierSpline):
            points = []
            for p in self._data.curve.control_points():
                center = QtCore.QPointF(p.center.x, p.center.y)
                left = None
                if p.handle_left is not None:
                    left = QtCore.QPointF(p.handle_left.x, p.handle_left.y)
                right = None
                if p.handle_right is not None:
                    right = QtCore.QPointF(p.handle_right.x, p.handle_right.y)
                points.append(ControlPoint(center, left, right, self))
            return points
        else:
            raise GremlinError(
                f"Invalid curve type encountered {str(type(self._data.curve))}"
            )

    def _get_is_symmetric(self) -> bool:
        return self._data.curve.is_symmetric

    def _set_is_symmetric(self, is_symmetric: bool) -> None:
        if self._data.curve.is_symmetric != is_symmetric:
            self._data.curve.is_symmetric = is_symmetric
            self.curveChanged.emit()
            self.controlPointChanged.emit()
            self.changed.emit()

    def _get_curve_type(self) -> str:
        lookup = {
            spline.PiecewiseLinear: "Piecewise Linear",
            spline.CubicSpline: "Cubic Spline",
            spline.CubicBezierSpline: "Cubic Bezier Spline"
        }
        return lookup[type(self._data.curve)]

    def _set_curve_type(self, value: str) -> None:
        lookup = {
            "Piecewise Linear": spline.PiecewiseLinear,
            "Cubic Spline": spline.CubicSpline,
            "Cubic Bezier Spline": spline.CubicBezierSpline
        }
        curve_type = lookup[value]
        if curve_type != type(self._data.curve):
            self._data.curve = curve_type()
            self.curveChanged.emit()
            self.controlPointChanged.emit()

    linePoints = Property(
        list,
        fget=_get_line_points,
        notify=curveChanged
    )

    controlPoints = Property(
        list,
        fget=_get_control_points,
        notify=controlPointChanged
    )

    isSymmetric = Property(
        bool,
        fget=_get_is_symmetric,
        fset=_set_is_symmetric,
        notify=changed
    )

    curveType = Property(
        str,
        fget=_get_curve_type,
        fset=_set_curve_type,
        notify=curveChanged
    )


class ResponseCurveData(AbstractActionData):

    """Model of a description action."""

    version = 1
    name = "Response Curve"
    tag = "response-curve"
    icon = "\uF18C"

    functor = ResponseCurveFunctor
    model = ResponseCurveModel

    properties = [
        ActionProperty.ActivateDisabled,
    ]
    input_types = [
        InputType.JoystickAxis,
    ]

    def __init__(
            self,
            behavior_type: InputType=InputType.JoystickAxis
    ):
        super().__init__(behavior_type)

        # Model variables
        self.deadzone = [-1.0, 0.0, 0.0, 1.0]
        self.curve = spline.PiecewiseLinear()
        # self.curve = spline.CubicSpline([(-1.0, -1.0), (-0.4, -0.2), (0.2, 0.7), (1.0, 1.0)])

    def _from_xml(self, node: ElementTree.Element, library: Library) -> None:
        self._id = util.read_action_id(node)

    def _to_xml(self) -> ElementTree.Element:
        node = util.create_action_node(ResponseCurveData.tag, self._id)

        return node

    def is_valid(self) -> bool:
        return True

    def _valid_selectors(self) -> List[str]:
        return []

    def _get_container(self, selector: str) -> List[AbstractActionData]:
        raise GremlinError(f"{self.name}: has no containers")

    def _handle_behavior_change(
        self,
        old_behavior: InputType,
        new_behavior: InputType
    ) -> None:
        pass


create = ResponseCurveData
