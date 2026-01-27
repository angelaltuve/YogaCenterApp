from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (  # Agregar QDialog y QCheckBox
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
    delete_user,
    get_session,
    search_users,
    select,
    update_role,
    update_user,
)
from services.services import UserService


class UserManagementWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.user_service = UserService()
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
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Email", "Teléfono", "Rol", "Estado", "Acciones"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

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

            # Botones de acción
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.clicked.connect(lambda checked, uid=user.id: self.edit_user(uid))

            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.clicked.connect(lambda checked, uid=user.id: self.delete_user(uid))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            action_widget.setLayout(action_layout)

            self.users_table.setCellWidget(row, 6, action_widget)

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
            self, "Confirmar",
            "¿Está seguro que desea eliminar este usuario?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if delete_user(user_id):
                QMessageBox.information(self, "Éxito", "Usuario eliminado correctamente")
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el usuario")

class AddUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Usuario")
        self.setFixedSize(400, 350)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value for role in Role])

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.create_user)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow("Contraseña:", self.password_input)
        layout.addRow("Rol:", self.role_combo)
        layout.addRow(buttons)

        self.setLayout(layout)

    def create_user(self):
        from database.db import Add_User, Role

        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        password = self.password_input.text()
        role = Role(self.role_combo.currentText())

        if not name or not email or not password:
            QMessageBox.warning(self, "Error", "Nombre, email y contraseña son obligatorios")
            return

        try:
            user = Add_User(name=name, email=email, phone=phone, password=password, role=role)
            if user:
                QMessageBox.information(self, "Éxito", "Usuario creado correctamente")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "El email ya está registrado")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear el usuario: {str(e)}")

class EditUserDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Editar Usuario")
        self.setFixedSize(400, 350)
        self.init_ui()
        self.load_user_data()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems([role.value for role in Role])

        self.is_active_check = QCheckBox("Usuario Activo")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_changes)
        buttons.rejected.connect(self.reject)

        layout.addRow("Nombre:", self.name_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Teléfono:", self.phone_input)
        layout.addRow("Rol:", self.role_combo)
        layout.addRow(self.is_active_check)
        layout.addRow(buttons)

        self.setLayout(layout)

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

        try:
            success = update_user(
                user_id=self.user_id,
                name=name,
                email=email,
                phone=phone,
                role=role,
                is_active=is_active
            )

            if success:
                QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar el usuario")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al actualizar: {str(e)}")
