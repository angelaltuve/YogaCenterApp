import pytest
from PyQt6.QtWidgets import QPushButton
from ui.class_management import ClassManagementWidget
from database.db import Role

def test_class_management_widget_admin(qtbot, mocker):
    user = mocker.Mock()
    user.role = Role.ADMINISTRATOR

    # Parchear load_classes para no hacer consultas reales
    mocker.patch.object(ClassManagementWidget, "load_classes", return_value=None)

    widget = ClassManagementWidget(user)
    qtbot.addWidget(widget)

    # Verificar que el botón "Nueva Clase" existe
    add_button = None
    for btn in widget.findChildren(QPushButton):
        if "Nueva Clase" in btn.text():
            add_button = btn
            break
    assert add_button is not None

def test_class_management_widget_student(qtbot, mocker):
    user = mocker.Mock()
    user.role = Role.STUDENT

    mocker.patch.object(ClassManagementWidget, "load_classes", return_value=None)

    widget = ClassManagementWidget(user)
    qtbot.addWidget(widget)

    # Para estudiante debería haber botón "Reservar Clase"
    reserve_button = None
    for btn in widget.findChildren(QPushButton):
        if "Reservar Clase" in btn.text():
            reserve_button = btn
            break
    assert reserve_button is not None

    # No debería haber botón "Nueva Clase"
    for btn in widget.findChildren(QPushButton):
        assert "Nueva Clase" not in btn.text()
