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

from typing import List, Optional, Tuple, TYPE_CHECKING

from PySide6 import QtCore, QtQml
from PySide6.QtCore import Property, Signal, Slot

from gremlin import input_cache
from gremlin.error import MissingImplementationError, GremlinError
from gremlin.plugin_manager import PluginManager
from gremlin.profile import Library
from gremlin.signal import signal
from gremlin.types import ActionActivationMode, InputType

if TYPE_CHECKING:
    from gremlin.base_classes import AbstractActionData
    from gremlin.ui.profile import InputItemBindingModel


QML_IMPORT_NAME = "Gremlin.Profile"
QML_IMPORT_MAJOR_VERSION = 1


class SequenceIndex:

    def __init__(
            self,
            parent_index: int | None,
            container_name: str | None,
            index: int,
    ):
        """Creates a new action index instance.
        This models the QModelIndex class.
        Args:
            parent_index: index assigned to the parent action
            container_name: name of the parent's container
            index: index assigned to this action
        """
        self._parent_index = parent_index
        self._container_name = container_name
        self._index = index

    @property
    def index(self) -> int:
        return self._index

    @property
    def parent_index(self) -> int:
        return self._parent_index

    @property
    def container_name(self) -> str:
        return self._container_name


@QtQml.QmlElement
class ActionModel(QtCore.QObject):

    """QML model representing a single action instance."""

    actionChanged = Signal()
    actionLabelChanged = Signal()

    def __init__(
            self,
            data: AbstractActionData,
            binding_model: InputItemBindingModel,
            action_index: SequenceIndex,
            parent_index: SequenceIndex,
            parent: QtCore.QObject
    ):
        super().__init__(parent)

        self._data = data
        self._binding_model = binding_model
        self._sequence_index = action_index
        self._parent_sequence_index = parent_index

    def _qml_path_impl(self) -> str:
        raise MissingImplementationError(
            "ActionModel._qml_path_impl not implemented in subclass"
        )

    @property
    def input_type(self) -> InputType:
        return self._binding_model.behavior_type

    @property
    def library(self) -> Library:
        return self._binding_model.input_item_binding.library

    @Property(type=InputType, notify=actionChanged)
    def inputType(self) -> InputType:
        return self._binding_model.behavior_type

    @Property(type="QVariant", notify=actionChanged)
    def actionData(self) -> AbstractActionData:
        return self._data

    @Property(type=str, notify=actionChanged)
    def name(self) -> str:
        return self._data.name

    @Property(type=str, notify=actionChanged)
    def qmlPath(self) -> str:
        return self._qml_path_impl()

    @Property(type=str, constant=True)
    def icon(self) -> str:
        return self._data.icon

    @Property(type=str, notify=actionChanged)
    def id(self) -> str:
        return str(self._data.id)

    @Property(type=int, notify=actionChanged)
    def sequenceIndex(self) -> int:
        return self._sequence_index.index

    @Property(type=str, notify=actionChanged)
    def rootActionId(self) -> str:
        return str(self._binding_model.root_action.id)

    @Property(type=bool, notify=actionChanged)
    def lastInContainer(self) -> bool:
        return self._binding_model.is_last_action_in_container(
            self._sequence_index
        )

    @Property(type=bool, constant=True)
    def canChangeActivation(self) -> bool:
        return self._data.activation_mode != ActionActivationMode.Disallowed

    @Slot(str, result=list)
    def getActions(self, selector: str) -> List[ActionModel]:
        """Returns the collection of actions corresponding to the selector.

        Args:
            selector: name of the container to return

        Returns:
            List of actions corresponding to the given container
        """
        return self._binding_model.get_child_actions(
            self._sequence_index,
            selector
        )

    @Slot(str, str)
    def appendAction(self, action_name: str, selector: str) -> None:
        """Adds a new action to the end of the specified container.

        Args:
            action_name: name of the action to add
            selector: name of the container into which to add the action
        """
        action = PluginManager().create_instance(
            action_name,
            self._binding_model.behavior_type
        )
        self._data.insert_action(action, selector)
        self._binding_model.sync_data()

    @Slot(int, int, str)
    def dropAction(self, source: int, target: int, method: str) -> None:
        """Handles dropping an action on a UI item.

        Args:
            source: sequence id of the acion being dropped
            target: sequence id of the action on which the source is dropped
            method: type of drop action to perform
        """
        # Force a UI refresh without performing any model changes if both
        # source and target item are identical, i.e. an invalid drag&drop
        if source == target:
            self._binding_model.sync_data()
            return

        if method == "append":
            self._append_drop_action(source, target)
        else:
            self._append_drop_action(source, target, method)

        if target == 0:
            signal.reloadCurrentInputItem.emit()

    @Slot(int)
    def removeAction(self, index: int) -> None:
        """Removes the given action from the specified container.

        Args:
            index: sequence index corresponding to the action to remove
        """
        self._binding_model.remove_action(index)

    @property
    def action_data(self) -> AbstractActionData:
        return self._data

    @property
    def sequence_index(self) -> SequenceIndex:
        return self._sequence_index

    @property
    def parent_sequence_index(self) -> SequenceIndex:
        return self._parent_sequence_index

    def _get_action_label(self) -> str:
        return self._data.action_label

    def _set_action_label(self, value: str) -> None:
        if value != self._data.action_label:
            self._data.action_label = value
            self.actionChanged.emit()
            # If the label of a root action is changed update the input button
            # as well as those labels are displayed on it
            if self._data == self._binding_model.root_action:
                signal.inputItemChanged.emit(
                    self._binding_model.parent().enumeration_index
                )

    def _get_activate_on_press(self) -> bool:
        return self._activation_to_tuple()[0]

    def _set_activate_on_press(self, value: bool) -> None:
        state = self._activation_to_tuple()
        if state[0] != value:
            self._tuple_to_activation((value, state[1]))

    def _get_activate_on_release(self) -> bool:
        return self._activation_to_tuple()[1]

    def _set_activate_on_release(self, value: bool) -> None:
        state = self._activation_to_tuple()
        if state[1] != value:
            self._tuple_to_activation((state[0], value))

    def _activation_to_tuple(self) -> Tuple[bool, bool]:
        """Returns a tuple representing the activation behavior state.

        Returns:
            Tuple indicating which activation behaviors are enabled
        """
        on_press = self._data.activation_mode in \
                   [ActionActivationMode.Both, ActionActivationMode.Press]
        on_release = self._data.activation_mode in \
            [ActionActivationMode.Both, ActionActivationMode.Release]
        return (on_press, on_release)

    def _tuple_to_activation(self, state: Tuple[bool, bool]) -> None:
        """Sets the activation state based on the state tuple.

        Args:
            Tuple containing the state of the press and releaes activations
        """
        match state:
            case (False, False):
                self._data.activation_mode = ActionActivationMode.Deactivated
            case (True, False):
                self._data.activation_mode = ActionActivationMode.Press
            case (False, True):
                self._data.activation_mode = ActionActivationMode.Release
            case (True, True):
                self._data.activation_mode = ActionActivationMode.Both

    def _append_drop_action(
            self,
            source_sidx: int,
            target_sidx: int,
            container: Optional[str]=None
        ) -> None:
        """Positions the source node after the target node.

        Args:
            source_sidx: sequence index of the source action
            target_sidx: sequence index of the target action
            container: name of the container to insert the action into
        """
        try:
            if container is None:
                self._binding_model.move_action(source_sidx, target_sidx)
            else:
                self._binding_model.move_action(source_sidx, target_sidx, container)
        except GremlinError:
            signal.reloadUi.emit()

    @Property(type=list, notify=actionChanged)
    def compatibleActions(self) -> List[str]:
        action_list = PluginManager().type_action_map[
            self._binding_model.behavior_type
        ]
        action_list = [entry for entry in action_list if entry.tag != "root"]
        return [a.name for a in sorted(action_list, key=lambda x: x.name)]

    actionLabel = Property(
        str,
        fget=_get_action_label,
        fset=_set_action_label,
        notify=actionChanged
    )

    activateOnPress = Property(
        bool,
        fget=_get_activate_on_press,
        fset=_set_activate_on_press,
        notify=actionChanged
    )

    activateOnRelease = Property(
        bool,
        fget=_get_activate_on_release,
        fset=_set_activate_on_release,
        notify=actionChanged
    )
