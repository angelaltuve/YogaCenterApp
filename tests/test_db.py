import pytest
from datetime import datetime, timedelta
from database.db import (
    add_user, authenticate, user_exists, Role,
    add_center, get_all_centers,
    add_yogaclass, get_class_by_id,
    add_reservation, get_reservations_by_student,
    add_payment,
    add_package, get_active_packages, purchase_package,
    reserve_class_with_package,
    has_administrator, has_centers,
)

def test_add_user_and_authenticate(test_session):
    # Crear usuario
    user = add_user(
        name="Test User",
        email="test@example.com",
        phone="123456789",
        password="secret",
        role=Role.STUDENT
    )
    assert user is not None
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == Role.STUDENT

    # Verificar existencia
    assert user_exists("test@example.com") is True

    # Autenticación correcta
    auth_user = authenticate("test@example.com", "secret")
    assert auth_user is not None
    assert auth_user.id == user.id

    # Autenticación incorrecta
    assert authenticate("test@example.com", "wrong") is None
    assert authenticate("no@existe.com", "secret") is None

def test_has_administrator_empty(test_session):
    """Sin administradores, debe retornar False."""
    assert has_administrator() is False

def test_has_centers_empty(test_session):
    assert has_centers() is False

def test_add_center(test_session):
    center = add_center("Centro Test", "Calle Falsa 123", "555-1234")
    assert center.id is not None
    centers = get_all_centers()
    assert len(centers) == 1
    assert centers[0].name == "Centro Test"

def test_add_yogaclass(test_session):
    # Primero necesitamos un profesor y un centro
    teacher = add_user(
        name="Teacher",
        email="teacher@test.com",
        phone="",
        password="pass",
        role=Role.TEACHER
    )
    center = add_center("Centro", "Dirección", "555-0000")

    scheduled_at = datetime.now() + timedelta(days=1)
    yoga_class = add_yogaclass(
        scheduled_at=scheduled_at,
        max_capacity=20,
        teacher_id=teacher.id,
        center_id=center.id,
        price=15.0,
        teacher_share_percentage=70.0
    )
    assert yoga_class.id is not None

    # Recuperar
    c = get_class_by_id(yoga_class.id)
    assert c is not None
    assert c.max_capacity == 20
    assert c.price == 15.0

def test_reservation_and_payment(test_session):
    # Crear estudiante, profesor, centro y clase
    student = add_user("Student", "s@test.com", "", "pass", Role.STUDENT)
    teacher = add_user("Teacher", "t@test.com", "", "pass", Role.TEACHER)
    center = add_center("C", "Addr", "123")
    yoga_class = add_yogaclass(
        scheduled_at=datetime.now() + timedelta(days=1),
        max_capacity=10,
        teacher_id=teacher.id,
        center_id=center.id,
        price=20.0
    )

    # Reservar
    reserve = add_reservation(student.id, yoga_class.id)
    assert reserve is not None
    assert reserve.status == "active"

    # Verificar reservas del estudiante
    reserves = get_reservations_by_student(student.id)
    assert len(reserves) == 1
    assert reserves[0].yogaclass_id == yoga_class.id

    # Pagar la clase
    payment = add_payment(
        student_id=student.id,
        yogaclass_id=yoga_class.id,
        amount=yoga_class.price,
        payment_method="cash"
    )
    assert payment is not None
    assert payment.status == "paid"

def test_package_flow(test_session):
    # Crear estudiante
    student = add_user("Student", "s2@test.com", "", "pass", Role.STUDENT)

    # Crear paquete
    pkg = add_package(
        name="Pack 10 clases",
        description="10 clases por $100",
        total_classes=10,
        validity_days=30,
        price=100.0,
        is_active=True
    )
    assert pkg.id is not None

    # Comprar paquete
    sp = purchase_package(
        student_id=student.id,
        package_id=pkg.id,
        payment_method="cash"
    )
    assert sp is not None
    assert sp.remaining_classes == 10
    assert sp.status == "active"

    # Verificar paquetes activos
    active = get_active_packages()
    assert len(active) == 1
    assert active[0].id == pkg.id

    # Crear clase para usar el paquete
    teacher = add_user("T", "t2@test.com", "", "pass", Role.TEACHER)
    center = add_center("C2", "Addr", "123")
    yoga_class = add_yogaclass(
        scheduled_at=datetime.now() + timedelta(days=1),
        max_capacity=5,
        teacher_id=teacher.id,
        center_id=center.id,
        price=15.0
    )

    # Reservar con paquete
    success, msg = reserve_class_with_package(student.id, yoga_class.id)
    assert success is True

    # Verificar que el paquete descontó una clase
    from database.db import get_student_packages
    sps = get_student_packages(student.id)
    assert sps[0].remaining_classes == 9
