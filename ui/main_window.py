from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from ui.receptionist_payment_dialog import ReceptionistPaymentDialog
from database.db import Role
from ui.attendance_widget import AttendanceWidget
from ui.center_management import CenterManagementWidget
from ui.class_management import ClassManagementWidget
from ui.dashboard import DashboardWidget
from ui.payments_widget import PaymentsWidget
from ui.reports_widget import ReportsWidget
from ui.user_management import UserManagementWidget
from ui.class_reservation_dialog import ClassReservationDialog
from ui.package_management import PackageManagementWidget


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(
            f"Sistema de Yoga - {self.user.name} ({self.user.role.value})"
        )
        self.setGeometry(100, 100, 1200, 700)

        # Área central con pestañas
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        self.content_area = QTabWidget()
        self.setup_tabs()
        self.create_menu_bar()
        main_layout.addWidget(self.content_area, 4)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Barra de estado
        self.statusBar().showMessage(
            f"Usuario: {self.user.name} | Rol: {self.user.role.value}"
        )

    # ----------------------------------------------------------------------
    # 🎯 BARRA DE MENÚ (sin navegación)
    # ----------------------------------------------------------------------
    def create_menu_bar(self):
        menubar = self.menuBar()

        # ------------------- Menú Archivo -------------------
        file_menu = menubar.addMenu("Archivo")
        exit_action = QAction("❌ Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ------------------- Menú Operaciones (recepcionista) -------------------
        if self.user.role in [Role.RECEPTIONIST]:
            oper_menu = menubar.addMenu("🛒 Operaciones")
            payment_action = QAction("💳 Registrar Pago / Vender Paquete", self)
            payment_action.triggered.connect(self.open_payment_dialog)
            oper_menu.addAction(payment_action)

        # ------------------- Menú Ayuda -------------------
        help_menu = menubar.addMenu("Ayuda")
        about_action = QAction("📄 Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    # ----------------------------------------------------------------------
    # PESTAÑAS PRINCIPALES
    # ----------------------------------------------------------------------
    def setup_tabs(self):
        self.tab_index = {}  # para recordar índices

        # Dashboard (siempre visible)
        self.dashboard_widget = DashboardWidget(self.user)
        self.content_area.addTab(self.dashboard_widget, "📊 Dashboard")
        self.tab_index["dashboard"] = 0
        current = 1

        # Gestión de Usuarios (solo admin/recepcionista)
        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.user_widget = UserManagementWidget(self.user)
            self.content_area.addTab(self.user_widget, "👥 Usuarios")
            self.tab_index["users"] = current
            current += 1

        # Gestión de Clases (todos)
        self.class_widget = ClassManagementWidget(self.user)
        self.content_area.addTab(self.class_widget, "🎯 Clases")
        self.tab_index["classes"] = current
        current += 1

        # Gestión de Centros (solo admin)
        if self.user.role == Role.ADMINISTRATOR:
            self.center_widget = CenterManagementWidget(self.user)
            self.content_area.addTab(self.center_widget, "🏢 Centros")
            self.tab_index["centers"] = current
            current += 1

        # Asistencia (solo profesores)
        if self.user.role == Role.TEACHER:
            self.attendance_widget = AttendanceWidget(self.user)
            self.content_area.addTab(self.attendance_widget, "📋 Asistencia")
            self.tab_index["attendance"] = current
            current += 1

        # Reportes (admin/recepcionista)
        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.reports_widget = ReportsWidget(self.user)
            self.content_area.addTab(self.reports_widget, "📈 Reportes")
            self.tab_index["reports"] = current
            current += 1

        # Gestión de Paquetes (solo admin y recepcionista) - MODIFICADO
        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.package_widget = PackageManagementWidget(self.user)
            self.content_area.addTab(self.package_widget, "📦 Paquetes")
            self.tab_index["packages"] = current
            current += 1

        # Pagos (solo estudiantes y profesores)
        if self.user.role in [Role.STUDENT, Role.TEACHER]:
            self.payments_widget = PaymentsWidget(self.user)
            self.content_area.addTab(self.payments_widget, "💰 Pagos")
            self.tab_index["payments"] = current

    # ----------------------------------------------------------------------
    # ACCIONES
    # ----------------------------------------------------------------------
    def open_payment_dialog(self):
        """Abre el diálogo de pago para recepcionistas/administradores."""
        dialog = ReceptionistPaymentDialog(self.user)
        dialog.exec()

    def show_reservation_dialog(self):
        """Abre el diálogo de reserva de clases para estudiantes."""
        dialog = ClassReservationDialog(self.user)
        dialog.exec()

    def show_about(self):
        QMessageBox.about(
            self,
            "Acerca de",
            "Sistema de Gestión de Centros de Yoga v1.0\n\n"
            "Desarrollado por Angel Altuve\n"
            "© 2025 Todos los derechos reservados",
        )

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Está seguro que desea salir?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
