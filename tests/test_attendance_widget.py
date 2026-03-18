import pytest
from PyQt6.QtWidgets import QPushButton
from ui.attendance_widget import AttendanceWidget
from database.db import Role, add_user, add_center, add_yogaclass
from datetime import datetime, timedelta

def test_attendance_widget_teacher(qtbot, test_session):
    # Crear un profesor real en la base de datos de prueba
    teacher = add_user(
        name="Teacher",
        email="teacher@test.com",
        phone="",
        password="pass",
        role=Role.TEACHER
    )
    # Crear un centro y una clase para que el combo tenga opciones
    center = add_center("Centro Test", "Dirección", "555-1234")
    add_yogaclass(
        scheduled_at=datetime.now() + timedelta(days=1),
        max_capacity=10,
        teacher_id=teacher.id,
        center_id=center.id,
        price=15.0
    )

    # Crear widget
    widget = AttendanceWidget(teacher)
    qtbot.addWidget(widget)

    # Verificar que el combo de clases existe y tiene al menos un ítem
    assert widget.class_combo.count() >= 1
    assert widget.class_combo.itemText(0) == "-- Seleccione una clase --"

    # Verificar que el botón "Marcar Todos Presentes" existe
    mark_btn = None
    for btn in widget.findChildren(QPushButton):
        if "Marcar Todos Presentes" in btn.text():
            mark_btn = btn
            break
    assert mark_btn is not None
