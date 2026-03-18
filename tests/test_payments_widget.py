import pytest
from PyQt6.QtWidgets import QTabWidget
from ui.payments_widget import PaymentsWidget
from database.db import Role, add_user, add_center

def test_payments_widget_for_student(qtbot, test_session):
    # Crear un estudiante real
    student = add_user(
        name="Student",
        email="student@test.com",
        phone="",
        password="pass",
        role=Role.STUDENT
    )
    # Crear un centro
    add_center("Centro Test", "Dirección", "555-1234")

    widget = PaymentsWidget(student)
    qtbot.addWidget(widget)

    # El widget principal tiene un QTabWidget
    outer_tabs = widget.findChild(QTabWidget)
    assert outer_tabs is not None
    # Para estudiante, la primera pestaña debe ser "Mis Pagos"
    assert outer_tabs.tabText(0) == "Mis Pagos"

    # Obtener el contenido de la primera pestaña
    inner_widget = outer_tabs.widget(0)
    inner_tabs = inner_widget.findChild(QTabWidget)
    assert inner_tabs is not None
    assert inner_tabs.tabText(0) == "📅 Mis Reservas"
    assert inner_tabs.tabText(1) == "📦 Mis Paquetes"
