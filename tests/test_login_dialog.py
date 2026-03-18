import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QMessageBox
from ui.login_dialog import LoginDialog

def test_login_dialog_initial_state(qtbot):
    dialog = LoginDialog()
    qtbot.addWidget(dialog)

    assert dialog.email_input.text() == ""
    assert dialog.password_input.text() == ""
    # Buscar el botón de login por su objectName
    login_btn = dialog.findChild(QPushButton, "login_btn")
    assert login_btn is not None

def test_login_empty_fields_shows_warning(qtbot, mocker):
    dialog = LoginDialog()
    qtbot.addWidget(dialog)

    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")
    login_btn = dialog.findChild(QPushButton, "login_btn")

    qtbot.mouseClick(login_btn, Qt.MouseButton.LeftButton)
    mock_warning.assert_called_once()

def test_login_invalid_email_shows_warning(qtbot, mocker):
    dialog = LoginDialog()
    qtbot.addWidget(dialog)

    dialog.email_input.setText("invalid")
    dialog.password_input.setText("pass")

    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")
    login_btn = dialog.findChild(QPushButton, "login_btn")
    qtbot.mouseClick(login_btn, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    args, _ = mock_warning.call_args
    assert "Email inválido" in args[1]

def test_login_successful(qtbot, mocker):
    # Mockear authenticate
    mock_authenticate = mocker.patch("ui.login_dialog.authenticate")
    mock_user = mocker.Mock()
    mock_user.is_active = True
    mock_authenticate.return_value = mock_user

    dialog = LoginDialog()
    qtbot.addWidget(dialog)

    dialog.email_input.setText("valid@test.com")
    dialog.password_input.setText("correctpass")

    # Conectar señal para asegurar que se emite
    with qtbot.waitSignal(dialog.login_successful, timeout=1000):
        login_btn = dialog.findChild(QPushButton, "login_btn")
        qtbot.mouseClick(login_btn, Qt.MouseButton.LeftButton)

    assert dialog.user == mock_user

def test_login_inactive_user(qtbot, mocker):
    mock_authenticate = mocker.patch("ui.login_dialog.authenticate")
    mock_user = mocker.Mock()
    mock_user.is_active = False
    mock_authenticate.return_value = mock_user

    mock_warning = mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")

    dialog = LoginDialog()
    qtbot.addWidget(dialog)

    dialog.email_input.setText("inactive@test.com")
    dialog.password_input.setText("pass")

    login_btn = dialog.findChild(QPushButton, "login_btn")
    qtbot.mouseClick(login_btn, Qt.MouseButton.LeftButton)

    mock_warning.assert_called_once()
    # El usuario no debería asignarse
    assert dialog.user is None
