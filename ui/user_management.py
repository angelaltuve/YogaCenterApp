from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.db import (
    Role,
    User,
    Center,
    delete_user,
    get_session,
    search_users,
    select,
    update_user,
    add_user,
    assign_user_to_center,
    get_user_centers,
    get_all_centers,
    UserCenter,
)
from sqlalchemy import delete
import re

class UserManagementWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_users()

    def init_ui(self):
        layout = QVBoxLayout()

        # Barra de herramientas
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o email...")
        self.search_input.textChanged.connect(self.filter_users)

        add_btn = QPushButton("➕ Nuevo Usuario")
        add_btn.clicked.connect(self.show_add_user_dialog)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_users)

        toolbar.addWidget(QLabel("Buscar:"))
        toolbar.addWidget(self.search_input)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()

        # Tabla de usuarios
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Nombre",
                "Email",
                "Teléfono",
                "Rol",
                "Estado",
                "Centros",
                "Acciones",
            ]
        )
        self.users_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addLayout(toolbar)
        layout.addWidget(self.users_table)
        self.setLayout(layout)

    def load_users(self):
        session = get_session()
        try:
            users = session.exec(select(User)).all()
            self.display_users(users)
        finally:
            session.close()

    def display_users(self, users):
        self.users_table.setRowCount(len(users))

        for row, user in enumerate(users):
            # Columnas básicas
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self.users_table.setItem(row, 1, QTableWidgetItem(user.name))
            self.users_table.setItem(row, 2, QTableWidgetItem(user.email))
            self.users_table.setItem(row, 3, QTableWidgetItem(user.phone or ""))
            self.users_table.setItem(row, 4, QTableWidgetItem(user.role.value))

            # Estado
            status_item = QTableWidgetItem("Activo" if user.is_active else "Inactivo")
            if user.is_active:
                status_item.setForeground(QColor("green"))
            else:
                status_item.setForeground(QColor("red"))
            self.users_table.setItem(row, 5, status_item)

            # Centros asignados
            user_centers = get_user_centers(user.id)
            if user_centers:
                centers_text = ", ".join(c.name for c in user_centers)
            else:
                centers_text = "Ninguno"
            self.users_table.setItem(row, 6, QTableWidgetItem(centers_text))

            # Botones de acción (columna 7)
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.clicked.connect(lambda checked, uid=user.id: self.edit_user(uid))

            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.clicked.connect(
                lambda checked, uid=user.id: self.delete_user(uid)
            )

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            action_widget.setLayout(action_layout)

            self.users_table.setCellWidget(row, 7, action_widget)

    def filter_users(self, text):
        if text.strip():
            session = get_session()
            try:
                users = search_users(text)
                self.display_users(users)
            finally:
                session.close()
        else:
            self.load_users()

    def show_add_user_dialog(self):
        dialog = AddUserDialog(self)
        if dialog.exec():
            self.load_users()

    def edit_user(self, user_id):
        dialog = EditUserDialog(user_id, self)
        if dialog.exec():
            self.load_users()

    def delete_user(self, user_id):
        if user_id == self.current_user.id:
            QMessageBox.warning(self, "Error", "No puedes eliminar tu propio usuario")
            return

        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Está seguro que desea eliminar este usuario?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if delete_user(user_id):
                QMessageBox.information(
                    self, "Éxito", "Usuario eliminado correctamente"
                )
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el usuario")


class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Usuario")
        self.setFixedSize(450, 500)
        self.init_ui()
        self.load_centers()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value for role in Role])

        # Lista de centros con checkboxes
        self.centers_list = QListWidget()
        self.centers_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.centers_list.setMaximumHeight(120)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.create_user)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow("Contraseña:", self.password_input)
        layout.addRow("Rol:", self.role_combo)
        layout.addRow("Centros asignados:", self.centers_list)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_centers(self):
        """Carga todos los centros como items checkeables."""
        centers = get_all_centers()
        for center in centers:
            item = QListWidgetItem(center.name)
            item.setData(Qt.ItemDataRole.UserRole, center.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.centers_list.addItem(item)

    def create_user(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.password_input.text()
        role = Role(self.role_combo.currentText())

        if not name or not email or not password:
            QMessageBox.warning(
                self, "Error", "Nombre, email y contraseña son obligatorios"
            )
            return

        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Email inválido", "Ingrese un email válido.")
            return

        phone_regex = r"^\+?[\d\s\-\(\)]+$"
        if phone and not re.match(phone_regex, phone):
            QMessageBox.warning(
                self,
                "Teléfono inválido",
                "El número de teléfono solo puede contener dígitos, espacios, guiones, paréntesis y un '+' al inicio.",
            )
            return

        if len(password) < 6:
            QMessageBox.warning(
                self,
                "Contraseña débil",
                "La contraseña debe tener al menos 6 caracteres.",
            )
            return


        session = get_session()
        try:
            # Crear usuario
            user = add_user(
                name=name, email=email, phone=phone, password=password, role=role
            )
            if user and user.id:
                for i in range(self.centers_list.count()):
                    item = self.centers_list.item(i)
                    if item.checkState() == Qt.CheckState.Checked:
                        center_id = item.data(Qt.ItemDataRole.UserRole)
                        assign_user_to_center(user.id, center_id)

                QMessageBox.information(self, "Éxito", "Usuario creado correctamente")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "El email ya está registrado")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo crear el usuario: {str(e)}"
            )
        finally:
            session.close()


class EditUserDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Editar Usuario")
        self.setFixedSize(450, 500)
        self.init_ui()
        self.load_centers()
        self.load_user_data()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value for role in Role])

        self.is_active_check = QCheckBox("Usuario Activo")

        # Lista de centros con checkboxes
        self.centers_list = QListWidget()
        self.centers_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.centers_list.setMaximumHeight(120)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_changes)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow("Rol:", self.role_combo)
        layout.addRow(self.is_active_check)
        layout.addRow("Centros asignados:", self.centers_list)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_centers(self):
        """Carga todos los centros como items checkeables."""
        centers = get_all_centers()
        for center in centers:
            item = QListWidgetItem(center.name)
            item.setData(Qt.ItemDataRole.UserRole, center.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.centers_list.addItem(item)

    def load_user_data(self):
        session = get_session()
        try:
            user = session.get(User, self.user_id)
            if user:
                self.name_input.setText(user.name)
                self.email_input.setText(user.email)
                self.phone_input.setText(user.phone or "")
                self.role_combo.setCurrentText(user.role.value)
                self.is_active_check.setChecked(user.is_active)

                # Obtener centros asignados al usuario (objetos Center)
                user_centers = get_user_centers(self.user_id)
                assigned_center_ids = [c.id for c in user_centers]

                # Marcar los centros correspondientes
                for i in range(self.centers_list.count()):
                    item = self.centers_list.item(i)
                    center_id = item.data(Qt.ItemDataRole.UserRole)
                    if center_id in assigned_center_ids:
                        item.setCheckState(Qt.CheckState.Checked)
        finally:
            session.close()

    def save_changes(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        role = Role(self.role_combo.currentText())
        is_active = self.is_active_check.isChecked()

        if not name or not email:
            QMessageBox.warning(self, "Error", "Nombre y email son obligatorios")
            return

        # Actualizar datos básicos del usuario
        success = update_user(
            user_id=self.user_id,
            name=name,
            email=email,
            phone=phone,
            role=role,
            is_active=is_active,
        )

        if not success:
            QMessageBox.critical(self, "Error", "No se pudo actualizar el usuario")
            return

        session = get_session()
        try:
            session.exec(delete(UserCenter).filter_by(user_id=self.user_id))
            session.commit()

            # 2. Asignar los centros seleccionados
            for i in range(self.centers_list.count()):
                item = self.centers_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    center_id = item.data(Qt.ItemDataRole.UserRole)
                    assign_user_to_center(self.user_id, center_id)

            QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(
                self, "Error", f"Error al actualizar centros: {str(e)}"
            )
        finally:
            session.close()
