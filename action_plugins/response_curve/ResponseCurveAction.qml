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
import QtQuick.Shapes
import Qt.labs.qmlmodels

import QtCharts

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"

import "render_helpers.js" as RH


Item {
    id: _root

    property ResponseCurveModel action
    property Deadzone deadzone: action.deadzone
    property alias widgetSize : _vis.size

    implicitHeight: _content.height

    // Handle model value changes as propert bindings run into cyclical
    // trigger challenges
    Component.onCompleted: function() {
        setLow(deadzone.low)
        setCenterLow(deadzone.centerLow)
        setCenterHigh(deadzone.centerHigh)
        setHigh(deadzone.high)
    }

    Connections {
        target: deadzone

        function onLowModified(value) { setLow(value) }
        function onCenterLowModified(value) { setCenterLow(value) }
        function onCenterHighModified(value) { setCenterHigh(value) }
        function onHighModified(value) { setHigh(value) }
    }

    function setLow(value) {
        _spinLow.realValue = value
        _sliderLow.first.value = value
    }

    function setCenterLow(value) {
        _spinCenterLow.realValue = value
        _sliderLow.second.value = value
    }

    function setCenterHigh(value) {
        _spinCenterHigh.realValue = value
        _sliderHigh.first.value = value
    }

    function setHigh(value) {
        _spinHigh.realValue = value
        _sliderHigh.second.value = value
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right


        RowLayout {
            Layout.fillWidth: true

            ComboBox {
                Layout.preferredWidth: 200

                model: ["Piecewise Linear", "Cubic Spline", "Cubic Bezier Spline"]

                Component.onCompleted: function () {
                    currentIndex = find(_root.action.curveType)
                }

                onActivated: function () {
                    _root.action.curveType = currentText
                }
            }

            Button {
                text: "Invert Curve"

                onClicked: _root.action.invertCurve()
            }

            CheckBox {
                text: "Symmetric"

                checked: _root.action.isSymmetric

                onToggled: function () {
                    _root.action.isSymmetric = checked
                }
            }
        }

        // Response curve widget
        Item {
            id: _vis

            property int size: 450
            property int border: 2

            Component.onCompleted: function () {
                action.setWidgetSize(size)
            }

            width: size + 2 * border
            height: size + 2 * border

            // Display the background image
            Image {
                width: _vis.size
                height: _vis.size
                x: _vis.border
                y: _vis.border
                source: "grid.svg"
            }

            // Render the response curve itself not the interactive elemntgs
            Shape {
                id: _curve

                width: _vis.size
                height: _vis.size

                anchors.centerIn: parent

                preferredRendererType: Shape.CurveRenderer

                ShapePath {
                    strokeColor: "#808080"
                    strokeWidth: 2
                    fillColor: "transparent"

                    PathPolyline {
                        path: action.linePoints
                    }
                }

                MouseArea {
                    anchors.fill: parent

                    onDoubleClicked: function (evt) {
                        action.addControlPoint(
                            2 * (evt.x / width) - 1,
                            -2 * (evt.y / height) + 1
                        )
                    }
                }
            }

            Repeater {
                id: _repeater

                model: action.controlPoints

                delegate: Component {
                    // Pick the correct control visualization to load and pass
                    // the repeater reference in
                    Loader {
                        Component.onCompleted: function() {
                            let url = modelData.hasHandles ? "HandleControl.qml" : "PointControl.qml"
                            setSource(url, {"repeater": _repeater})
                        }

                    }
                }
            }
        }

        // Deadzone widget
        Label {
            text: "Deadzone"
        }

        GridLayout {
                Layout.fillWidth: true

                columns: 4

                RangeSlider {
                    id: _sliderLow

                    Layout.columnSpan: 2
                    Layout.alignment: Qt.AlignRight

                    from: -1.0
                    to: 0.0

                    first {
                        onMoved: {
                            deadzone.low = first.value
                        }
                    }
                    second {
                        onMoved: {
                            deadzone.centerLow = second.value
                        }
                    }
                }

                RangeSlider {
                    id: _sliderHigh

                    Layout.columnSpan: 2
                    Layout.alignment: Qt.AlignLeft

                    from: 0.0
                    to: 1.0

                    first {
                        onMoved: {
                            deadzone.centerHigh = first.value
                        }
                    }
                    second {
                        onMoved: {
                            deadzone.high = second.value
                        }
                    }
                }

                FloatSpinBox {
                    id: _spinLow

                    realValue: -1.0
                    minValue: -1.0
                    maxValue: _spinCenterLow.realValue

                    onRealValueModified: {
                        deadzone.low = realValue
                    }
                }
                FloatSpinBox {
                    id: _spinCenterLow

                    realValue: 0.0
                    minValue: _spinLow.realValue
                    maxValue: 0.0
                }
                FloatSpinBox {
                    id: _spinCenterHigh

                    realValue: 0.0
                    minValue: 0.0
                    maxValue: _spinHigh.realValue
                }
                FloatSpinBox {
                    id: _spinHigh

                    realValue: 1.0
                    minValue: _spinCenterHigh.realValue
                    maxValue: 1.0
                }
            }
    }
}