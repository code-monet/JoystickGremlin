// -*- coding: utf-8; -*-
//
// Copyright (C) 2015 - 2022 Lionel Ott
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
import QtQuick.Templates as T
import QtQuick.Controls.Universal

T.TabBar {
    id: control

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            contentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             contentHeight + topPadding + bottomPadding)

    contentItem: ListView {
            model: control.contentModel
            currentIndex: control.currentIndex

            spacing: control.spacing
            orientation: ListView.Horizontal
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.AutoFlickIfNeeded
            snapMode: ListView.SnapToItem

            ScrollBar.horizontal: ScrollBar {
                policy: ScrollBar.AlwaysOn
            }

            highlightMoveDuration: 100
            highlightRangeMode: ListView.ApplyRange
            preferredHighlightBegin: 48
            preferredHighlightEnd: width - 48


            MouseArea {
                anchors.fill: parent

                // Scroll the view without the need for a modifier
                onWheel: function(evt) {
                    if(parent.contentWidth < parent.width) {
                        return
                    }

                    if (evt.angleDelta.y > 0) {
                        parent.contentX = Math.max(0, parent.contentX - 10)
                    } else {
                        parent.contentX = Math.min(
                            parent.contentWidth - parent.width,
                            parent.contentX + 10
                        )
                    }
                }

                // Ignore all other events and thus pass then  to the
                // underlying ListView
                onClicked: (mouse) => mouse.accepted = false
                onPressed: (mouse) => mouse.accepted = false
                onReleased: (mouse) => mouse.accepted = false
                onDoubleClicked: (mouse) => mouse.accepted = false
                onPositionChanged: (mouse) => mouse.accepted = false
                onPressAndHold: (mouse) => mouse.accepted = false
            }
        }

    background: Rectangle {
        implicitWidth: 200
        implicitHeight: 48
        color: control.Universal.background
    }
}