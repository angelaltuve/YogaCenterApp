import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QMessageBox
from ui.register_dialog import RegisterDialog
from database.db import user_exists

def test_register_dialog_initial_state(qtbot):
    dialog = RegisterDialog()
    qtbot.addWidget(dialog)

    assert dialog.name_input.text() == ""
    assert dialog.email_input.text() == ""
    assert dialog.phone_input.text() == ""
    assert dialog.password_input.text() == ""
    assert dialog.confirm_input.text() == ""

def test_register_empty_fields_shows_warning(qtbot, mocker):
    dialog = RegisterDialog()
    qtbot.addWidget(dialog)

    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")

    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_button is not None

    qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    args, _ = mock_warning.call_args
    assert "Campos requeridos" in args[1]

def test_register_password_mismatch(qtbot, mocker):
    dialog = RegisterDialog()
    qtbot.addWidget(dialog)

    dialog.name_input.setText("Test User")
    dialog.email_input.setText("test@example.com")
    dialog.password_input.setText("password123")
    dialog.confirm_input.setText("password456")

    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")

    button_box = dialog.findChild(QDialogButtonBox)
    ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)

    qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    args, _ = mock_warning.call_args
    assert "no coinciden" in args[1]

def test_register_successful(qtbot, test_session, mocker):
    assert not user_exists("newuser@test.com")

    mock_info = mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    dialog = RegisterDialog()
    qtbot.addWidget(dialog)

    dialog.name_input.setText("New User")
    dialog.email_input.setText("newuser@test.com")
    dialog.phone_input.setText("123456789")
    dialog.password_input.setText("securepass")
    dialog.confirm_input.setText("securepass")

    button_box = dialog.findChild(QDialogButtonBox)
    ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)

    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    assert user_exists("newuser@test.com") is True
    assert dialog.user is not None
    assert dialog.user.email == "newuser@test.com"
    mock_info.assert_called_once()
