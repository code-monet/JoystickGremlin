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

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"


Item {
    property ChainModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                id: _label

                text: "Timeout (sec)"
            }

            FloatSpinBox {
                minValue: 0
                maxValue: 3600
                realValue: _root.action.timeout
                stepSize: 5

                onRealValueModified: {
                    _root.action.timeout = realValue
                }
            }

            LayoutSpacer {}

            Button {
                text: "Add Chain Sequence"

                onPressed: function() {
                    _root.action.addSequence()
                }
            }
        }

        Repeater {
            model: _root.action.chainCount

            delegate: ChainSet {}
        }
    }

    component ChainSet : ColumnLayout {
        Layout.fillWidth: true

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Sequence " + index
            }

            LayoutSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: function(x) {
                    _root.action.appendAction(x, index.toString());
                }
            }

            IconButton {
                text: bsi.icons.remove

                onClicked: function() {
                    _root.action.removeSequence(index)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 2
            color: Universal.baseLowColor
        }

        ListView {
            id: _chainSequence

            model: _root.action.getActions(index.toString())

            Layout.fillWidth: true
            implicitHeight: contentHeight

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: index.toString()

                width: _chainSequence.width
            }
        }
    }
}