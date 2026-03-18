import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QPushButton
from ui.reports_widget import ReportsWidget
from database.db import (
    Role, User, Center, YogaClass, Reserve, Attendance, Payment,
    hash_password, select
)
from datetime import datetime, timedelta


@pytest.fixture
def setup_report_data(test_session):
    """Crea datos directamente en la sesión de prueba para reportes."""
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash=hash_password("pass"),
        role=Role.ADMINISTRATOR
    )
    test_session.add(admin)

    center = Center(name="Centro Test", address="Dir", phone="555")
    test_session.add(center)

    teacher = User(
        name="Teacher",
        email="t@test.com",
        password_hash=hash_password("pass"),
        role=Role.TEACHER
    )
    test_session.add(teacher)

    student = User(
        name="Student",
        email="s@test.com",
        password_hash=hash_password("pass"),
        role=Role.STUDENT
    )
    test_session.add(student)

    test_session.flush()

    past_class = YogaClass(
        scheduled_at=datetime.now() - timedelta(days=2),
        max_capacity=10,
        current_capacity=0,
        price=20.0,
        teacher_id=teacher.id,
        center_id=center.id,
        teacher_share_percentage=70.0
    )
    test_session.add(past_class)

    future_class = YogaClass(
        scheduled_at=datetime.now() + timedelta(days=3),
        max_capacity=10,
        current_capacity=0,
        price=25.0,
        teacher_id=teacher.id,
        center_id=center.id,
        teacher_share_percentage=70.0
    )
    test_session.add(future_class)

    test_session.flush()

    reserve_past = Reserve(
        student_id=student.id,
        yogaclass_id=past_class.id,
        status="active"
    )
    test_session.add(reserve_past)

    attendance = Attendance(
        student_id=student.id,
        yogaclass_id=past_class.id,
        attended_at=datetime.now() - timedelta(days=2),
        status="present"
    )
    test_session.add(attendance)

    reserve_future = Reserve(
        student_id=student.id,
        yogaclass_id=future_class.id,
        status="active"
    )
    test_session.add(reserve_future)

    payment = Payment(
        student_id=student.id,
        yogaclass_id=past_class.id,
        amount=past_class.price,
        payment_method="cash",
        status="paid",
        paid_at=datetime.now() - timedelta(days=2)
    )
    test_session.add(payment)

    test_session.commit()

    past_class.current_capacity += 1
    future_class.current_capacity += 1
    test_session.commit()

    return {
        "admin": admin,
        "center": center,
        "teacher": teacher,
        "student": student,
        "past_class": past_class,
        "future_class": future_class,
        "payment": payment
    }


def test_reports_widget_admin_tabs(qtbot, test_session, setup_report_data):
    admin = setup_report_data["admin"]
    widget = ReportsWidget(admin)
    qtbot.addWidget(widget)

    tabs = widget.tabs
    assert tabs.count() == 4
    assert "💰 Financiero" in tabs.tabText(0)
    assert "📋 Asistencia" in tabs.tabText(1)
    assert "🎯 Clases" in tabs.tabText(2)
    assert "👥 Usuarios" in tabs.tabText(3)


def test_generate_financial_report(qtbot, test_session, setup_report_data):
    admin = setup_report_data["admin"]
    widget = ReportsWidget(admin)
    qtbot.addWidget(widget)

    payments = test_session.exec(select(Payment)).all()
    assert len(payments) == 1, "Debería haber un pago en la BD"

    widget.tabs.setCurrentIndex(0)
    widget.fin_start.setDate(QDate.currentDate().addDays(-10))
    widget.fin_end.setDate(QDate.currentDate().addDays(1))

    widget.generate_report("financial")

    qtbot.wait(100)

    table = widget.fin_table
    assert table.rowCount() >= 1, "La tabla financiera debería tener al menos una fila"

    found = False
    for row in range(table.rowCount()):
        if table.item(row, 2) and "Student" in table.item(row, 2).text():
            found = True
            break
    assert found, "No se encontró el pago del estudiante en la tabla"


def test_generate_attendance_report(qtbot, test_session, setup_report_data):
    admin = setup_report_data["admin"]
    widget = ReportsWidget(admin)
    qtbot.addWidget(widget)

    attendances = test_session.exec(select(Attendance)).all()
    assert len(attendances) == 1, "Debería haber una asistencia en la BD"

    widget.tabs.setCurrentIndex(1)
    widget.att_start.setDate(QDate.currentDate().addDays(-10))
    widget.att_end.setDate(QDate.currentDate().addDays(1))

    teacher_id = setup_report_data["teacher"].id
    index = widget.att_teacher.findData(teacher_id)
    widget.att_teacher.setCurrentIndex(index)

    widget.generate_report("attendance")

    qtbot.wait(100)

    table = widget.att_table
    assert table.rowCount() >= 1, "La tabla de asistencia debería tener al menos una fila"
    assert "Student" in table.item(0, 2).text()
