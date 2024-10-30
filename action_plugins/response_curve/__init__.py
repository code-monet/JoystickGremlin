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

from PySide6 import QtCore, QtQml
from PySide6.QtCore import Property, Signal

from action_plugins.description import DescriptionData
from gremlin import event_handler, util
from gremlin.base_classes import AbstractActionData, AbstractFunctor, \
    DataCreationMode, Value
from gremlin.error import GremlinError
from gremlin.profile import Library
from gremlin.types import ActionProperty, InputType, PropertyType

from gremlin.ui.action_model import SequenceIndex, ActionModel

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


class ResponseCurveModel(ActionModel):

    # Signal emitted when the description variable's content changes
    changed = Signal()

    def __init__(
            self,
            data: AbstractActionData,
            binding_model: InputItemBindingModel,
            action_index: SequenceIndex,
            parent_index: SequenceIndex,
            parent: QtCore.QObject
    ):
        super().__init__(data, binding_model, action_index, parent_index, parent)

    def _qml_path_impl(self) -> str:
        return "file:///" + QtCore.QFile(
            "core_plugins:response_curve/ResponseCurveAction.qml"
        ).fileName()

    def _icon_string_impl(self) -> str:
        return ResponseCurve.icon

    @Property(Deadzone, notify=changed)
    def deadzone(self) -> Deadzone:
        return Deadzone(self._data, self)



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
