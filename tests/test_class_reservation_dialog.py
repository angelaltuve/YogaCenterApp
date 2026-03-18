import pytest
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import QPushButton, QTableWidget
from ui.class_reservation_dialog import ClassReservationDialog
from database.db import (
    Role, add_user, add_center, add_yogaclass,
    add_package, purchase_package
)
from datetime import datetime, timedelta


def test_class_reservation_dialog_load_classes(qtbot, test_session):
    student = add_user("Student", "s@test.com", "", "pass", Role.STUDENT)
    teacher = add_user("Teacher", "t@test.com", "", "pass", Role.TEACHER)
    center = add_center("Centro", "Dir", "555")

    # Crear una clase disponible para mañana
    tomorrow = datetime.now() + timedelta(days=1)
    yoga_class = add_yogaclass(
        scheduled_at=tomorrow,
        max_capacity=5,
        teacher_id=teacher.id,
        center_id=center.id,
        price=20.0
    )

    dialog = ClassReservationDialog(student)
    qtbot.addWidget(dialog)

    # Seleccionar la fecha de mañana
    dialog.date_input.setDate(QDate.currentDate().addDays(1))

    # Verificar que la tabla tiene la clase
    table = dialog.classes_table
    assert table.rowCount() == 1
    # Hora, ID, profesor, centro, precio, disponibilidad, botones
    assert table.item(0, 1).text() == f"#{yoga_class.id}"
    assert "20.00" in table.item(0, 4).text()
    assert table.item(0, 5).text() == "5 cupos"  # disponibilidad


def test_reserve_with_package(qtbot, test_session, mocker):
    student = add_user("Student", "s@test.com", "", "pass", Role.STUDENT)
    teacher = add_user("Teacher", "t@test.com", "", "pass", Role.TEACHER)
    center = add_center("Centro", "Dir", "555")
    tomorrow = datetime.now() + timedelta(days=1)
    yoga_class = add_yogaclass(
        scheduled_at=tomorrow,
        max_capacity=5,
        teacher_id=teacher.id,
        center_id=center.id,
        price=20.0
    )

    # Darle un paquete al estudiante
    pkg = add_package("Pack", "desc", 5, 30, 100.0, True)
    purchase_package(student.id, pkg.id, "cash")

    dialog = ClassReservationDialog(student)
    qtbot.addWidget(dialog)

    dialog.date_input.setDate(QDate.currentDate().addDays(1))

    # Buscar el botón "📦" en la primera fila (columna 6)
    table = dialog.classes_table
    package_btn = table.cellWidget(0, 6)
    assert package_btn is not None
    assert package_btn.toolTip() == "Reservar usando un paquete"

    # Mockear reserve_class_with_package para evitar la llamada real y simular éxito
    mock_reserve = mocker.patch("ui.class_reservation_dialog.reserve_class_with_package")
    mock_reserve.return_value = (True, "Reserva exitosa")

    qtbot.mouseClick(package_btn, Qt.MouseButton.LeftButton)

    mock_reserve.assert_called_once_with(student.id, yoga_class.id)
    # Después de reservar, la tabla debería actualizarse (pero en la prueba no recargamos datos reales)
    # Al menos verificamos que se llamó al método
