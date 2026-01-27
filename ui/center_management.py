from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout,
    QDialogButtonBox, QLineEdit
)
from database.db import get_session, select, Center, add_center, Role, delete_center, update_center

class CenterManagementWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_centers()

    def init_ui(self):
        layout = QVBoxLayout()

        # Barra de herramientas
        toolbar = QHBoxLayout()

        add_btn = QPushButton("➕ Nuevo Centro")
        add_btn.clicked.connect(self.show_add_center_dialog)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_centers)

        toolbar.addWidget(add_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()

        # Tabla de centros
        self.centers_table = QTableWidget()
        self.centers_table.setColumnCount(5)
        self.centers_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Dirección", "Teléfono", "Acciones"
        ])
        self.centers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(toolbar)
        layout.addWidget(self.centers_table)
        self.setLayout(layout)

    def load_centers(self):
        session = get_session()
        try:
            centers = session.exec(select(Center)).all()
            self.display_centers(centers)
        finally:
            session.close()

    def display_centers(self, centers):
        self.centers_table.setRowCount(len(centers))

        for row, center in enumerate(centers):
            self.centers_table.setItem(row, 0, QTableWidgetItem(str(center.id)))
            self.centers_table.setItem(row, 1, QTableWidgetItem(center.name))
            self.centers_table.setItem(row, 2, QTableWidgetItem(center.address))
            self.centers_table.setItem(row, 3, QTableWidgetItem(center.phone))

            if self.current_user.role in [
            Role.ADMINISTRATOR,
            Role.RECEPTIONIST,
            ]:
                # Botones de acción
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(0, 0, 0, 0)

                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(30, 30)
                edit_btn.clicked.connect(
                    lambda checked, center_id=center.id: self.edit_center(center_id)
                )

                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.clicked.connect(
                    lambda checked, center_id=center.id: self.delete_center(center_id)
                )

                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                action_widget.setLayout(action_layout)
                self.centers_table.setCellWidget(row, 4, action_widget)

    def edit_center(self, center_id):
        dialog = EditCenterDialog(center_id, self)
        if dialog.exec():
            self.load_centers()

    def delete_center(self, center_id):
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro que desea eliminar este centro?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if delete_center(center_id):
                    QMessageBox.information(self, "Éxito", "Centro eliminado correctamente")
                    self.load_centers()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar el centro")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar el centro: {str(e)}")


    def show_add_center_dialog(self):
        dialog = AddCenterDialog(self)
        if dialog.exec():
            self.load_centers()

class AddCenterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Centro")
        self.setFixedSize(400, 250)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.create_center)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Dirección:", self.address_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow(buttons)

        self.setLayout(layout)

    def create_center(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip()
        phone = self.phone_input.text().strip()

        if not name or not address:
            QMessageBox.warning(self, "Error", "Nombre y dirección son obligatorios")
            return

        try:
            add_center(name=name, address=address, phone=phone)
            QMessageBox.information(self, "Éxito", "Centro creado correctamente")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el centro: {str(e)}")

class EditCenterDialog(QDialog):
    def __init__(self, center_id, parent=None):
        super().__init__(parent)
        self.center_id = center_id
        self.setWindowTitle("Editar Centro")
        self.setFixedSize(400, 250)
        self.init_ui()
        self.load_center_data()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_changes)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Dirección:", self.address_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_center_data(self):
        session = get_session()
        try:
            center = session.get(Center, self.center_id)
            if not center:
                QMessageBox.warning(self, "Error", "Centro no encontrado")
                self.reject()
                return

            self.name_input.setText(center.name)
            self.address_input.setText(center.address)
            self.phone_input.setText(center.phone if center.phone else "")
        finally:
            session.close()

    def save_changes(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip()
        phone = self.phone_input.text().strip()

        if not name or not address:
            QMessageBox.warning(self, "Error", "Nombre y dirección son obligatorios")
            return

        try:
            if update_center(self.center_id, name=name, address=address, phone=phone):
                QMessageBox.information(self, "Éxito", "Centro actualizado correctamente")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar el centro")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el centro: {str(e)}")
