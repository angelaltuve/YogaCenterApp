import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QTableWidget
from ui.package_management import PackageManagementWidget, PackageDialog
from database.db import Role, add_user, add_package


def test_package_management_widget_admin(qtbot, test_session, mocker):
    # Crear un usuario administrador
    admin = add_user(
        name="Admin",
        email="admin@test.com",
        phone="",
        password="pass",
        role=Role.ADMINISTRATOR
    )

    # Crear algunos paquetes de prueba
    pkg1 = add_package(
        name="Pack 5 clases",
        description="5 clases por $50",
        total_classes=5,
        validity_days=30,
        price=50.0,
        is_active=True
    )
    pkg2 = add_package(
        name="Pack 10 clases",
        description="10 clases por $90",
        total_classes=10,
        validity_days=None,
        price=90.0,
        is_active=False
    )

    # Crear widget
    widget = PackageManagementWidget(admin)
    qtbot.addWidget(widget)

    # Verificar que la tabla tiene las filas correctas
    table = widget.packages_table
    assert table.rowCount() == 2

    # Verificar contenido de la primera fila
    assert table.item(0, 1).text() == "Pack 5 clases"
    assert table.item(0, 3).text() == "5"
    assert table.item(0, 4).text() == "30"
    assert table.item(0, 5).text() == "$50.00"
    assert table.item(0, 6).text() == "✅ Sí"

    # Segunda fila (pkg2) debe mostrar "❌ No"
    assert table.item(1, 6).text() == "❌ No"

    # Botones de acción deben existir en la columna 7
    cell_widget = table.cellWidget(0, 7)
    assert cell_widget is not None
    buttons = cell_widget.findChildren(QPushButton)
    assert len(buttons) == 2  # editar y eliminar

    # Botón "Nuevo Paquete"
    add_btn = None
    for btn in widget.findChildren(QPushButton):
        if "Nuevo Paquete" in btn.text():
            add_btn = btn
            break
    assert add_btn is not None


def test_package_dialog_create(qtbot, mocker):
    """Prueba la creación de un nuevo paquete."""
    # Mockear add_package
    mock_add = mocker.patch("ui.package_management.add_package")
    mock_add.return_value = mocker.Mock(id=1)

    dialog = PackageDialog()
    qtbot.addWidget(dialog)

    # Llenar el formulario
    dialog.name_input.setText("Pack Test")
    dialog.desc_input.setPlainText("Descripción de prueba")
    dialog.classes_input.setValue(8)
    dialog.validity_input.setValue(45)
    dialog.price_input.setValue(120.50)
    dialog.active_check.setChecked(True)

    # Simular clic en guardar
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog.save_package()

    # Verificar que se llamó a add_package con los parámetros correctos
    mock_add.assert_called_once_with(
        name="Pack Test",
        description="Descripción de prueba",
        total_classes=8,
        validity_days=45,
        price=120.5,
        is_active=True
    )


def test_package_dialog_edit(qtbot, mocker):
    """Prueba la edición de un paquete existente."""
    # Crear un paquete simulado
    mock_pkg = mocker.Mock()
    mock_pkg.name = "Pack Original"
    mock_pkg.description = "Descripción original"
    mock_pkg.total_classes = 5
    mock_pkg.validity_days = 30
    mock_pkg.price = 60.0
    mock_pkg.is_active = True

    # Mockear get_session y session.get
    mock_session = mocker.Mock()
    mock_session.get.return_value = mock_pkg
    mocker.patch("ui.package_management.get_session", return_value=mock_session)

    # Mockear update_package
    mock_update = mocker.patch("ui.package_management.update_package")
    mock_update.return_value = True

    dialog = PackageDialog(package_id=1)
    qtbot.addWidget(dialog)

    # Verificar que los datos se cargaron
    assert dialog.name_input.text() == "Pack Original"
    assert dialog.desc_input.toPlainText() == "Descripción original"
    assert dialog.classes_input.value() == 5
    assert dialog.validity_input.value() == 30
    assert dialog.price_input.value() == 60.0
    assert dialog.active_check.isChecked() is True

    # Modificar algún campo
    dialog.name_input.setText("Pack Modificado")
    dialog.price_input.setValue(70.0)

    # Guardar
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog.save_package()

    # Verificar que se llamó a update_package con los nuevos valores
    mock_update.assert_called_once_with(
        package_id=1,
        name="Pack Modificado",
        description="Descripción original",
        total_classes=5,
        validity_days=30,
        price=70.0,
        is_active=True
    )
