from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFormLayout,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from database.db import (
    add_user,
    Role,
    user_exists,
)
import re

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle("Registro de Nuevo Usuario")
        self.setFixedSize(400, 350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("📝 Crear cuenta de estudiante")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre completo")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("correo@ejemplo.com")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Teléfono (opcional)")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Mínimo 6 caracteres")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Repetir contraseña")

        form_layout.addRow("👤 Nombre:", self.name_input)
        form_layout.addRow("📧 Email:", self.email_input)
        form_layout.addRow("📞 Teléfono:", self.phone_input)
        form_layout.addRow("🔒 Contraseña:", self.password_input)
        form_layout.addRow("🔒 Confirmar:", self.confirm_input)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.register)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def register(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip() or None
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        # Validaciones
        if not name or not email or not password:
            QMessageBox.warning(
                self,
                "Campos requeridos",
                "Nombre, email y contraseña son obligatorios.",
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

        if password != confirm:
            QMessageBox.warning(
                self, "Contraseñas no coinciden", "Las contraseñas no coinciden."
            )
            return

        if user_exists(email):
            QMessageBox.warning(
                self, "Email registrado", "Este email ya está registrado."
            )
            return

        try:
            user = add_user(
                name=name,
                email=email,
                phone=phone,
                password=password,
                role=Role.STUDENT,
            )
            if user:
                self.user = user
                QMessageBox.information(
                    self,
                    "Registro exitoso",
                    "Cuenta creada correctamente. Ya puedes iniciar sesión.",
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "No se pudo crear el usuario.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al registrar: {str(e)}")
