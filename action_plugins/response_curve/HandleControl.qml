import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Shapes

import "render_helpers.js" as RH


Rectangle {
    id: _control

    readonly property int offset: 5
    property Repeater repeater

    width: offset * 2
    height: offset * 2
    radius: offset

    color: "#66808080"
    border.color: "#66000000"
    border.width: 1

    function map2u(x) {
        return RH.x2u(x, _curve.x, _vis.size, offset)
    }
    function map2v(y) {
        return RH.y2v(y, _curve.x, _vis.size, offset)
    }
    function map2x(u, du) {
        return RH.u2x(u + du - offset, offset, _vis.size)
    }
    function map2y(v, dv) {
        return RH.v2y(v + dv - offset, offset, _vis.size)
    }

    x: map2u(modelData.center.x)
    y: map2v(modelData.center.y)


    Shape {
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeColor: "#0000aa"

            startX: offset
            startY: offset

            PathLine {
                x: _handleLeft.x + offset
                y: _handleLeft.y + offset
            }
            PathMove {
                x: offset
                y: offset
            }
            PathLine {
                x: _handleRight.x + offset
                y: _handleRight.y + offset
            }
        }

        Rectangle {
            id: _handleLeft

            x: ((modelData.handleLeft.x - modelData.center.x) / 2.0) * _vis.size
            y: -((modelData.handleLeft.y - modelData.center.y) / 2.0) * _vis.size

            width: offset * 2
            height: offset * 2

            color: "#aa0000"

            MouseArea {
                anchors.fill: parent
                preventStealing: true

                onPositionChanged: function (evt) {
                    // Compute new data values
                    let new_x = RH.clamp(map2x(parent.x, evt.x), -1.0, 1.0)
                    let new_y = RH.clamp(map2y(parent.y, evt.y), -1.0, 1.0)

                    // Compute new visual values
                    let new_u = RH.clamp(
                        map2u(new_x) - _control.x,
                        -_control.x - offset,
                        _vis.size + offset - _control.x
                    )
                    let new_v = RH.clamp(map2v(new_y), -offset, _vis.size + offset)

                    // Move the actual marker
                    parent.x = new_u
                    parent.y = new_v

                    action.setControlHandle(new_x, new_y, index, "left")
                }
            }
        }

        Rectangle {
            id: _handleRight

            x: ((modelData.handleRight.x - modelData.center.x) / 2.0) * _vis.size
            y: -((modelData.handleRight.y - modelData.center.y) / 2.0) * _vis.size

            width: offset * 2
            height: offset * 2

            color: "#00aa00"

            MouseArea {
                anchors.fill: parent
                preventStealing: true

                onPositionChanged: function (evt) {
                    console.log("h2", evt.x, evt.y)
                }
            }
        }

    }

    MouseArea {
        anchors.fill: parent
        preventStealing: true

        onPositionChanged: function (evt) {
            console.log("c", evt.x, evt.y)
        }
    }
}