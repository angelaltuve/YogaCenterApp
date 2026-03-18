import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QTableWidget
from ui.package_purchase_dialog import PackagePurchaseDialog
from database.db import add_user, add_package, Role


def test_package_purchase_dialog_load_packages(qtbot, test_session):
    # Crear estudiante
    student = add_user(
        name="Student",
        email="s@test.com",
        phone="",
        password="pass",
        role=Role.STUDENT
    )

    # Crear paquetes activos
    pkg1 = add_package("Pack 5", "desc", 5, 30, 50.0, True)
    pkg2 = add_package("Pack 10", "desc", 10, None, 100.0, True)
    pkg3 = add_package("Pack Inactivo", "desc", 3, 15, 30.0, False)

    dialog = PackagePurchaseDialog(student.id)
    qtbot.addWidget(dialog)

    # La tabla debe mostrar solo los paquetes activos
    table = dialog.packages_table
    assert table.rowCount() == 2

    # Verificar contenido de la primera fila
    assert table.item(0, 0).text() == "Pack 5"
    assert table.item(0, 1).text() == "5"
    assert table.item(0, 2).text() == "$50.00"
    assert table.item(0, 3).text() == "30 días"

    # Segunda fila: sin expiración
    assert table.item(1, 3).text() == "Sin expiración"

    # Cada fila debe tener un botón "Seleccionar"
    btn = table.cellWidget(0, 4)
    assert isinstance(btn, QPushButton)
    assert btn.text() == "Seleccionar"


def test_package_purchase_select_and_purchase(qtbot, test_session, mocker):
    student = add_user("Student", "s@test.com", "", "pass", Role.STUDENT)
    pkg = add_package("Pack Test", "desc", 5, 30, 50.0, True)

    dialog = PackagePurchaseDialog(student.id)
    qtbot.addWidget(dialog)

    # Mockear purchase_package
    mock_purchase = mocker.patch("ui.package_purchase_dialog.purchase_package")
    mock_purchase.return_value = mocker.Mock(id=1)

    # Seleccionar el paquete
    table = dialog.packages_table
    select_btn = table.cellWidget(0, 4)
    qtbot.mouseClick(select_btn, Qt.MouseButton.LeftButton)

    # Ahora hacer clic en "Comprar ahora"
    buy_btn = None
    for btn in dialog.findChildren(QPushButton):
        if "Comprar ahora" in btn.text():
            buy_btn = btn
            break
    assert buy_btn is not None

    # Configurar método de pago y referencia
    dialog.method_combo.setCurrentText("Tarjeta de Crédito")
    dialog.reference_input.setText("REF123")

    # Ejecutar compra
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        qtbot.mouseClick(buy_btn, Qt.MouseButton.LeftButton)

    # Verificar que purchase_package se llamó correctamente
    mock_purchase.assert_called_once_with(
        student_id=student.id,
        package_id=pkg.id,
        payment_method="Tarjeta de Crédito",
        reference="REF123"
    )


def test_package_purchase_reserve(qtbot, test_session, mocker):
    student = add_user("Student", "s@test.com", "", "pass", Role.STUDENT)
    pkg = add_package("Pack Test", "desc", 5, 30, 50.0, True)

    dialog = PackagePurchaseDialog(student.id)
    qtbot.addWidget(dialog)

    mock_reserve = mocker.patch("ui.package_purchase_dialog.reserve_package")
    mock_reserve.return_value = mocker.Mock(id=1)

    # Seleccionar paquete
    table = dialog.packages_table
    select_btn = table.cellWidget(0, 4)
    qtbot.mouseClick(select_btn, Qt.MouseButton.LeftButton)

    # Hacer clic en "Reservar"
    reserve_btn = None
    for btn in dialog.findChildren(QPushButton):
        if "Reservar (pagar después)" in btn.text():
            reserve_btn = btn
            break
    assert reserve_btn is not None

    dialog.method_combo.setCurrentText("Efectivo")
    dialog.reference_input.setText("")

    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        qtbot.mouseClick(reserve_btn, Qt.MouseButton.LeftButton)

    mock_reserve.assert_called_once_with(
        student_id=student.id,
        package_id=pkg.id,
        payment_method="Efectivo",
        reference=""
    )
