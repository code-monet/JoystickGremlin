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

import json
from json.decoder import JSONDecodeError
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from PySide6 import QtCharts, QtCore, QtQml
from PySide6.QtCore import Property, Signal, Slot

import dill

from gremlin import common, event_handler, joystick_handling, shared_state
from gremlin.error import GremlinError
from gremlin.intermediate_output import IntermediateOutput
from gremlin.types import InputType, PropertyType
import gremlin.util as util
from gremlin.common import SingletonDecorator
from gremlin.config import Configuration


QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1


class DeviceMapping:

    def __init__(self, input_map: Dict[str, Any]) -> None:
        self._input_map = input_map

    def input_name(self, input_name: str) -> str:
        """

        Args:
            input_name - name of the original input,
                         e.g.: "Axis 1" or "Button 1" or "Hat 1"

        Returns:
            The input name based on the global configuration option
            and availability of information about the input in
            the device device mapping.

            If a device exists in the device database and it's mapping or
            the input are not defined, input_name() returns a default
            input name, e.g. Axis 1 or Button 1 or Hat 1.

            Note that some devices have configurable number of buttons and/or axes
            so adjusting device database information might be required in the future.
        """
        input_name_display_mode = Configuration().value(
            "global", "input-names", "input-name-display-mode"
            )

        if (
            input_name_display_mode == "Numerical" or
            input_name not in self._input_map
        ):
            return input_name

        db_input_name = self._input_map[input_name].strip()

        # return default input name if input is defined, but empty
        if len(db_input_name) == 0:
            return input_name

        # return configured input name style
        if input_name_display_mode == "Numerical + Label":
            return f"{input_name} - {db_input_name}"
        if input_name_display_mode == "Label":
            return db_input_name



@SingletonDecorator
class DeviceDatabase:
    """Provides button/axis/hat to name mapping for known devices"""

    def __init__(self) -> None:
        self._load()

    def _load(self) -> None:

        db_file = util.resource_path("device_db.json")
        if not util.file_exists_and_is_accessible(db_file):
            return

        load_successful = False
        json_data = {}
        try:
            json_data = json.load(open(db_file))
            load_successful = True
        except JSONDecodeError as error:
            logging.getLogger("system").error(
                    f"There was an error loading {db_file}: {error}")

        parser_successful = self._parse_device_db(json_data)

        if load_successful and parser_successful:
            self._device_db = json_data
        else:
            self._device_db = {"revision": 0, "devices": [], "mapping": {}}

    def _parse_device_db(self, device_db: Dict[str, Any]) -> bool:
        """
        Parse device_db to make sure it has a valid structure.

        This piece could be refactored with JSON schema validation code,
        if need be in the future.
        """
        parser_successful = True

        # check top structure: devices and mappings
        if (not(
            isinstance(device_db.get("mapping", None), dict) and
            isinstance(device_db.get("devices", None), list))
            ):
            logging.getLogger("system").error(
                    "DeviceDatabase is corrupt and/or is missing mapping or device information.")
            parser_successful = False

        # check that devices contain mandatory fields
        device_count = 0
        for dev in device_db["devices"]:
            if not ("product_id" in dev and
                    "vendor_id" in dev and
                    "mapping" in dev
                    ):
                logging.getLogger("system").error(
                    f"DeviceDatabase device structure is corrupt for device {dev}")
                parser_successful = False
            else:
                device_count += 1

        # don't parse mapping, just make sure there is at least 1 mapping
        mapping_count = len(device_db["mapping"])

        if parser_successful and device_count > 0 and mapping_count > 0:
            return True

        return False

    def _device_matches(self, dev: Dict[str, Any], device: dill.DeviceSummary) -> bool:
        return dev["product_id"] == device.product_id and dev["vendor_id"] == device.vendor_id

    def get_mapping(self, device: dill.DeviceSummary) -> DeviceMapping | None:
        """Returns: DeviceMapping object for the detected device"""
        if device is None:
            return None

        for dev in self._device_db["devices"]:
            if self._device_matches(dev, device):
                if dev["mapping"] not in self._device_db["mapping"]:
                    logging.getLogger("system").warning(
                        f"Unable to find device mapping for product_id={device.product_id} "
                        f"vendor_id={device.vendor_id}")
                    return None

                return DeviceMapping(self._device_db["mapping"][dev["mapping"]])

        logging.getLogger("system").warning(
            f"Unsupported device product_id={device.product_id} "
            f"vendor_id={device.vendor_id}")

        return None


@QtQml.QmlElement
class InputIdentifier(QtCore.QObject):

    """Stores the identifier of a single input item."""

    changed = Signal()

    def __init__(
            self,
            device_guid: uuid.UUID | None=None,
            input_type: InputType | None=None,
            input_id: int | None=None,
            parent=None
    ):
        super().__init__(parent)

        self.device_guid = device_guid
        self.input_type = input_type
        self.input_id = input_id

    @Property(str, notify=changed)
    def label(self) -> str:
        if self.isValid:
            dev_name = dill.DILL.get_device_name(
                dill.GUID.from_uuid(self.device_guid)
            )
            return f"{dev_name} - " + \
                   f"{InputType.to_string(self.input_type).capitalize()} " + \
                   f"{self.input_id}"
        else:
            return "No input"

    @Property(bool, notify=changed)
    def isValid(self) -> bool:
        return self.device_guid is not None \
            and self.input_type is not None \
            and self.input_id is not None

    def __eq__(self, other: InputIdentifier) -> bool:
        return self.device_guid == other.device_guid and \
            self.input_type == other.input_type and \
            self.input_id == other.input_id


@QtQml.QmlElement
class DeviceListModel(QtCore.QAbstractListModel):

    """Model containing basic information about all connected devices."""

    roles = {
        QtCore.Qt.UserRole + 1: QtCore.QByteArray("name".encode()),
        QtCore.Qt.UserRole + 2: QtCore.QByteArray("axes".encode()),
        QtCore.Qt.UserRole + 3: QtCore.QByteArray("buttons".encode()),
        QtCore.Qt.UserRole + 4: QtCore.QByteArray("hats".encode()),
        QtCore.Qt.UserRole + 5: QtCore.QByteArray("pid".encode()),
        QtCore.Qt.UserRole + 6: QtCore.QByteArray("vid".encode()),
        QtCore.Qt.UserRole + 7: QtCore.QByteArray("guid".encode()),
        QtCore.Qt.UserRole + 8: QtCore.QByteArray("joy_id".encode()),
    }

    role_query = {
        "name": lambda dev: dev.name,
        "axes": lambda dev: dev.axis_count,
        "buttons": lambda dev: dev.button_count,
        "hats": lambda dev: dev.hat_count,
        "pid": lambda dev: "{:04X}".format(dev.product_id),
        "vid": lambda dev: "{:04X}".format(dev.vendor_id),
        "guid": lambda dev: str(dev.device_guid),
        "joy_id": lambda dev: dev.joystick_id,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices = joystick_handling.physical_devices()

        event_handler.EventListener().device_change_event.connect(
            self.update_model
        )

    def update_model(self) -> None:
        """Updates the model if the connected devices change."""
        old_count = len(self._devices)
        self._devices = joystick_handling.joystick_devices()
        new_count = len(self._devices)

        # Remove everything and then add it back to force a model update
        self.rowsRemoved.emit(self.parent(), 0, new_count)
        self.rowsInserted.emit(self.parent(), 0, new_count)

    def rowCount(self, parent:QtCore.QModelIndex=...) -> int:
        return len(self._devices)

    def data(self, index:QtCore.QModelIndex, role:int=...) -> Any:
        if role in DeviceListModel.roles:
            role_name = DeviceListModel.roles[role].data().decode()
            return DeviceListModel.role_query[role_name](
                self._devices[index.row()]
            )
        else:
            return "Unknown"

    def roleNames(self) -> Dict:
        return DeviceListModel.roles

    @Slot(int, result=str)
    def guidAtIndex(self, index: int) -> str:
        if not(0 <= index < len(self._devices)):
            raise GremlinError("Provided index out of range")

        return str(self._devices[index].device_guid)

    def _change_device_type(self, types: str) -> None:
        """Sets which device types are going to be used.

        Valid options are:
        - physical
        - virtual
        - all

        Args:
            types: the type of devices to list
        """
        if types == "physical":
            self._devices = joystick_handling.physical_devices()
        elif types == "virtual":
            self._devices = joystick_handling.vjoy_devices()
        elif types == "all":
            self._devices = joystick_handling.joystick_devices()

        # Remove everything and then add it back to force a model update
        new_count = len(self._devices)
        self.rowsRemoved.emit(self.parent(), 0, new_count)
        self.rowsInserted.emit(self.parent(), 0, new_count)

    deviceType = Property(
        str,
        fset=_change_device_type
    )


@QtQml.QmlElement
class Device(QtCore.QAbstractListModel):

    """Model providing access to information about a single device."""

    roles = {
        QtCore.Qt.UserRole + 1: QtCore.QByteArray("name".encode()),
        QtCore.Qt.UserRole + 2: QtCore.QByteArray("actionCount".encode()),
        QtCore.Qt.UserRole + 3: QtCore.QByteArray("description".encode()),
    }

    deviceChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._device: dill.DeviceSummary | None = None
        self._device_mapping: Dict[str, str] | None = None

    @Slot(int)
    def refreshInput(self, index: int) -> None:
        """Refreshes the input at the given index.

        Args:
            index: linear index of the device's inputs to refresh
        """
        self.beginResetModel()
        self.endResetModel()

    def _get_guid(self) -> str:
        if self._device is None:
            return "Unknown"
        else:
            return str(self._device.device_guid)

    def _set_guid(self, guid: str) -> None:
        if self._device is not None and guid == str(self._device.device_guid):
            return

        self._device = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_str(guid)
        )

        self._device_mapping = DeviceDatabase().get_mapping(self._device)
        self.deviceChanged.emit()
        self.layoutChanged.emit()

    def rowCount(self, parent:QtCore.QModelIndex=...) -> int:
        if self._device is None:
            return 0

        return self._device.axis_count + \
               self._device.button_count + \
               self._device.hat_count

    def data(self, index: QtCore.QModelIndex, role:int=...) -> Any:
        if role not in Device.roles:
            return "Unknown"

        role_name = Device.roles[role].data().decode()
        match role_name:
            case "name":
                return self._name(self._convert_index(index.row()))
            case "actionCount":
                input_info = self._convert_index(index.row())
                # FIXME: retrieve currently selected mode
                return shared_state.current_profile.get_input_count(
                    self._device.device_guid.uuid,
                    input_info[0],
                    input_info[1],
                    "Default"
                )
            case "description":
                input_info = self._convert_index(index.row())
                # FIXME: retrieve currently selected mode
                item = shared_state.current_profile.get_input_item(
                    self._device.device_guid.uuid,
                    input_info[0],
                    input_info[1],
                    "Default"
                )
                if item and len(item.action_sequences) > 0:
                    labels = filter(
                        lambda x: x != "Root",
                        [seq.root_action.action_label for seq in item.action_sequences]
                    )
                    return " / ".join(labels)
                else:
                    return ""

    @Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        """Returns the InputIdentifier for input with the specified index.

        Args:
            index: the index of the input for which to generate the
                InpuIdentifier instance

        Returns:
            An InputIdentifier instance referring to the input item with
            the given index.
        """
        identifier = InputIdentifier(parent=self)
        identifier.device_guid = self._device.device_guid.uuid
        input_info = self._convert_index(index)
        identifier.input_type = input_info[0]
        identifier.input_id = input_info[1]

        return identifier

    def _name(self, identifier: Tuple[InputType, int]) -> str:
        input_name = "{} {:d}".format(
            InputType.to_string(identifier[0]).capitalize(),
            identifier[1]
            )

        if self._device_mapping is not None:
            return self._device_mapping.input_name(input_name)
        else:
            return input_name

    def _convert_index(self, index: int) -> Tuple[InputType, int]:
        axis_count = self._device.axis_count
        button_count = self._device.button_count
        hat_count = self._device.hat_count

        if index < axis_count:
            return (
                InputType.JoystickAxis,
                self._device.axis_map[index].axis_index
            )
        elif index < axis_count + button_count:
            return (
                InputType.JoystickButton,
                index + 1 - axis_count
            )
        else:
            return (
                InputType.JoystickHat,
                index + 1 - axis_count - button_count
            )

    def roleNames(self) -> Dict:
        return Device.roles

    guid = Property(
        str,
        fget=_get_guid,
        fset=_set_guid
    )


@QtQml.QmlElement
class IODeviceManagementModel(QtCore.QAbstractListModel):

    """Model providing information about the intermedia output device."""

    roles = {
        QtCore.Qt.UserRole + 1: QtCore.QByteArray("name".encode()),
        QtCore.Qt.UserRole + 2: QtCore.QByteArray("actionCount".encode()),
        QtCore.Qt.UserRole + 3: QtCore.QByteArray("label".encode()),
    }

    deviceChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._io = IntermediateOutput()

    @Slot(str)
    def createInput(self, type_str: str) -> None:
        self.beginInsertRows(
            QtCore.QModelIndex(),
            self.rowCount(),
            self.rowCount()
        )
        self._io.create(InputType.to_enum(type_str))
        self.endInsertRows()

    @Slot(str, str)
    def changeName(self, old_labele: str, new_label: str) -> None:
        try:
            self._io.set_label(old_labele, new_label)
        except GremlinError:
            # FIXME: Somehow needs to reset the text field to the previous value
            pass

    @Slot(str)
    def deleteInput(self, label: str) -> None:
        self._io.delete(label)
        self.modelReset.emit()

    def _get_guid(self) -> str:
        return str(self._io.device_guid)

    def rowCount(self, parent:QtCore.QModelIndex=...) -> int:
        return len(self._io.labels_of_type())

    def data(self, index: QtCore.QModelIndex, role:int=...) -> Any:
        if role not in IODeviceManagementModel.roles:
            return "Unknown"

        role_name = IODeviceManagementModel.roles[role].data().decode()
        input = self._index_to_input(index.row())
        if role_name == "name":
            return f"{InputType.to_string(input.type).capitalize()} " \
                f"{input.suffix}"
        elif role_name == "actionCount":
            # FIXME: retrieve currently selected moden mae
            return shared_state.current_profile.get_input_count(
                self._io.device_guid,
                input.type,
                input.guid,
                "Default"
            )
        elif role_name == "label":
            return input.label

    @Slot(str, result=List[str])
    def validLabels(self, type_str: str) -> List[str]:
        """Returns a list of valid labels for a given input."""
        type = InputType.to_enum(type_str)
        if len(self._io.keys_of_type([type])) == 0:
            self._io.create(type)
        return self._io.keys_of_type([type])

    @Slot(int, result=InputIdentifier)
    def inputIdentifier(self, index: int) -> InputIdentifier:
        """Returns the InputIdentifier for input with the specified index.

        Args:
            index: the index of the input for which to generate the
                InpuIdentifier instance

        Returns:
            An InputIdentifier instance referring to the input item with
            the given index.
        """
        if index < 0:
            return InputIdentifier(parent=self)

        input = self._index_to_input(index)
        identifier = InputIdentifier(parent=self)
        identifier.device_guid = self._io.device_guid
        identifier.input_type = input.type
        identifier.input_id = input.guid

        return identifier

    def _name(self, identifier: Tuple[InputType, int]) -> str:
        return "{} {:d}".format(
            InputType.to_string(identifier[0]).capitalize(),
            identifier[1]
        )

    def _index_to_input(self, index: int) -> IntermediateOutput.Input:
        """Returns the label corresponding to the provided linear index.

        Args:
            index: the linear index into the list of inputs

        Returns:
            The input corresponding to the given index
        """
        return self._io[self._io.labels_of_type()[index]]

    def roleNames(self) -> Dict:
        return IODeviceManagementModel.roles

    guid = Property(str, fget=_get_guid)


@QtQml.QmlElement
class IODeviceInputsModel(QtCore.QAbstractListModel):

    inputsChanged = Signal()
    selectionChanged = Signal()

    roles = {
        QtCore.Qt.UserRole + 1: QtCore.QByteArray("label".encode()),
        QtCore.Qt.UserRole + 2: QtCore.QByteArray("guid".encode())
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._io = IntermediateOutput()
        self._valid_types = None
        self._current_index = 0
        self._current_guid = None

    def rowCount(self, parent) -> int:
        return len(self._io.labels_of_type(self._valid_types))

    def data(
            self,
            index: QtCore.QModelIndex,
            role: int=QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role not in self.roleNames():
            raise GremlinError(f"Invalid role {role} in IODeviceInputsModel")

        input = self._io.inputs_of_type(self._valid_types)[index.row()]
        if role == QtCore.Qt.UserRole + 1:
            return input.label
        elif role == QtCore.Qt.UserRole + 2:
            return str(input.guid)

    def roleNames(self) -> Dict:
        return IODeviceInputsModel.roles

    def _set_valid_types(self, valid_types: List[str]) -> None:
        type_list = sorted([InputType.to_enum(entry) for entry in valid_types])
        if type_list != self._valid_types:
            self._valid_types = type_list
            self.inputsChanged.emit()

    def _get_current_selection_index(self) -> int:
        return self._current_index

    def _get_current_guid(self) -> str:
        return str(self._current_guid)

    def _set_current_guid(self, guid_str: str) -> None:
        guid = uuid.UUID(guid_str)
        if guid != self._current_guid:
            self._current_guid = guid
            self._current_index = 0
            for i, input in enumerate(self._io.inputs_of_type(self._valid_types)):
                if input.guid == guid:
                    self._current_index = i
            self.selectionChanged.emit()

    validTypes = Property(
        "QVariantList",
        fset=_set_valid_types,
        notify=inputsChanged
    )

    currentSelectionIndex = Property(
        int,
        fget=_get_current_selection_index,
        notify=selectionChanged
    )

    currentGuid = Property(
        str,
        fget=_get_current_guid,
        fset=_set_current_guid,
        notify=selectionChanged
    )


@QtQml.QmlElement
class VJoyDevices(QtCore.QObject):

    """vJoy model used together with the VJoySelector QML.

    The model provides setters and getters for UI selection index values while
    only providing getters for the equivalent id based values. Setting the
    state based on id values is supported via a slot method.
    """

    deviceModelChanged = Signal()
    inputModelChanged = Signal()
    validTypesChanged = Signal()

    vjoyIndexChanged = Signal()
    vjoyIdChanged = Signal()
    inputIdChanged = Signal()
    inputIndexChanged = Signal()
    inputTypeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._devices = sorted(
            joystick_handling.vjoy_devices(),
            key=lambda x: x.vjoy_id
        )

        # Information used to determine what to show in the UI
        self._valid_types = [
            InputType.JoystickAxis,
            InputType.JoystickButton,
            InputType.JoystickHat
        ]
        self._input_items = []
        self._input_data = []

        # Model state information to allow translation between UI index
        # values and model ids
        self._current_vjoy_index = 0
        # Force a refresh of internal state
        self.inputModel
        self._current_input_index = 0
        self._current_input_type = self._input_data[0][0]

        self._is_initialized = False

    def _device_name(self, device) -> str:
        return "vJoy Device {:d}".format(device.vjoy_id)

    def _is_state_valid(self) -> bool:
        """Returns if the state of the object is valid.

        Returns:
            True if the state is valid and consistent, False otherwise
        """
        return self._current_vjoy_index is not None and \
               self._current_input_index is not None and \
               self._current_input_type is not None

    @Slot(int, int, str)
    def setSelection(self, vjoy_id: int, input_id: int, input_type: str) -> None:
        """Sets the internal index state based on the model id data.

        Args:
            vjoy_id: id of the vjoy device
            input_id: id of the input item
            input_type: type of input being selected by the input_id
        """
        # Find vjoy_index corresponding to the provided id
        vjoy_index = -1
        for i, dev in enumerate(self._devices):
            if dev.vjoy_id == vjoy_id:
                vjoy_index = i
                self._set_vjoy_index(i)

        if vjoy_index == -1:
            raise GremlinError(f"Could not find vJoy device with id {vjoy_id}")

        # Find the index corresponding to the provided input_type and input_id
        input_label = common.input_to_ui_string(
            InputType.to_enum(input_type),
            input_id
        )
        try:
            self._set_input_index(self._input_items.index(input_label))
        except ValueError:
            raise GremlinError(f"No input named \"{input_label}\" present")

    @Property(type="QVariantList", notify=deviceModelChanged)
    def deviceModel(self):
        return [self._device_name(dev) for dev in self._devices]

    @Property(type="QVariantList", notify=inputModelChanged)
    def inputModel(self):
        input_count = {
            InputType.JoystickAxis: lambda x: x.axis_count,
            InputType.JoystickButton: lambda x: x.button_count,
            InputType.JoystickHat: lambda x: x.hat_count
        }

        self._input_items = []
        self._input_data = []
        device = self._devices[self._current_vjoy_index]
        # Add items based on the input type
        for input_type in self._valid_types:
            for i in range(input_count[input_type](device)):
                input_id = i+1
                if input_type == InputType.JoystickAxis:
                    input_id = device.axis_map[i].axis_index

                self._input_items.append(common.input_to_ui_string(
                    input_type,
                    input_id
                ))
                self._input_data.append((input_type, input_id))

        return self._input_items

    def _get_valid_types(self) -> List[str]:
        return [InputType.to_string(entry) for entry in self._valid_types]

    def _set_valid_types(self, valid_types: List[str]) -> None:
        type_list = [InputType.to_enum(entry) for entry in sorted(valid_types)]
        if type_list != self._valid_types:
            self._valid_types = type_list

            # When changing the input type attempt to preserve the existing
            # selection if the input type is part of the new set of valid
            # types. If this is not possible, the selection is set to the
            # first entry of the available values.
            old_vjoy_id = self._get_vjoy_id()
            old_input_type = self._get_input_type()

            # Refresh the UI elements
            self.inputModel

            input_label = common.input_to_ui_string(
                InputType.to_enum(old_input_type),
                old_vjoy_id
            )
            if input_label in self._input_items:
                self.setSelection(
                    self._get_vjoy_id(),
                    old_vjoy_id,
                    old_input_type
                )
            else:
                self._current_vjoy_index = 0
                self._current_input_index = 0
                self._current_input_type = self._input_data[0][0]

            # Prevent sending change of input indices and thus changing the
            # model if the model hadn't been initialized yet.
            if self._is_initialized:
                self.inputIndexChanged.emit()
            else:
                self._is_initialized = True
            self.validTypesChanged.emit()
            self.inputModelChanged.emit()

    def _get_vjoy_id(self) -> int:
        if not self._is_state_valid():
            raise GremlinError(
                "Attempted to read from invalid VJoyDevices instance."
            )
        return self._devices[self._current_vjoy_index].vjoy_id

    def _get_vjoy_index(self) -> int:
        if not self._is_state_valid():
            raise GremlinError(
                "Attempted to read from invalid VJoyDevices instance."
            )
        return self._current_vjoy_index

    def _set_vjoy_index(self, index: int) -> None:
        if index != self._current_vjoy_index:
            if index >= len(self._devices):
                raise GremlinError(
                    f"Invalid device index used device with index {index} "
                    f"does not exist"
                )
            self._current_vjoy_index = index
            self.vjoyIndexChanged.emit()
            self.inputModelChanged.emit()

    def _get_input_id(self) -> int:
        if not self._is_state_valid():
            raise GremlinError(
                "Attempted to read from invalid VJoyDevices instance."
            )
        return self._input_data[self._current_input_index][1]

    def _get_input_index(self) -> int:
        if not self._is_state_valid():
            raise GremlinError(
                "Attempted to read from invalid VJoyDevices instance."
            )
        return self._current_input_index

    def _set_input_index(self, index: int) -> None:
        if index != self._current_input_index:
            self._current_input_index = index
            self._current_input_type = self._input_data[index][0]
            self.inputIndexChanged.emit()

    def _get_input_type(self) -> str:
        return InputType.to_string(self._current_input_type)

    validTypes = Property(
        "QVariantList",
        fget=_get_valid_types,
        fset=_set_valid_types,
        notify=validTypesChanged
    )

    vjoyId = Property(
        int,
        fget=_get_vjoy_id,
        notify=vjoyIdChanged
    )

    vjoyIndex = Property(
        int,
        fget=_get_vjoy_index,
        fset=_set_vjoy_index,
        notify=vjoyIndexChanged
    )

    inputId = Property(
        int,
        fget=_get_input_id,
        notify=inputIdChanged
    )

    inputIndex = Property(
        int,
        fget=_get_input_index,
        fset=_set_input_index,
        notify=inputIndexChanged
    )

    inputType = Property(
        str,
        fget=_get_input_type,
        notify=inputTypeChanged
    )


class AbstractDeviceState(QtCore.QAbstractListModel):

    deviceChanged = Signal()

    roles = {
        QtCore.Qt.UserRole + 1: QtCore.QByteArray("identifier".encode()),
        QtCore.Qt.UserRole + 2: QtCore.QByteArray("value".encode()),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        el = event_handler.EventListener()
        el.joystick_event.connect(self._event_callback)

        self._device = None
        self._device_uuid = None
        self._state = []

    def _event_callback(self, event: event_handler.Event):
        if event.device_guid != self._device_uuid:
            return

        self._event_handler_impl(event)

    def _event_handler_impl(self, event: event_handler.Event) -> None:
        raise GremlinError(
            "AbstractDeviceState._event_handler_impl not implemented"
        )

    def _set_guid(self, guid: str) -> None:
        if self._device is not None and guid == str(self._device.device_guid):
            return

        self._device = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_str(guid)
        )
        self._device_uuid = uuid.UUID(guid)
        self._state = []
        self._initialize_state()
        self.deviceChanged.emit()

    def _initilize_state(self) -> None:
        raise GremlinError(
            "AbstractDeviceState._initialize_state not implemented"
        )

    def rowCount(self, parent:QtCore.QModelIndex=...) -> int:
        if self._device is None:
            return 0

        return len(self._state)

    def data(self, index: QtCore.QModelIndex, role:int=...) -> Any:
        if role not in AbstractDeviceState.roles:
            return False

        role_name = DeviceButtonState.roles[role].data().decode()
        return self._state[index.row()][role_name]

    def roleNames(self) -> Dict:
        return DeviceButtonState.roles

    guid = Property(
        str,
        fset=_set_guid,
        notify=deviceChanged
    )


@QtQml.QmlElement
class DeviceAxisState(AbstractDeviceState):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._identifier_map = {}

    def _event_handler_impl(self, event: event_handler.Event) -> None:
        if event.event_type == InputType.JoystickAxis:
            index = self._identifier_map[event.identifier]
            self._state[index]["value"] = event.value
            self.dataChanged.emit(self.index(index, 0), self.index(index, 0))

    def _initialize_state(self) -> None:
        for i in range(self._device.axis_count):
            self._identifier_map[self._device.axis_map[i].axis_index] = i
            self._state.append({
                "identifier": self._device.axis_map[i].axis_index,
                "value": 0.0
            })


@QtQml.QmlElement
class DeviceButtonState(AbstractDeviceState):

    def __init__(self, parent=None):
        super().__init__(parent)

    def _event_handler_impl(self, event):
        if event.event_type == InputType.JoystickButton:
            idx = event.identifier-1
            self._state[idx]["value"] = event.is_pressed
            self.dataChanged.emit(self.index(idx, 0), self.index(idx, 0))

    def _initialize_state(self) -> None:
        for i in range(self._device.button_count):
            self._state.append({
                "identifier": i+1,
                "value": False
            })


@QtQml.QmlElement
class DeviceHatState(AbstractDeviceState):

    def __init__(self, parent=None):
        super().__init__(parent)

    def _event_handler_impl(self, event):
        if event.event_type == InputType.JoystickHat:
            idx = event.identifier-1
            pt = QtCore.QPoint(event.value[0], event.value[1])
            if pt != self._state[idx]["value"]:
                self._state[idx]["value"] = pt
                self.dataChanged.emit(self.index(idx, 0), self.index(idx, 0))

    def _initialize_state(self) -> None:
        for i in range(self._device.hat_count):
            self._state.append({
                "identifier": i+1,
                "value": QtCore.QPoint(0, 0)
            })


@QtQml.QmlElement
class DeviceAxisSeries(QtCore.QObject):

    windowSizeChanged = Signal()
    deviceChanged = Signal()
    axisCountChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        el = event_handler.EventListener()
        el.joystick_event.connect(self._event_callback)

        self._device = None
        self._device_uuid = None
        self._state = []
        self._identifier_map = {}
        self._window_size = 20

    def _set_guid(self, guid: str) -> None:
        if self._device is not None and guid == str(self._device.device_guid):
            return

        self._device = dill.DILL.get_device_information_by_guid(
            dill.GUID.from_str(guid)
        )
        self._device_uuid = uuid.UUID(guid)

        self._state = []
        for i in range(self._device.axis_count):
            self._identifier_map[self._device.axis_map[i].axis_index] = i
            self._state.append({
                "identifier": self._device.axis_map[i].axis_index,
                "timeSeries": []
            })
        self.deviceChanged.emit()

    def _get_window_size(self) -> int:
        return self._window_size

    def _set_window_size(self, value: int) -> None:
        if value != self._window_size:
            self._window_size = value
            self.windowSizeChanged.emit()

    def _event_callback(self, event: event_handler.Event):
        if event.device_guid != self._device_uuid:
            return

        if event.event_type == InputType.JoystickAxis:
            index = self._identifier_map[event.identifier]
            self._state[index]["timeSeries"].append(
                (time.time(), event.value)
            )

    @Property(int, notify=axisCountChanged)
    def axisCount(self) -> int:
        return self._device.axis_count

    @Slot(QtCharts.QLineSeries, int)
    def updateSeries(self, series: QtCharts.QLineSeries, identifier: int):
        data = self._state[identifier]["timeSeries"]

        if len(data) == 0:
            series.replace([
                QtCore.QPointF(0.0, 0.0),
                QtCore.QPointF(self._window_size, 0.0),
            ])
            return

        now  = time.time()
        try:
            while now - data[0][0] > self._window_size:
                data.pop(0)
        except IndexError as e:
            logging.getLogger("system").warning(f"Unexpected exception: {e}")
            return

        time_series = []
        for pt in data:
            time_series.append(QtCore.QPointF(pt[0] - now, pt[1]))
        time_series.append(QtCore.QPointF(0, data[-1][1]))
        series.replace(time_series)

    @Slot(int, result=int)
    def axisIdentifier(self, index: int) -> int:
        return self._state[index]["identifier"]

    guid = Property(
        str,
        fset=_set_guid,
        notify=deviceChanged
    )

    windowSize = Property(
        int,
        fset=_set_window_size,
        fget=_get_window_size,
        notify=windowSizeChanged
    )


Configuration().register(
    "global",
    "input-names",
    "input-name-display-mode",
    PropertyType.Selection,
    "Numerical & Label",
    "Defines how input name is displayed.",
    {
        "valid_options": ["Numerical", "Numerical + Label", "Label"]
    },
    True
)
