from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
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
from ui.reports_widget import ReportsWidget
from ui.class_reservation_dialog import ClassReservationDialog

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

        # Crear barra de menú
        self.create_menu_bar()

        # Crear barra de herramientas
        # self.create_toolbar()

        # Crear área central
        central_widget = QWidget()
        main_layout = QHBoxLayout()

        # Panel lateral (sidebar)
        # sidebar = self.create_sidebar()
        # main_layout.addWidget(sidebar, 1)

        # Área de contenido principal
        self.content_area = QTabWidget()
        self.setup_tabs()
        main_layout.addWidget(self.content_area, 4)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Barra de estado
        self.statusBar().showMessage(
            f"Usuario: {self.user.name} | Rol: {self.user.role.value}"
        )

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Menú Archivo
        file_menu = menubar.addMenu("Archivo")

        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Menú Ayuda
        help_menu = menubar.addMenu("Ayuda")

        about_action = QAction("Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        toolbar = self.addToolBar("Herramientas")

        dashboard_btn = QPushButton("Dashboard")
        dashboard_btn.clicked.connect(
            lambda: self.content_area.setCurrentIndex(0)
        )
        toolbar.addWidget(dashboard_btn)

        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            users_btn = QPushButton("Usuarios")
            users_btn.clicked.connect(
                lambda: self.content_area.setCurrentIndex(1)
            )
            toolbar.addWidget(users_btn)

        classes_btn = QPushButton("Clases")
        classes_btn.clicked.connect(
            lambda: self.content_area.setCurrentIndex(2)
        )
        toolbar.addWidget(classes_btn)

    # def create_sidebar(self):
    #     sidebar = QListWidget()
    #     sidebar.setFixedWidth(200)
    #
    #     items = [
    #         "📊 Dashboard",
    #         "👥 Usuarios" if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST] else None,
    #         "🎯 Clases",
    #         "🏢 Centros" if self.user.role == Role.ADMINISTRATOR else None,
    #         "📋 Asistencia" if self.user.role == Role.TEACHER else None,
    #         "💰 Pagos",
    #         "📈 Reportes" if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST] else None,
    #         "⚙️ Configuración" if self.user.role == Role.ADMINISTRATOR else None
    #     ]
    #
    #     for item in items:
    #         if item:
    #             sidebar.addItem(item)
    #
    #     sidebar.currentRowChanged.connect(self.change_tab)
    #     return sidebar

    def setup_tabs(self):
        # Dashboard
        self.dashboard_widget = DashboardWidget(self.user)
        self.content_area.addTab(self.dashboard_widget, "📊 Dashboard")

        # Gestión de Usuarios (solo admin/recepcionista)
        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.user_widget = UserManagementWidget(self.user)
            self.content_area.addTab(self.user_widget, "👥 Usuarios")

        # Gestión de Clases
        self.class_widget = ClassManagementWidget(self.user)
        self.content_area.addTab(self.class_widget, "🎯 Clases")

        # Gestión de Centros (solo admin)
        if self.user.role == Role.ADMINISTRATOR:
            self.center_widget = CenterManagementWidget(self.user)
            self.content_area.addTab(self.center_widget, "🏢 Centros")

        # Asistencia (solo profesores)
        if self.user.role == Role.TEACHER:
            self.attendance_widget = AttendanceWidget(self.user)
            self.content_area.addTab(self.attendance_widget, "📋 Asistencia")

        # Reportes (admin/recepcionista)
        if self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.reports_widget = ReportsWidget(self.user)
            self.content_area.addTab(self.reports_widget, "📈 Reportes")
            self.payments_widget = PaymentsWidget(self.user)
            self.content_area.addTab(self.payments_widget, "💰 Pagos")

        # if self.user.role == Role.RECEPTIONIST:
        #     receptionist_payment_btn = QPushButton("💳 Pagos Recepcionista")
        #     receptionist_payment_btn.clicked.connect(self.show_receptionist_payment_dialog)
        #
        #
        if self.user.role == Role.STUDENT:
            reserve_button = QPushButton("Reservar Clase")
            reserve_button.clicked.connect(self.show_reservation_dialog)

        if self.user.role in [
            Role.ADMINISTRATOR,
            Role.RECEPTIONIST,
            Role.STUDENT,
            Role.TEACHER,
        ]:
            self.payments_widget = PaymentsWidget(self.user)
            self.content_area.addTab(self.payments_widget, "💰 Pagos")

    def show_reservation_dialog(self):
        """Mostrar diálogo de reserva de clases."""
        dialog = ClassReservationDialog(self.user)
        dialog.exec()

    def change_tab(self, index):
        self.content_area.setCurrentIndex(index)

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
