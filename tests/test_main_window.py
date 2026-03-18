import pytest
from PyQt6.QtWidgets import QTabWidget
from ui.main_window import MainWindow
from database.db import Role, add_user, add_center

def test_main_window_for_admin(qtbot, test_session):
    # Crear un administrador real en la base de datos
    admin = add_user(
        name="Admin",
        email="admin@test.com",
        phone="",
        password="pass",
        role=Role.ADMINISTRATOR
    )

    add_center("Centro Principal", "Dirección", "555-0000")

    window = MainWindow(admin)
    qtbot.addWidget(window)

    tab_widget = window.findChild(QTabWidget)
    assert tab_widget is not None

    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    expected = ["📊 Dashboard", "👥 Usuarios", "🎯 Clases", "🏢 Centros", "📈 Reportes", "📦 Paquetes"]
    for name in expected:
        assert name in tab_names

def test_main_window_for_student(qtbot, test_session):
    # Crear un estudiante real
    student = add_user(
        name="Student",
        email="student@test.com",
        phone="",
        password="pass",
        role=Role.STUDENT
    )
    # Crear un centro para evitar errores en el dashboard
    add_center("Centro Test", "Dirección", "555-1234")

    window = MainWindow(student)
    qtbot.addWidget(window)

    tab_widget = window.findChild(QTabWidget)
    tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    expected = ["📊 Dashboard", "🎯 Clases", "💰 Pagos"]
    for name in expected:
        assert name in tab_names
    assert "👥 Usuarios" not in tab_names
    assert "🏢 Centros" not in tab_names
