import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QTableWidget
from ui.center_management import CenterManagementWidget, AddCenterDialog, EditCenterDialog
from database.db import Role, add_user, add_center


def test_center_management_widget_admin(qtbot, test_session):
    admin = add_user("Admin", "a@test.com", "", "pass", Role.ADMINISTRATOR)
    # Crear algunos centros
    c1 = add_center("Centro A", "Dir A", "111")
    c2 = add_center("Centro B", "Dir B", "222")

    widget = CenterManagementWidget(admin)
    qtbot.addWidget(widget)

    table = widget.centers_table
    assert table.rowCount() == 2
    assert table.item(0, 1).text() == "Centro A"
    assert table.item(1, 1).text() == "Centro B"

    # Botones de acción deben existir
    cell_widget = table.cellWidget(0, 4)
    assert cell_widget is not None
    buttons = cell_widget.findChildren(QPushButton)
    assert len(buttons) == 2  # editar y eliminar


def test_add_center_dialog(qtbot, mocker):
    mock_add_center = mocker.patch("ui.center_management.add_center")
    mock_add_center.return_value = mocker.Mock(id=1)

    dialog = AddCenterDialog()
    qtbot.addWidget(dialog)

    dialog.name_input.setText("Nuevo Centro")
    dialog.address_input.setText("Av. Siempre Viva 123")
    dialog.phone_input.setText("555-9999")

    # Aceptar
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog.create_center()

    mock_add_center.assert_called_once_with(
        name="Nuevo Centro",
        address="Av. Siempre Viva 123",
        phone="555-9999"
    )


def test_edit_center_dialog(qtbot, test_session, mocker):
    # Crear un centro real
    center = add_center("Centro Original", "Dir Orig", "000")

    # Mockear update_center
    mock_update = mocker.patch("ui.center_management.update_center")
    mock_update.return_value = True

    dialog = EditCenterDialog(center.id)
    qtbot.addWidget(dialog)

    # Verificar que los datos se cargaron
    assert dialog.name_input.text() == "Centro Original"
    assert dialog.address_input.text() == "Dir Orig"
    assert dialog.phone_input.text() == "000"

    # Modificar
    dialog.name_input.setText("Centro Modificado")
    dialog.address_input.setText("Nueva Dir")
    dialog.phone_input.setText("111")

    # Guardar
    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        dialog.save_changes()

    mock_update.assert_called_once_with(
        center.id,
        name="Centro Modificado",
        address="Nueva Dir",
        phone="111"
    )
