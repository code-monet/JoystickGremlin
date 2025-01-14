// -*- coding: utf-8; -*-
//
// Copyright (C) 2015 - 2023 Lionel Ott
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
// contained in a Device instance
Item {
    id: _root

    property Device device
    property int inputIndex
    property InputIdentifier inputIdentifier
    property int minimumWidth: _inputList.minimumWidth
    property alias currentIndex: _inputList.currentIndex

    // Sychronize input selection when the underlying device changes
    Connections {
        target: device

        function onDeviceChanged()
        {
            inputIndex = _inputList.currentIndex
            inputIdentifier = device.inputIdentifier(inputIndex)
        }
    }

    // List of all the inputs available on the device
    ListView {
        id: _inputList
        anchors.fill: parent

        property int minimumWidth: 200

        model: device
        delegate: _deviceDelegate

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

    // Renders the information about a single input, including name and
    // overview of the assopciated actions
    Component {
        id: _deviceDelegate

        Rectangle {
            id: _inputDisplay

            width: _inputList.width
            implicitWidth: _inputLabel.width + _inputOverview.width + 50
            height: 50

            // Dynamically compute the minimum width required to fully display
            // the input information. This is used to properly configure the
            // SplitView component.
            Component.onCompleted: {
                _inputList.minimumWidth = Math.max(
                    _inputList.minimumWidth,
                    implicitWidth
                )
            }

            color: model.index === _inputList.currentIndex
                ? Universal.chromeMediumColor : Universal.background

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    _inputList.currentIndex = model.index;
                }
            }

            Label {
                id: _inputLabel
                text: name
                font.weight: 600

                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 5
                anchors.topMargin: 5
            }

            Label {
                id: _inputOverview
                text: actionCount ? actionCount : ""

                anchors.top: parent.top
                anchors.right: _inputDisplay.right
                anchors.rightMargin: 20
                anchors.topMargin: 5
            }

            Text {
                id: _inputDescription
                text: description
                font.italic: true

                width: parent.width - 30
                elide: Text.ElideRight

                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.leftMargin: 5
                anchors.bottomMargin: 5
            }
        }
    }
}