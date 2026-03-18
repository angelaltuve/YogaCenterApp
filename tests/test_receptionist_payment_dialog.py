import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QTabWidget, QMessageBox
from ui.receptionist_payment_dialog import ReceptionistPaymentDialog
from database.db import (
    Role, add_user, add_center, assign_user_to_center,
    add_yogaclass, add_reservation, select, Payment
)
from datetime import datetime, timedelta


@pytest.fixture
def setup_receptionist_data(test_session):
    center = add_center("Centro Norte", "Av. Principal 123", "555-1234")
    recep = add_user(
        name="Recepcionista",
        email="recep@test.com",
        phone="",
        password="pass",
        role=Role.RECEPTIONIST
    )
    assign_user_to_center(recep.id, center.id)
    student = add_user(
        name="Estudiante",
        email="est@test.com",
        phone="",
        password="pass",
        role=Role.STUDENT
    )
    teacher = add_user(
        name="Profesor",
        email="prof@test.com",
        phone="",
        password="pass",
        role=Role.TEACHER
    )
    yoga_class = add_yogaclass(
        scheduled_at=datetime.now() + timedelta(days=2),
        max_capacity=10,
        teacher_id=teacher.id,
        center_id=center.id,
        price=25.0
    )
    add_reservation(student.id, yoga_class.id)
    return {
        "recep": recep,
        "student": student,
        "center": center,
        "teacher": teacher,
        "class": yoga_class
    }


def test_receptionist_payment_dialog_init(qtbot, test_session, setup_receptionist_data):
    recep = setup_receptionist_data["recep"]
    dialog = ReceptionistPaymentDialog(recep)
    qtbot.addWidget(dialog)

    tabs = dialog.findChild(QTabWidget)
    assert tabs.count() == 3
    assert "💵 Pago por clase" in tabs.tabText(0)
    assert "📦 Venta de paquetes" in tabs.tabText(1)
    assert "📅 Reservar clase" in tabs.tabText(2)

    assert dialog.student_combo.count() > 1
    assert dialog.pkg_student_combo.count() > 1
    assert dialog.res_student_combo.count() > 1


def test_payment_tab_load_student_reservations(qtbot, test_session, setup_receptionist_data):
    recep = setup_receptionist_data["recep"]
    student = setup_receptionist_data["student"]
    yoga_class = setup_receptionist_data["class"]

    dialog = ReceptionistPaymentDialog(recep)
    qtbot.addWidget(dialog)

    index = dialog.student_combo.findData(student.id)
    assert index != -1
    dialog.student_combo.setCurrentIndex(index)

    assert dialog.class_combo.count() == 2
    item_text = dialog.class_combo.itemText(1)
    assert f"#{yoga_class.id}" in item_text
    assert f"${yoga_class.price:.2f}" in item_text


def test_process_payment(qtbot, test_session, setup_receptionist_data, mocker):
    recep = setup_receptionist_data["recep"]
    student = setup_receptionist_data["student"]
    yoga_class = setup_receptionist_data["class"]

    dialog = ReceptionistPaymentDialog(recep)
    qtbot.addWidget(dialog)

    dialog.student_combo.setCurrentIndex(dialog.student_combo.findData(student.id))
    dialog.class_combo.setCurrentIndex(1)

    mock_payment = mocker.Mock()
    mock_payment.id = 123
    mock_payment.paid_at = datetime.now()
    mock_payment.amount = yoga_class.price
    mock_payment.status = 'paid'
    mock_payment.payment_method = 'Efectivo'

    mock_add_payment = mocker.patch("ui.receptionist_payment_dialog.add_payment", return_value=mock_payment)

    dialog.method_combo.setCurrentText("💵 Efectivo")
    dialog.reference_input.setText("REF001")

    process_btn = None
    for btn in dialog.findChildren(QPushButton):
        if "Procesar Pago" in btn.text():
            process_btn = btn
            break
    assert process_btn is not None

    mocker.patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes)

    qtbot.mouseClick(process_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    mock_add_payment.assert_called_once_with(
        student_id=student.id,
        yogaclass_id=yoga_class.id,
        amount=yoga_class.price,
        payment_method="Efectivo"
    )
