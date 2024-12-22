// -*- coding: utf-8; -*-
//
// Copyright (C) 2015 - 2024 Lionel Ott
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal

import Gremlin.Device

// Visualizes the inputs and information about their associated actions
// contained in the IntermediateOutput system.
Item {
    id: _root

    property IODeviceManagementModel device
    property int inputIndex
    property InputIdentifier inputIdentifier

    // Modal window to allow renaming of inputs
    TextInputDialog {
        id: _textInput

        visible: false
        width: 300

        property var callback: null

        onAccepted: function(value)
        {
            callback(value)
            visible = false
        }
    }

    // List of all existing inputs
    ColumnLayout {
        id: _content

        anchors.fill: parent

        ListView {
            id: _inputList

            Layout.minimumWidth: 200
            Layout.fillHeight: true
            Layout.fillWidth: true

            model: device
            delegate: _entryDelegate

            onCurrentIndexChanged: {
                inputIndex = currentIndex
                inputIdentifier = device.inputIdentifier(currentIndex)
            }

            // Make it behave like a sensible scrolling container
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AlwaysOn
            }
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
        }

        // Controls to add new intermediate output instances
        RowLayout {
            Layout.minimumWidth: 100
            Layout.preferredHeight: 50

            ComboBox {
                id: _input_type

                Layout.fillWidth: true

                model: ["Axis", "Button", "Hat"]
            }

            IconButton {
                text: Constants.add
                backgroundColor: Universal.baseLowColor

                onClicked: {
                    device.createInput(_input_type.currentValue)
                }
            }
        }
    }

    Component {
        id: _entryDelegate

        Item {
            id: _delegate

            height: _inputDisplay.height
            width: _inputDisplay.width

            required property int index
            required property string name
            required property string label
            required property int actionCount
            property ListView view: ListView.view

            // Renders the entire "button" area of the singular input
            Rectangle {
                id: _inputDisplay

                implicitWidth: view.width - _inputList.ScrollBar.vertical.width
                height: 50

                color: index == view.currentIndex
                    ? Universal.chromeMediumColor : Universal.background

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        view.currentIndex = index
                    }
                }

                // User specified name assigned to this output
                Label {
                    text: label
                    font.weight: 600

                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 5
                    anchors.topMargin: 5
                }

                // Internal UUID-based name
                Text {
                    text: name
                    anchors.leftMargin: 5
                    anchors.topMargin: 5

                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                }

                Label {
                    text: actionCount ? actionCount : ""

                    anchors.top: parent.top
                    anchors.right: _btnTrash.left
                    anchors.rightMargin: 5
                    anchors.topMargin: 5
                }

                // Button to remove an input
                IconButton {
                    id: _btnTrash
                    text: Constants.remove
                    font.pixelSize: 12

                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.rightMargin: 5
                    anchors.topMargin: 5

                    onClicked: {
                        device.deleteInput(label)
                    }
                }

                // Button enabling the editing of the input's label
                IconButton {
                    id: _btnEdit
                    text: Constants.edit
                    font.pixelSize: 12

                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.rightMargin: 5
                    anchors.bottomMargin: 2

                    onClicked: function () {
                        _textInput.text = label
                        _textInput.callback = function(value) {
                            device.changeName(label, value)
                        }
                        _textInput.visible = true
                    }
                }
            }
        }
    }
}