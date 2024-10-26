// -*- coding: utf-8; -*-
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
import QtQuick.Dialogs

import QtQuick.Controls.Universal

import Gremlin.ActionPlugins
import "../../qml"


Item {
    property PlaySoundModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Label {
            id: _label

            Layout.preferredWidth: 110

            text: "Audio filename"
        }

        TextField {
            id: _soundFilename

            Layout.fillWidth: true

            placeholderText: null != action ? null : "Input the name of the audio file to play."
            text: action.soundFilename
            selectByMouse: true

            onTextChanged: {
                action.soundFilename = text
            }
        }

        Button {
            text: "Select File"
            onClicked: _fileDialog.open()
        }

        Label {
            Layout.preferredWidth: 50
            text: "Volume"
        }

        SpinBox {
            id: _soundVolume
            Layout.preferredWidth: 100
            value: action.soundVolume
            from: 0
            to: 100
            editable: true
            onValueModified: {
                action.soundVolume = value
            }
        }
   }

   FileDialog {
        id: _fileDialog
        nameFilters: ["Audio files (*.wav *.mp3 *.ogg)"]
        title: "Select a File"
        onAccepted: {
            _soundFilename.text = selectedFile.toString().substring("file:///".length)
        }
    }
}
