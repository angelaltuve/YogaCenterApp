from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QDateEdit,
    QComboBox, QDialog, QFormLayout, QDialogButtonBox,
    QLineEdit, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor
from datetime import datetime
from database.db import (
    get_session, select, Payment, User, YogaClass, Role,
    get_payments_by_teacher, get_all_payments, update_payment_status,
    get_total_earnings_by_teacher, Add_Payment, Reserve, calculate_teacher_earnings
)
from ui.payment_dialog import PaymentDialog

class PaymentsWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Pestañas diferentes según el rol
        self.tabs = QTabWidget()

        if self.current_user.role == Role.STUDENT:
            self.tabs.addTab(self.create_student_payments_tab(), "Mis Pagos")
            self.load_student_payments()
        elif self.current_user.role == Role.TEACHER:
            self.tabs.addTab(self.create_teacher_earnings_tab(), "Mis Ganancias")
            self.load_teacher_earnings()
        elif self.current_user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.tabs.addTab(self.create_admin_payments_tab(), "Gestión de Pagos")
            self.load_admin_payments()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def create_student_payments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Botón para realizar pago
        button_layout = QHBoxLayout()
        pay_button = QPushButton("💳 Realizar Pago")
        pay_button.clicked.connect(self.show_payment_dialog)

        refresh_button = QPushButton("🔄 Actualizar")
        refresh_button.clicked.connect(self.load_student_payments)

        button_layout.addWidget(pay_button)
        button_layout.addWidget(refresh_button)
        button_layout.addStretch()

        # Tabla de pagos del estudiante
        self.student_payments_table = QTableWidget()
        self.student_payments_table.setColumnCount(6)
        self.student_payments_table.setHorizontalHeaderLabels([
            "ID", "Clase", "Fecha", "Monto", "Método", "Estado"
        ])
        self.student_payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(button_layout)
        layout.addWidget(self.student_payments_table)
        widget.setLayout(layout)

        return widget

    def create_teacher_earnings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Estadísticas del profesor
        stats_layout = QHBoxLayout()

        self.earnings_label = QLabel("💰 Cargando...")
        self.earnings_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;")

        stats_layout.addWidget(self.earnings_label)
        stats_layout.addStretch()

        # Filtros por fecha
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Desde:"))
        self.teacher_start_date = QDateEdit()
        self.teacher_start_date.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.teacher_start_date)

        filter_layout.addWidget(QLabel("Hasta:"))
        self.teacher_end_date = QDateEdit()
        self.teacher_end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.teacher_end_date)

        filter_btn = QPushButton("Filtrar")
        filter_btn.clicked.connect(self.load_teacher_earnings)
        filter_layout.addWidget(filter_btn)

        # Tabla de ganancias
        self.teacher_earnings_table = QTableWidget()
        self.teacher_earnings_table.setColumnCount(5)
        self.teacher_earnings_table.setHorizontalHeaderLabels([
            "Fecha", "Clase", "Alumno", "Monto", "Estado"
        ])
        self.teacher_earnings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(stats_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.teacher_earnings_table)
        widget.setLayout(layout)

        return widget

    def create_admin_payments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Estado:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Todos", "paid", "pending", "refunded"])
        self.status_combo.currentTextChanged.connect(self.load_admin_payments)

        filter_layout.addWidget(QLabel("Desde:"))
        self.admin_start_date = QDateEdit()
        self.admin_start_date.setDate(QDate.currentDate().addMonths(-1))

        filter_layout.addWidget(QLabel("Hasta:"))
        self.admin_end_date = QDateEdit()
        self.admin_end_date.setDate(QDate.currentDate())

        filter_btn = QPushButton("Filtrar")
        filter_btn.clicked.connect(self.load_admin_payments)

        filter_layout.addWidget(self.status_combo)
        filter_layout.addWidget(self.admin_start_date)
        filter_layout.addWidget(self.admin_end_date)
        filter_layout.addWidget(filter_btn)
        filter_layout.addStretch()

        # Estadísticas
        stats_layout = QHBoxLayout()
        self.total_revenue_label = QLabel("Ingresos Totales: $0.00")
        self.monthly_revenue_label = QLabel("Ingresos del Mes: $0.00")
        self.pending_payments_label = QLabel("Pagos Pendientes: 0")

        for label in [self.total_revenue_label, self.monthly_revenue_label, self.pending_payments_label]:
            label.setStyleSheet("font-size: 14px; padding: 5px; background-color: #f8f9fa; border-radius: 5px;")

        stats_layout.addWidget(self.total_revenue_label)
        stats_layout.addWidget(self.monthly_revenue_label)
        stats_layout.addWidget(self.pending_payments_label)
        stats_layout.addStretch()

        # Tabla de pagos
        self.admin_payments_table = QTableWidget()
        self.admin_payments_table.setColumnCount(8)
        self.admin_payments_table.setHorizontalHeaderLabels([
            "ID", "Alumno", "Profesor", "Clase", "Fecha", "Monto", "Método", "Estado"
        ])
        self.admin_payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addLayout(filter_layout)
        layout.addLayout(stats_layout)
        layout.addWidget(self.admin_payments_table)
        widget.setLayout(layout)

        return widget

    def load_student_payments(self):
        session = get_session()
        try:
            payments = session.exec(
                select(Payment).where(Payment.student_id == self.current_user.id)
                .order_by(Payment.paid_at.desc())
            ).all()

            self.student_payments_table.setRowCount(len(payments))
            for row, payment in enumerate(payments):
                self.student_payments_table.setItem(row, 0, QTableWidgetItem(str(payment.id)))

                # Obtener información de la clase
                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                class_info = f"Clase {yoga_class.id}" if yoga_class else "N/A"
                self.student_payments_table.setItem(row, 1, QTableWidgetItem(class_info))

                self.student_payments_table.setItem(row, 2, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d %H:%M")))
                self.student_payments_table.setItem(row, 3, QTableWidgetItem(f"${payment.amount:.2f}"))
                self.student_payments_table.setItem(row, 4, QTableWidgetItem(payment.payment_method))

                # Estado con colores
                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                elif payment.status == "pending":
                    status_item.setForeground(QColor("orange"))
                elif payment.status == "refunded":
                    status_item.setForeground(QColor("red"))
                self.student_payments_table.setItem(row, 5, status_item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar pagos: {str(e)}")
        finally:
            session.close()

    def load_teacher_earnings(self):
        start_date = datetime.combine(self.teacher_start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.teacher_end_date.date().toPyDate(), datetime.max.time())

        session = get_session()
        try:
            # Calcular ganancias totales
            total_earnings = get_total_earnings_by_teacher(self.current_user.id)
            self.earnings_label.setText(f"💰 Ganancias Totales: ${total_earnings:.2f}")

            # Obtener pagos
            payments = get_payments_by_teacher(self.current_user.id, start_date, end_date)

            self.teacher_earnings_table.setRowCount(len(payments))
            for row, payment in enumerate(payments):
                self.teacher_earnings_table.setItem(row, 0, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d")))

                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                class_info = f"Clase {yoga_class.id}" if yoga_class else "N/A"
                self.teacher_earnings_table.setItem(row, 1, QTableWidgetItem(class_info))

                student = session.get(User, payment.student_id)
                student_name = student.name if student else "N/A"
                self.teacher_earnings_table.setItem(row, 2, QTableWidgetItem(student_name))

                self.teacher_earnings_table.setItem(row, 3, QTableWidgetItem(f"${payment.amount:.2f}"))

                # Estado
                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                self.teacher_earnings_table.setItem(row, 4, status_item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar ganancias: {str(e)}")
        finally:
            session.close()

    def load_admin_payments(self):
        start_date = datetime.combine(self.admin_start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.admin_end_date.date().toPyDate(), datetime.max.time())
        status_filter = self.status_combo.currentText()

        session = get_session()
        try:
            payments = get_all_payments(start_date, end_date)

            # Filtrar por estado
            if status_filter != "Todos":
                payments = [p for p in payments if p.status == status_filter.lower()]

            self.admin_payments_table.setRowCount(len(payments))

            total_revenue = 0
            monthly_revenue = 0
            pending_count = 0

            current_month = datetime.now().month

            for row, payment in enumerate(payments):
                self.admin_payments_table.setItem(row, 0, QTableWidgetItem(str(payment.id)))

                student = session.get(User, payment.student_id)
                student_name = student.name if student else "N/A"
                self.admin_payments_table.setItem(row, 1, QTableWidgetItem(student_name))

                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                teacher_name = "N/A"
                if yoga_class and yoga_class.teacher_id:
                    teacher = session.get(User, yoga_class.teacher_id)
                    teacher_name = teacher.name if teacher else "N/A"
                self.admin_payments_table.setItem(row, 2, QTableWidgetItem(teacher_name))

                class_info = f"Clase {yoga_class.id}" if yoga_class else "N/A"
                self.admin_payments_table.setItem(row, 3, QTableWidgetItem(class_info))

                self.admin_payments_table.setItem(row, 4, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d")))
                self.admin_payments_table.setItem(row, 5, QTableWidgetItem(f"${payment.amount:.2f}"))
                self.admin_payments_table.setItem(row, 6, QTableWidgetItem(payment.payment_method))

                # Estado con acciones
                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                elif payment.status == "pending":
                    status_item.setForeground(QColor("orange"))
                    pending_count += 1
                elif payment.status == "refunded":
                    status_item.setForeground(QColor("red"))

                self.admin_payments_table.setItem(row, 7, status_item)

                # Calcular estadísticas
                total_revenue += payment.amount
                if payment.paid_at.month == current_month:
                    monthly_revenue += payment.amount

            # Actualizar etiquetas de estadísticas
            self.total_revenue_label.setText(f"Ingresos Totales: ${total_revenue:.2f}")
            self.monthly_revenue_label.setText(f"Ingresos del Mes: ${monthly_revenue:.2f}")
            self.pending_payments_label.setText(f"Pagos Pendientes: {pending_count}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar pagos: {str(e)}")
        finally:
            session.close()

    def show_payment_dialog(self):
        """Mostrar diálogo de pago."""
        dialog = PaymentDialog(self.current_user)
        if dialog.exec():
            self.load_student_payments()
