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

import QtGraphs

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"


Item {
    property ResponseCurveModel action
    property Deadzone deadzone: action.deadzone

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

        Label {
            text: "Reponse Curve"
        }

        GraphsView {
            width: 400
            height: 400

            theme: GraphTheme {
                colorTheme: GraphTheme.ColorThemeDark
                gridMajorBarsColor: "#ccccff"
                gridMinorBarsColor: "#eeeeff"
                axisYMajorColor: "#ccccff"
                axisYMinorColor: "#eeeeff"
            }
            BarSeries {
                axisX: BarCategoryAxis {
                    categories: ["2023", "2024", "2025"]
                    lineVisible: false
                }
                axisY: ValueAxis {
                    min: 0
                    max: 10
                    minorTickCount: 4
                }
                BarSet {
                    values: [7, 6, 9]
                }
                BarSet {
                    values: [9, 8, 6]
                }
            }
        }

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