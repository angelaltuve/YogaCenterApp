from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from database.db import authenticate


class LoginDialog(QDialog):
    login_successful = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.user = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Inicio de Sesión - Sistema de Yoga")

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Logo/título
        title = QLabel("🧘 Sistema de Gestión de Centros de Yoga")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))

        subtitle = QLabel("Inicia sesión para continuar")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Arial", 11))

        # Formulario
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.Shape.StyledPanel)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        # Email
        email_label = QLabel("📧 Email:")
        email_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("usuario@ejemplo.com")
        self.email_input.setMinimumHeight(40)

        # Contraseña
        password_label = QLabel("🔒 Contraseña:")
        password_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Ingrese su contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(40)

        # Botones
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        login_btn = QPushButton("🚀 Iniciar Sesión")
        login_btn.setObjectName("login_btn")
        login_btn.setMinimumHeight(45)
        login_btn.clicked.connect(self.authenticate)

        cancel_btn = QPushButton("❌ Cancelar")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setMinimumHeight(45)
        cancel_btn.clicked.connect(self.reject)

        # Enter key shortcut
        login_btn.setAutoDefault(True)
        login_btn.setDefault(True)

        button_layout.addWidget(login_btn)
        button_layout.addWidget(cancel_btn)

        # Agregar widgets al formulario
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(10)
        form_layout.addLayout(button_layout)

        form_frame.setLayout(form_layout)

        # Enlaces adicionales
        links_layout = QHBoxLayout()
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        register_link = QLabel(
            '<a href="register" style="color: #3498db; text-decoration: none;">📝 Crear nueva cuenta</a>'
        )
        register_link.setOpenExternalLinks(False)
        register_link.linkActivated.connect(self.show_register_dialog)
        register_link.setFont(QFont("Arial", 10))

        forgot_link = QLabel(
            '<a href="forgot" style="color: #3498db; text-decoration: none;">🔑 ¿Olvidó su contraseña?</a>'
        )
        forgot_link.setOpenExternalLinks(False)
        forgot_link.linkActivated.connect(self.show_forgot_password)
        forgot_link.setFont(QFont("Arial", 10))

        links_layout.addWidget(register_link)
        links_layout.addWidget(QLabel(" | "))
        links_layout.addWidget(forgot_link)

        # Agregar al layout principal
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(form_frame)
        layout.addLayout(links_layout)

        self.setLayout(layout)

    def authenticate(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        # Validaciones
        if not email:
            QMessageBox.warning(self, "Campo requerido", "Por favor ingrese su email")
            self.email_input.setFocus()
            return

        if not password:
            QMessageBox.warning(
                self, "Campo requerido", "Por favor ingrese su contraseña"
            )
            self.password_input.setFocus()
            return

        # Validación básica de email
        if "@" not in email or "." not in email:
            QMessageBox.warning(
                self, "Email inválido", "Por favor ingrese un email válido"
            )
            self.email_input.selectAll()
            self.email_input.setFocus()
            return

        # Mostrar indicador de carga
        self.setCursor(Qt.CursorShape.WaitCursor)

        try:
            self.user = authenticate(email, password)

            if self.user:
                if not self.user.is_active:
                    QMessageBox.warning(
                        self,
                        "Cuenta desactivada",
                        "Su cuenta ha sido desactivada. Contacte al administrador.",
                    )
                    self.user = None
                    return

                self.login_successful.emit(self.user)
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Error de autenticación",
                    "Email o contraseña incorrectos. Intente nuevamente.",
                )
                self.password_input.clear()
                self.password_input.setFocus()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error al conectar con la base de datos: {str(e)}"
            )
        finally:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def show_register_dialog(self):
        """Mostrar diálogo de registro."""
        from ui.register_dialog import RegisterDialog

        register_dialog = RegisterDialog(self)
        if register_dialog.exec():
            # Auto-completar email después del registro exitoso
            self.email_input.setText(register_dialog.user.email)
            self.password_input.setFocus()

    def show_forgot_password(self):
        """Mostrar diálogo para recuperar contraseña."""
        QMessageBox.information(
            self,
            "Recuperar contraseña",
            "Por favor contacte al administrador para recuperar su contraseña.\n\n"
            "Email: admin@yogacenter.com\n"
            "Teléfono: 123-456-7890",
        )
