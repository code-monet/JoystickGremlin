import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

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

    x: RH.x2u(modelData.center.x, _curve.x, _vis.size, offset)
    y: RH.y2v(modelData.center.y, _curve.y, _vis.size, offset)

    MouseArea {
        anchors.fill: parent
        preventStealing: true

        onReleased: function (evt) {
            let new_x = RH.clamp(
                RH.u2x(parent.x, offset, _vis.size),
                -1.0,
                1.0
            )
            let new_y = RH.clamp(
                RH.v2y(parent.y, offset, _vis.size),
                -1.0,
                1.0
            )
            action.setControlPoint(new_x, new_y, index)
        }

        onPositionChanged: function (evt) {
            let new_x = RH.clamp(
                RH.u2x(parent.x + evt.x - offset, offset, _vis.size),
                -1.0,
                1.0
            )
            let new_y = RH.clamp(
                RH.v2y(parent.y + evt.y - offset, offset, _vis.size),
                -1.0,
                1.0
            )

            // Ensure the points at either end cannot be moved
            // away from the edge
            if (index === 0) {
                new_x = -1.0
            } else if (index === action.controlPoints.length - 1) {
                new_x = 1.0
            }

            // In symmetry mode moving the center point, if
            // there is one is not allowed
            if (_root.action.isSymmetric && repeater.count % 2 !== 0 &&
                index * 2 + 1 === repeater.count) {
                return
            }

            // Prevent moving control point past neighoring ones
            let new_u = RH.clamp(
                RH.x2u(new_x, _curve.x, _vis.size, offset),
                -offset,
                _vis.size + offset
            )
            let new_v = RH.clamp(
                RH.y2v(new_y, _curve.y, _vis.size, offset),
                -offset,
                _vis.size + offset
            )

            let left = repeater.itemAt(index - 1)
            let right = repeater.itemAt(index + 1)
            if (left && left.item.x > new_u) {
                new_u = parent.x
                new_x = RH.u2x(parent.x, offset, _vis.size)
            }
            if (right && right.item.x < new_u) {
                new_u = parent.x
                new_x = RH.u2x(parent.x, offset, _vis.size)
            }

            // Move the actual marker
            parent.x = new_u
            parent.y = new_v

            // Handle symmetry mode, no need to update model as
            // the code does this behind the scenes with the
            // model update below
            if (_root.action.isSymmetric) {
                let mirror = repeater.itemAt(repeater.count - index - 1).item
                mirror.x = RH.x2u(-new_x, _curve.x, _vis.size, offset)
                mirror.y = RH.y2v(-new_y, _curve.y, _vis.size, offset)

            }

            // Update model with new position
            action.setControlPoint(new_x, new_y, index)
        }
    }
}