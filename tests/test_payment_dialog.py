import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QComboBox
from ui.payment_dialog import PaymentDialog
from database.db import (
    Role, add_user, add_center, add_yogaclass,
    add_reservation
)
from datetime import datetime, timedelta


def test_payment_dialog_load_classes(qtbot, test_session):
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
    # Reserva activa sin pago
    add_reservation(student.id, yoga_class.id)

    dialog = PaymentDialog(student)
    qtbot.addWidget(dialog)

    # El combo debe tener la clase
    assert dialog.class_combo.count() == 1
    item_text = dialog.class_combo.itemText(0)
    # Verificar que el texto contiene el ID de la clase y el precio
    assert f"Clase {yoga_class.id}" in item_text
    assert "$20.00" in item_text


def test_process_payment(qtbot, test_session, mocker):
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
    add_reservation(student.id, yoga_class.id)

    dialog = PaymentDialog(student)
    qtbot.addWidget(dialog)

    # Mockear add_payment
    mock_add_payment = mocker.patch("ui.payment_dialog.add_payment")
    mock_add_payment.return_value = mocker.Mock(id=1)

    # Seleccionar método
    dialog.method_combo.setCurrentText("Tarjeta de Crédito")

    # Hacer clic en OK
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog.process_payment()

    mock_add_payment.assert_called_once_with(
        student_id=student.id,
        yogaclass_id=yoga_class.id,
        amount=20.0,
        payment_method="Tarjeta de Crédito"
    )
