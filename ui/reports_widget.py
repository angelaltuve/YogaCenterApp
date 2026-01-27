from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QTextEdit, QTabWidget, QGridLayout, QProgressBar,
    QFileDialog, QCheckBox, QApplication
)
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from datetime import datetime, timedelta
import csv
import json
import os
from database.db import (
    get_session, select, Payment, User, YogaClass, Role,
    Center, Attendance, Reserve, get_all_payments,
    get_attendance_by_class, get_classes_by_date, get_users_by_role,
    get_payments_by_teacher, get_total_earnings_by_teacher,
    get_student_statistics, get_teacher_statistics,
    get_all_centers, get_classes_by_teacher
)

class ReportsWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Título
        title = QLabel("📊 Sistema de Reportes")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; padding: 10px;")
        layout.addWidget(title)

        # Pestañas para diferentes tipos de reportes
        self.tabs = QTabWidget()

        # Reporte Financiero
        financial_tab = self.create_financial_report_tab()
        self.tabs.addTab(financial_tab, "💰 Financiero")

        # Reporte de Asistencia
        attendance_tab = self.create_attendance_report_tab()
        self.tabs.addTab(attendance_tab, "📋 Asistencia")

        # Reporte de Clases
        class_tab = self.create_class_report_tab()
        self.tabs.addTab(class_tab, "🎯 Clases")

        # Reporte de Usuarios
        user_tab = self.create_user_report_tab()
        self.tabs.addTab(user_tab, "👥 Usuarios")

        # Reporte de Profesores
        teacher_tab = self.create_teacher_report_tab()
        self.tabs.addTab(teacher_tab, "🧘 Profesores")

        # Dashboard Ejecutivo (solo admin)
        if self.current_user.role == Role.ADMINISTRATOR:
            dashboard_tab = self.create_executive_dashboard_tab()
            self.tabs.addTab(dashboard_tab, "📈 Dashboard")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def create_financial_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("🔍 Filtros del Reporte")
        filter_layout = QVBoxLayout()

        # Fila 1
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("📅 Período:"))

        self.fin_start_date = QDateEdit()
        self.fin_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.fin_start_date.setCalendarPopup(True)
        row1_layout.addWidget(self.fin_start_date)

        row1_layout.addWidget(QLabel("a"))

        self.fin_end_date = QDateEdit()
        self.fin_end_date.setDate(QDate.currentDate())
        self.fin_end_date.setCalendarPopup(True)
        row1_layout.addWidget(self.fin_end_date)

        row1_layout.addWidget(QLabel("🏢 Centro:"))
        self.fin_center_combo = QComboBox()
        self.fin_center_combo.addItem("Todos los centros", None)
        row1_layout.addWidget(self.fin_center_combo)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        # Fila 2
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("📊 Tipo:"))

        self.fin_report_type = QComboBox()
        self.fin_report_type.addItems([
            "Resumen General",
            "Detalle de Pagos",
            "Ingresos por Centro",
            "Ingresos por Método de Pago"
        ])
        row2_layout.addWidget(self.fin_report_type)

        row2_layout.addWidget(QLabel("💳 Estado:"))
        self.fin_status_combo = QComboBox()
        self.fin_status_combo.addItems(["Todos", "paid", "pending", "refunded"])
        row2_layout.addWidget(self.fin_status_combo)

        row2_layout.addStretch()

        generate_btn = QPushButton("🔄 Generar Reporte")
        generate_btn.clicked.connect(self.generate_financial_report)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        row2_layout.addWidget(generate_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Panel de estadísticas
        stats_group = QGroupBox("📈 Estadísticas Financieras")
        stats_layout = QGridLayout()

        self.total_revenue_label = QLabel("💰 Ingresos Totales:\n$0.00")
        self.monthly_revenue_label = QLabel("📅 Ingresos del Mes:\n$0.00")
        self.avg_payment_label = QLabel("📊 Pago Promedio:\n$0.00")
        self.pending_payments_label = QLabel("⏳ Pagos Pendientes:\n0")
        self.refunded_payments_label = QLabel("↩️ Pagos Reembolsados:\n0")
        self.top_student_label = QLabel("🏆 Top Estudiante:\nN/A")

        for label in [self.total_revenue_label, self.monthly_revenue_label,
                     self.avg_payment_label, self.pending_payments_label,
                     self.refunded_payments_label, self.top_student_label]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }
            """)

        stats_layout.addWidget(self.total_revenue_label, 0, 0)
        stats_layout.addWidget(self.monthly_revenue_label, 0, 1)
        stats_layout.addWidget(self.avg_payment_label, 0, 2)
        stats_layout.addWidget(self.pending_payments_label, 1, 0)
        stats_layout.addWidget(self.refunded_payments_label, 1, 1)
        stats_layout.addWidget(self.top_student_label, 1, 2)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Tabla de resultados
        self.financial_table = QTableWidget()
        self.financial_table.setColumnCount(0)
        self.financial_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.financial_table)

        # Botones de exportación
        export_layout = QHBoxLayout()

        export_csv_btn = QPushButton("📥 Exportar a CSV")
        export_csv_btn.clicked.connect(self.export_financial_csv)
        export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        export_pdf_btn = QPushButton("📄 Generar PDF")
        export_pdf_btn.clicked.connect(self.export_financial_pdf)
        export_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        export_layout.addWidget(export_csv_btn)
        export_layout.addWidget(export_pdf_btn)
        export_layout.addStretch()

        layout.addLayout(export_layout)

        widget.setLayout(layout)
        return widget

    def create_attendance_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("🔍 Filtros de Asistencia")
        filter_layout = QVBoxLayout()

        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("📅 Desde:"))

        self.att_start_date = QDateEdit()
        self.att_start_date.setDate(QDate.currentDate().addMonths(-1))
        row1_layout.addWidget(self.att_start_date)

        row1_layout.addWidget(QLabel("Hasta:"))
        self.att_end_date = QDateEdit()
        self.att_end_date.setDate(QDate.currentDate())
        row1_layout.addWidget(self.att_end_date)

        row1_layout.addWidget(QLabel("🏢 Centro:"))
        self.att_center_combo = QComboBox()
        self.att_center_combo.addItem("Todos los centros", None)
        row1_layout.addWidget(self.att_center_combo)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("👨‍🏫 Profesor:"))
        self.att_teacher_combo = QComboBox()
        self.att_teacher_combo.addItem("Todos los profesores", None)
        row2_layout.addWidget(self.att_teacher_combo)

        row2_layout.addWidget(QLabel("📊 Tipo:"))
        self.att_report_type = QComboBox()
        self.att_report_type.addItems([
            "Resumen por Clase",
            "Detalle de Asistencia",
            "Estadísticas por Estudiante",
            "Tendencias de Asistencia"
        ])
        row2_layout.addWidget(self.att_report_type)

        row2_layout.addStretch()

        generate_btn = QPushButton("🔄 Generar Reporte")
        generate_btn.clicked.connect(self.generate_attendance_report)
        row2_layout.addWidget(generate_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Estadísticas
        self.att_stats_label = QLabel("📊 Cargando estadísticas...")
        self.att_stats_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.att_stats_label)

        # Tabla de resultados
        self.attendance_table = QTableWidget()
        self.attendance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.attendance_table)

        widget.setLayout(layout)
        return widget

    def create_class_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("🔍 Filtros de Clases")
        filter_layout = QVBoxLayout()

        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("📅 Mes:"))

        self.class_month_combo = QComboBox()
        current_month = datetime.now().month
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        for i, month in enumerate(months, 1):
            self.class_month_combo.addItem(f"{month} 2024", i)

        self.class_month_combo.setCurrentIndex(current_month - 1)
        row1_layout.addWidget(self.class_month_combo)

        row1_layout.addWidget(QLabel("🏢 Centro:"))
        self.class_center_combo = QComboBox()
        self.class_center_combo.addItem("Todos los centros", None)
        row1_layout.addWidget(self.class_center_combo)

        row1_layout.addWidget(QLabel("👨‍🏫 Profesor:"))
        self.class_teacher_combo = QComboBox()
        self.class_teacher_combo.addItem("Todos los profesores", None)
        row1_layout.addWidget(self.class_teacher_combo)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("📊 Vista:"))

        self.class_view_type = QComboBox()
        self.class_view_type.addItems([
            "Calendario de Clases",
            "Ocupación por Horario",
            "Clases Más Populares",
            "Análisis de Rentabilidad"
        ])
        row2_layout.addWidget(self.class_view_type)

        row2_layout.addStretch()

        generate_btn = QPushButton("🔄 Generar Reporte")
        generate_btn.clicked.connect(self.generate_class_report)
        row2_layout.addWidget(generate_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla de clases
        self.classes_table = QTableWidget()
        self.classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.classes_table)

        widget.setLayout(layout)
        return widget

    def create_user_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("🔍 Filtros de Usuarios")
        filter_layout = QVBoxLayout()

        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("👤 Rol:"))

        self.user_role_combo = QComboBox()
        self.user_role_combo.addItems(["Todos", "STUDENT", "TEACHER", "RECEPTIONIST", "ADMINISTRATOR"])
        row1_layout.addWidget(self.user_role_combo)

        row1_layout.addWidget(QLabel("📅 Registrados desde:"))

        self.user_start_date = QDateEdit()
        self.user_start_date.setDate(QDate.currentDate().addMonths(-6))
        row1_layout.addWidget(self.user_start_date)

        row1_layout.addWidget(QLabel("Estado:"))
        self.user_status_combo = QComboBox()
        self.user_status_combo.addItems(["Todos", "Activos", "Inactivos"])
        row1_layout.addWidget(self.user_status_combo)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("📊 Reporte:"))

        self.user_report_type = QComboBox()
        self.user_report_type.addItems([
            "Listado de Usuarios",
            "Crecimiento de Usuarios",
            "Actividad por Rol",
            "Estadísticas de Estudiantes"
        ])
        row2_layout.addWidget(self.user_report_type)

        row2_layout.addStretch()

        generate_btn = QPushButton("🔄 Generar Reporte")
        generate_btn.clicked.connect(self.generate_user_report)
        row2_layout.addWidget(generate_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla de usuarios
        self.users_table = QTableWidget()
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.users_table)

        widget.setLayout(layout)
        return widget

    def create_teacher_report_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("🔍 Filtros de Profesores")
        filter_layout = QVBoxLayout()

        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("👨‍🏫 Profesor:"))

        self.teacher_combo = QComboBox()
        self.teacher_combo.addItem("Todos los profesores", None)
        row1_layout.addWidget(self.teacher_combo)

        row1_layout.addWidget(QLabel("📅 Período:"))

        self.teacher_start_date = QDateEdit()
        self.teacher_start_date.setDate(QDate.currentDate().addMonths(-3))
        row1_layout.addWidget(self.teacher_start_date)

        row1_layout.addWidget(QLabel("a"))

        self.teacher_end_date = QDateEdit()
        self.teacher_end_date.setDate(QDate.currentDate())
        row1_layout.addWidget(self.teacher_end_date)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("📊 Métrica:"))

        self.teacher_metric = QComboBox()
        self.teacher_metric.addItems([
            "Rendimiento General",
            "Ganancias Detalladas",
            "Asistencia de Estudiantes",
            "Clases Impartidas"
        ])
        row2_layout.addWidget(self.teacher_metric)

        row2_layout.addStretch()

        generate_btn = QPushButton("🔄 Generar Reporte")
        generate_btn.clicked.connect(self.generate_teacher_report)
        row2_layout.addWidget(generate_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla de profesores
        self.teachers_table = QTableWidget()
        self.teachers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.teachers_table)

        widget.setLayout(layout)
        return widget

    def create_executive_dashboard_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # KPI Cards
        kpi_layout = QGridLayout()

        self.kpi_total_revenue = self.create_kpi_card("💰 Ingresos Totales", "$0.00", "#2ecc71")
        self.kpi_total_users = self.create_kpi_card("👥 Usuarios Activos", "0", "#3498db")
        self.kpi_total_classes = self.create_kpi_card("🎯 Clases Este Mes", "0", "#e74c3c")
        self.kpi_occupancy_rate = self.create_kpi_card("📊 Tasa de Ocupación", "0%", "#f39c12")
        self.kpi_avg_attendance = self.create_kpi_card("✅ Asistencia Promedio", "0%", "#9b59b6")
        self.kpi_new_students = self.create_kpi_card("🎓 Nuevos Estudiantes", "0", "#1abc9c")

        kpi_layout.addWidget(self.kpi_total_revenue, 0, 0)
        kpi_layout.addWidget(self.kpi_total_users, 0, 1)
        kpi_layout.addWidget(self.kpi_total_classes, 0, 2)
        kpi_layout.addWidget(self.kpi_occupancy_rate, 1, 0)
        kpi_layout.addWidget(self.kpi_avg_attendance, 1, 1)
        kpi_layout.addWidget(self.kpi_new_students, 1, 2)

        layout.addLayout(kpi_layout)

        # Gráficos (simulados con tablas)
        charts_layout = QHBoxLayout()

        # Gráfico de ingresos mensuales
        revenue_group = QGroupBox("📈 Ingresos Mensuales")
        revenue_layout = QVBoxLayout()
        self.revenue_table = QTableWidget()
        self.revenue_table.setColumnCount(2)
        self.revenue_table.setHorizontalHeaderLabels(["Mes", "Ingresos"])
        self.revenue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        revenue_layout.addWidget(self.revenue_table)
        revenue_group.setLayout(revenue_layout)

        # Gráfico de clases populares
        classes_group = QGroupBox("🏆 Clases Más Populares")
        classes_layout = QVBoxLayout()
        self.classes_popularity_table = QTableWidget()
        self.classes_popularity_table.setColumnCount(2)
        self.classes_popularity_table.setHorizontalHeaderLabels(["Clase", "Ocupación"])
        self.classes_popularity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        classes_layout.addWidget(self.classes_popularity_table)
        classes_group.setLayout(classes_layout)

        charts_layout.addWidget(revenue_group, 2)
        charts_layout.addWidget(classes_group, 1)

        layout.addLayout(charts_layout)

        # Botón de actualización
        update_btn = QPushButton("🔄 Actualizar Dashboard")
        update_btn.clicked.connect(self.update_executive_dashboard)
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
        """)
        layout.addWidget(update_btn)

        widget.setLayout(layout)
        return widget

    def create_kpi_card(self, title, value, color):
        """Crear una tarjeta KPI para el dashboard."""
        card = QGroupBox(title)
        card.setStyleSheet(f"""
            QGroupBox {{
                border: 2px solid {color};
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {color};
            }}
        """)

        layout = QVBoxLayout()
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")

        layout.addWidget(value_label)
        card.setLayout(layout)
        return card

    def load_initial_data(self):
        """Cargar datos iniciales en los combos."""
        session = get_session()
        try:
            # Centros
            centers = get_all_centers()
            for combo in [self.fin_center_combo, self.att_center_combo,
                         self.class_center_combo]:
                combo.clear()
                combo.addItem("Todos los centros", None)
                for center in centers:
                    combo.addItem(center.name, center.id)

            # Profesores
            teachers = get_users_by_role(Role.TEACHER)
            for combo in [self.att_teacher_combo, self.class_teacher_combo,
                         self.teacher_combo]:
                combo.clear()
                combo.addItem("Todos los profesores", None)
                for teacher in teachers:
                    combo.addItem(teacher.name, teacher.id)

        finally:
            session.close()

        # Cargar datos iniciales del dashboard
        if self.current_user.role == Role.ADMINISTRATOR:
            self.update_executive_dashboard()

    # ===========================================================================
    # FUNCIONES DE REPORTES FINANCIEROS
    # ===========================================================================

    def generate_financial_report(self):
        """Generar reporte financiero."""
        start_date = datetime.combine(self.fin_start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.fin_end_date.date().toPyDate(), datetime.max.time())
        center_id = self.fin_center_combo.currentData()
        status_filter = self.fin_status_combo.currentText()
        report_type = self.fin_report_type.currentText()

        try:
            if report_type == "Resumen General":
                self.generate_financial_summary(start_date, end_date, center_id, status_filter)
            elif report_type == "Detalle de Pagos":
                self.generate_payment_details(start_date, end_date, center_id, status_filter)
            elif report_type == "Ingresos por Centro":
                self.generate_revenue_by_center(start_date, end_date, status_filter)
            elif report_type == "Ingresos por Método de Pago":
                self.generate_revenue_by_payment_method(start_date, end_date, center_id, status_filter)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    def generate_financial_summary(self, start_date, end_date, center_id, status_filter):
        """Generar resumen financiero."""
        session = get_session()
        try:
            # Obtener todos los pagos en el período
            payments = get_all_payments(start_date, end_date)

            # Aplicar filtros
            filtered_payments = []
            for payment in payments:
                if status_filter != "Todos" and payment.status != status_filter:
                    continue

                if center_id:
                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    if yoga_class and yoga_class.center_id != center_id:
                        continue

                filtered_payments.append(payment)

            # Calcular estadísticas
            total_revenue = sum(p.amount for p in filtered_payments)
            monthly_revenue = sum(p.amount for p in filtered_payments
                                if p.paid_at.month == datetime.now().month and
                                p.paid_at.year == datetime.now().year)
            avg_payment = total_revenue / len(filtered_payments) if filtered_payments else 0

            pending_count = len([p for p in filtered_payments if p.status == "pending"])
            refunded_count = len([p for p in filtered_payments if p.status == "refunded"])

            # Encontrar top estudiante
            student_totals = {}
            for payment in filtered_payments:
                if payment.status == "paid":
                    student_totals[payment.student_id] = student_totals.get(payment.student_id, 0) + payment.amount

            top_student_id = max(student_totals, key=student_totals.get) if student_totals else None
            top_student = session.get(User, top_student_id) if top_student_id else None

            # Actualizar estadísticas
            self.total_revenue_label.setText(f"💰 Ingresos Totales:\n${total_revenue:,.2f}")
            self.monthly_revenue_label.setText(f"📅 Ingresos del Mes:\n${monthly_revenue:,.2f}")
            self.avg_payment_label.setText(f"📊 Pago Promedio:\n${avg_payment:,.2f}")
            self.pending_payments_label.setText(f"⏳ Pagos Pendientes:\n{pending_count}")
            self.refunded_payments_label.setText(f"↩️ Pagos Reembolsados:\n{refunded_count}")
            self.top_student_label.setText(f"🏆 Top Estudiante:\n{top_student.name if top_student else 'N/A'}")

            # Configurar tabla
            self.financial_table.setColumnCount(6)
            self.financial_table.setHorizontalHeaderLabels([
                "Fecha", "ID Pago", "Estudiante", "Monto", "Método", "Estado"
            ])

            self.financial_table.setRowCount(len(filtered_payments))
            for row, payment in enumerate(filtered_payments):
                student = session.get(User, payment.student_id)

                self.financial_table.setItem(row, 0,
                    QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d %H:%M")))
                self.financial_table.setItem(row, 1,
                    QTableWidgetItem(str(payment.id)))
                self.financial_table.setItem(row, 2,
                    QTableWidgetItem(student.name if student else "N/A"))

                amount_item = QTableWidgetItem(f"${payment.amount:.2f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.financial_table.setItem(row, 3, amount_item)

                self.financial_table.setItem(row, 4,
                    QTableWidgetItem(payment.payment_method))

                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                    status_item.setText("✅ Pagado")
                elif payment.status == "pending":
                    status_item.setForeground(QColor("orange"))
                    status_item.setText("⏳ Pendiente")
                elif payment.status == "refunded":
                    status_item.setForeground(QColor("red"))
                    status_item.setText("↩️ Reembolsado")
                self.financial_table.setItem(row, 5, status_item)

        finally:
            session.close()

    def generate_payment_details(self, start_date, end_date, center_id, status_filter):
        """Generar detalles de pagos."""
        session = get_session()
        try:
            payments = get_all_payments(start_date, end_date)

            # Aplicar filtros
            filtered_payments = []
            for payment in payments:
                if status_filter != "Todos" and payment.status != status_filter:
                    continue

                if center_id:
                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    if yoga_class and yoga_class.center_id != center_id:
                        continue

                filtered_payments.append(payment)

            # Configurar tabla con más detalles
            self.financial_table.setColumnCount(8)
            self.financial_table.setHorizontalHeaderLabels([
                "Fecha", "ID", "Estudiante", "Clase", "Profesor", "Monto", "Método", "Estado"
            ])

            self.financial_table.setRowCount(len(filtered_payments))
            for row, payment in enumerate(filtered_payments):
                student = session.get(User, payment.student_id)
                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                teacher = session.get(User, yoga_class.teacher_id) if yoga_class else None

                self.financial_table.setItem(row, 0,
                    QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d %H:%M")))
                self.financial_table.setItem(row, 1,
                    QTableWidgetItem(str(payment.id)))
                self.financial_table.setItem(row, 2,
                    QTableWidgetItem(student.name if student else "N/A"))
                self.financial_table.setItem(row, 3,
                    QTableWidgetItem(f"Clase #{yoga_class.id}" if yoga_class else "N/A"))
                self.financial_table.setItem(row, 4,
                    QTableWidgetItem(teacher.name if teacher else "N/A"))

                amount_item = QTableWidgetItem(f"${payment.amount:.2f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.financial_table.setItem(row, 5, amount_item)

                self.financial_table.setItem(row, 6,
                    QTableWidgetItem(payment.payment_method))

                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                elif payment.status == "pending":
                    status_item.setForeground(QColor("orange"))
                elif payment.status == "refunded":
                    status_item.setForeground(QColor("red"))
                self.financial_table.setItem(row, 7, status_item)

        finally:
            session.close()

    def generate_revenue_by_center(self, start_date, end_date, status_filter):
        """Generar ingresos por centro."""
        session = get_session()
        try:
            centers = get_all_centers()
            center_revenue = {}

            for center in centers:
                payments = get_all_payments(start_date, end_date)
                center_total = 0

                for payment in payments:
                    if status_filter != "Todos" and payment.status != status_filter:
                        continue

                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    if yoga_class and yoga_class.center_id == center.id:
                        center_total += payment.amount

                center_revenue[center.name] = center_total

            # Configurar tabla
            self.financial_table.setColumnCount(2)
            self.financial_table.setHorizontalHeaderLabels(["Centro", "Ingresos"])

            self.financial_table.setRowCount(len(center_revenue))

            for row, (center_name, revenue) in enumerate(center_revenue.items()):
                self.financial_table.setItem(row, 0, QTableWidgetItem(center_name))

                revenue_item = QTableWidgetItem(f"${revenue:,.2f}")
                revenue_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.financial_table.setItem(row, 1, revenue_item)

        finally:
            session.close()

    def generate_revenue_by_payment_method(self, start_date, end_date, center_id, status_filter):
        """Generar ingresos por método de pago."""
        session = get_session()
        try:
            payments = get_all_payments(start_date, end_date)
            method_revenue = {}

            for payment in payments:
                if status_filter != "Todos" and payment.status != status_filter:
                    continue

                if center_id:
                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    if yoga_class and yoga_class.center_id != center_id:
                        continue

                method_revenue[payment.payment_method] = method_revenue.get(payment.payment_method, 0) + payment.amount

            # Configurar tabla
            self.financial_table.setColumnCount(2)
            self.financial_table.setHorizontalHeaderLabels(["Método de Pago", "Ingresos"])

            self.financial_table.setRowCount(len(method_revenue))

            for row, (method, revenue) in enumerate(method_revenue.items()):
                self.financial_table.setItem(row, 0, QTableWidgetItem(method))

                revenue_item = QTableWidgetItem(f"${revenue:,.2f}")
                revenue_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.financial_table.setItem(row, 1, revenue_item)

        finally:
            session.close()

    def export_financial_csv(self):
        """Exportar reporte financiero a CSV."""
        if self.financial_table.rowCount() == 0:
            QMessageBox.warning(self, "Advertencia", "No hay datos para exportar")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exportar a CSV", "", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)

                    # Escribir encabezados
                    headers = []
                    for col in range(self.financial_table.columnCount()):
                        headers.append(self.financial_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)

                    # Escribir datos
                    for row in range(self.financial_table.rowCount()):
                        row_data = []
                        for col in range(self.financial_table.columnCount()):
                            item = self.financial_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)

                QMessageBox.information(self, "Éxito", f"Reporte exportado a:\n{file_path}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar: {str(e)}")

    def export_financial_pdf(self):
        """Exportar reporte financiero a PDF (simulado)."""
        QMessageBox.information(
            self,
            "Exportar a PDF",
            "La exportación a PDF está en desarrollo.\n"
            "Por ahora, use la exportación a CSV."
        )

    # ===========================================================================
    # FUNCIONES DE REPORTES DE ASISTENCIA
    # ===========================================================================

    def generate_attendance_report(self):
        """Generar reporte de asistencia."""
        start_date = datetime.combine(self.att_start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.att_end_date.date().toPyDate(), datetime.max.time())
        center_id = self.att_center_combo.currentData()
        teacher_id = self.att_teacher_combo.currentData()
        report_type = self.att_report_type.currentText()

        try:
            if report_type == "Resumen por Clase":
                self.generate_attendance_by_class(start_date, end_date, center_id, teacher_id)
            elif report_type == "Detalle de Asistencia":
                self.generate_attendance_details(start_date, end_date, center_id, teacher_id)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    def generate_attendance_by_class(self, start_date, end_date, center_id, teacher_id):
        """Generar resumen de asistencia por clase."""
        session = get_session()
        try:
            # Obtener clases en el período
            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at <= end_date
            )

            if center_id:
                query = query.where(YogaClass.center_id == center_id)
            if teacher_id:
                query = query.where(YogaClass.teacher_id == teacher_id)

            classes = session.exec(query.order_by(YogaClass.scheduled_at.asc())).all()

            # Configurar tabla
            self.attendance_table.setColumnCount(7)
            self.attendance_table.setHorizontalHeaderLabels([
                "Fecha", "Hora", "Clase", "Profesor", "Inscritos", "Asistentes", "Tasa"
            ])

            self.attendance_table.setRowCount(len(classes))

            total_inscritos = 0
            total_asistentes = 0

            for row, yoga_class in enumerate(classes):
                # Fecha y hora
                self.attendance_table.setItem(row, 0,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%Y-%m-%d")))
                self.attendance_table.setItem(row, 1,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%H:%M")))
                self.attendance_table.setItem(row, 2,
                    QTableWidgetItem(f"Clase #{yoga_class.id}"))

                # Profesor
                teacher = session.get(User, yoga_class.teacher_id)
                self.attendance_table.setItem(row, 3,
                    QTableWidgetItem(teacher.name if teacher else "N/A"))

                # Inscritos
                inscritos = yoga_class.current_capacity
                self.attendance_table.setItem(row, 4, QTableWidgetItem(str(inscritos)))
                total_inscritos += inscritos

                # Asistentes
                attendances = session.exec(
                    select(Attendance).where(
                        Attendance.yogaclass_id == yoga_class.id,
                        Attendance.status == "present"
                    )
                ).all()
                asistentes = len(attendances)
                self.attendance_table.setItem(row, 5, QTableWidgetItem(str(asistentes)))
                total_asistentes += asistentes

                # Tasa de asistencia
                tasa = (asistentes / inscritos * 100) if inscritos > 0 else 0
                tasa_item = QTableWidgetItem(f"{tasa:.1f}%")
                if tasa >= 80:
                    tasa_item.setForeground(QColor("green"))
                elif tasa >= 50:
                    tasa_item.setForeground(QColor("orange"))
                else:
                    tasa_item.setForeground(QColor("red"))
                self.attendance_table.setItem(row, 6, tasa_item)

            # Actualizar estadísticas
            tasa_total = (total_asistentes / total_inscritos * 100) if total_inscritos > 0 else 0
            self.att_stats_label.setText(
                f"📊 Resumen de Asistencia\n"
                f"📅 Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}\n"
                f"🏢 Centro: {'Todos' if not center_id else self.att_center_combo.currentText()}\n"
                f"👨‍🏫 Profesor: {'Todos' if not teacher_id else self.att_teacher_combo.currentText()}\n"
                f"🎯 Total Clases: {len(classes)}\n"
                f"👥 Total Inscritos: {total_inscritos}\n"
                f"✅ Total Asistentes: {total_asistentes}\n"
                f"📊 Tasa de Asistencia: {tasa_total:.1f}%"
            )

        finally:
            session.close()

    def generate_attendance_details(self, start_date, end_date, center_id, teacher_id):
        """Generar detalle de asistencia."""
        session = get_session()
        try:
            # Obtener todas las asistencias en el período
            query = select(Attendance).where(
                Attendance.attended_at >= start_date,
                Attendance.attended_at <= end_date
            )

            attendances = session.exec(query.order_by(Attendance.attended_at.desc())).all()

            # Configurar tabla
            self.attendance_table.setColumnCount(6)
            self.attendance_table.setHorizontalHeaderLabels([
                "Fecha", "Hora", "Estudiante", "Clase", "Estado", "Observaciones"
            ])

            filtered_attendances = []
            for attendance in attendances:
                yoga_class = session.get(YogaClass, attendance.yogaclass_id)
                if not yoga_class:
                    continue

                if center_id and yoga_class.center_id != center_id:
                    continue

                if teacher_id and yoga_class.teacher_id != teacher_id:
                    continue

                filtered_attendances.append(attendance)

            self.attendance_table.setRowCount(len(filtered_attendances))

            for row, attendance in enumerate(filtered_attendances):
                yoga_class = session.get(YogaClass, attendance.yogaclass_id)
                student = session.get(User, attendance.student_id)

                self.attendance_table.setItem(row, 0,
                    QTableWidgetItem(attendance.attended_at.strftime("%Y-%m-%d") if attendance.attended_at else "N/A"))
                self.attendance_table.setItem(row, 1,
                    QTableWidgetItem(attendance.attended_at.strftime("%H:%M") if attendance.attended_at else "N/A"))
                self.attendance_table.setItem(row, 2,
                    QTableWidgetItem(student.name if student else "N/A"))
                self.attendance_table.setItem(row, 3,
                    QTableWidgetItem(f"Clase #{yoga_class.id}" if yoga_class else "N/A"))

                status_item = QTableWidgetItem(attendance.status)
                if attendance.status == "present":
                    status_item.setForeground(QColor("green"))
                    status_item.setText("✅ Presente")
                elif attendance.status == "absent":
                    status_item.setForeground(QColor("red"))
                    status_item.setText("❌ Ausente")
                elif attendance.status == "late":
                    status_item.setForeground(QColor("orange"))
                    status_item.setText("⏰ Tarde")
                self.attendance_table.setItem(row, 4, status_item)

                self.attendance_table.setItem(row, 5, QTableWidgetItem(""))

            # Actualizar estadísticas
            presentes = len([a for a in filtered_attendances if a.status == "present"])
            ausentes = len([a for a in filtered_attendances if a.status == "absent"])
            tardes = len([a for a in filtered_attendances if a.status == "late"])

            self.att_stats_label.setText(
                f"📋 Detalle de Asistencia\n"
                f"📅 Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}\n"
                f"🎯 Total Registros: {len(filtered_attendances)}\n"
                f"✅ Presentes: {presentes}\n"
                f"❌ Ausentes: {ausentes}\n"
                f"⏰ Tardes: {tardes}"
            )

        finally:
            session.close()

    # ===========================================================================
    # FUNCIONES DE REPORTES DE CLASES
    # ===========================================================================

    def generate_class_report(self):
        """Generar reporte de clases."""
        month = self.class_month_combo.currentData()
        center_id = self.class_center_combo.currentData()
        teacher_id = self.class_teacher_combo.currentData()
        view_type = self.class_view_type.currentText()

        try:
            if view_type == "Calendario de Clases":
                self.generate_class_calendar(month, center_id, teacher_id)
            elif view_type == "Clases Más Populares":
                self.generate_popular_classes(month, center_id, teacher_id)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    def generate_class_calendar(self, month, center_id, teacher_id):
        """Generar calendario de clases."""
        session = get_session()
        try:
            # Obtener clases del mes
            year = datetime.now().year
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at < end_date
            )

            if center_id:
                query = query.where(YogaClass.center_id == center_id)
            if teacher_id:
                query = query.where(YogaClass.teacher_id == teacher_id)

            classes = session.exec(query.order_by(YogaClass.scheduled_at.asc())).all()

            # Configurar tabla
            self.classes_table.setColumnCount(6)
            self.classes_table.setHorizontalHeaderLabels([
                "Fecha", "Hora", "Clase", "Profesor", "Capacidad", "Ocupación"
            ])

            self.classes_table.setRowCount(len(classes))

            total_capacity = 0
            total_booked = 0

            for row, yoga_class in enumerate(classes):
                teacher = session.get(User, yoga_class.teacher_id)

                self.classes_table.setItem(row, 0,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%Y-%m-%d")))
                self.classes_table.setItem(row, 1,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%H:%M")))
                self.classes_table.setItem(row, 2,
                    QTableWidgetItem(f"Clase #{yoga_class.id}"))
                self.classes_table.setItem(row, 3,
                    QTableWidgetItem(teacher.name if teacher else "N/A"))

                capacity_item = QTableWidgetItem(f"{yoga_class.current_capacity}/{yoga_class.max_capacity}")
                self.classes_table.setItem(row, 4, capacity_item)

                total_capacity += yoga_class.max_capacity
                total_booked += yoga_class.current_capacity

                # Ocupación
                ocupacion = (yoga_class.current_capacity / yoga_class.max_capacity * 100) if yoga_class.max_capacity > 0 else 0
                ocupacion_item = QTableWidgetItem(f"{ocupacion:.1f}%")
                if ocupacion >= 80:
                    ocupacion_item.setForeground(QColor("green"))
                elif ocupacion >= 50:
                    ocupacion_item.setForeground(QColor("orange"))
                else:
                    ocupacion_item.setForeground(QColor("red"))
                self.classes_table.setItem(row, 5, ocupacion_item)

        finally:
            session.close()

    def generate_popular_classes(self, month, center_id, teacher_id):
        """Generar clases más populares."""
        session = get_session()
        try:
            # Obtener clases del mes
            year = datetime.now().year
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at < end_date
            )

            if center_id:
                query = query.where(YogaClass.center_id == center_id)
            if teacher_id:
                query = query.where(YogaClass.teacher_id == teacher_id)

            classes = session.exec(query.order_by(YogaClass.current_capacity.desc())).all()

            # Tomar solo las 10 más populares
            top_classes = classes[:10]

            # Configurar tabla
            self.classes_table.setColumnCount(5)
            self.classes_table.setHorizontalHeaderLabels([
                "Clase", "Fecha", "Profesor", "Inscritos", "Ocupación"
            ])

            self.classes_table.setRowCount(len(top_classes))

            for row, yoga_class in enumerate(top_classes):
                teacher = session.get(User, yoga_class.teacher_id)

                self.classes_table.setItem(row, 0,
                    QTableWidgetItem(f"Clase #{yoga_class.id}"))
                self.classes_table.setItem(row, 1,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%Y-%m-%d %H:%M")))
                self.classes_table.setItem(row, 2,
                    QTableWidgetItem(teacher.name if teacher else "N/A"))
                self.classes_table.setItem(row, 3,
                    QTableWidgetItem(f"{yoga_class.current_capacity}/{yoga_class.max_capacity}"))

                # Ocupación
                ocupacion = (yoga_class.current_capacity / yoga_class.max_capacity * 100) if yoga_class.max_capacity > 0 else 0
                ocupacion_item = QTableWidgetItem(f"{ocupacion:.1f}%")
                if ocupacion >= 80:
                    ocupacion_item.setForeground(QColor("green"))
                elif ocupacion >= 50:
                    ocupacion_item.setForeground(QColor("orange"))
                else:
                    ocupacion_item.setForeground(QColor("red"))
                self.classes_table.setItem(row, 4, ocupacion_item)

        finally:
            session.close()

    # ===========================================================================
    # FUNCIONES DE REPORTES DE USUARIOS
    # ===========================================================================

    def generate_user_report(self):
        """Generar reporte de usuarios."""
        role_filter = self.user_role_combo.currentText()
        start_date = datetime.combine(self.user_start_date.date().toPyDate(), datetime.min.time())
        status_filter = self.user_status_combo.currentText()
        report_type = self.user_report_type.currentText()

        try:
            if report_type == "Listado de Usuarios":
                self.generate_user_list(role_filter, start_date, status_filter)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    def generate_user_list(self, role_filter, start_date, status_filter):
        """Generar listado de usuarios."""
        session = get_session()
        try:
            query = select(User).where(User.created_at >= start_date)

            if role_filter != "Todos":
                query = query.where(User.role == role_filter)

            users = session.exec(query.order_by(User.created_at.desc())).all()

            # Aplicar filtro de estado
            if status_filter == "Activos":
                users = [u for u in users if u.is_active]
            elif status_filter == "Inactivos":
                users = [u for u in users if not u.is_active]

            # Configurar tabla
            self.users_table.setColumnCount(6)
            self.users_table.setHorizontalHeaderLabels([
                "ID", "Nombre", "Email", "Rol", "Fecha Registro", "Estado"
            ])

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.name))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.email))
                self.users_table.setItem(row, 3, QTableWidgetItem(user.role.value))
                self.users_table.setItem(row, 4,
                    QTableWidgetItem(user.created_at.strftime("%Y-%m-%d")))

                status_item = QTableWidgetItem("✅ Activo" if user.is_active else "❌ Inactivo")
                status_item.setForeground(QColor("green") if user.is_active else QColor("red"))
                self.users_table.setItem(row, 5, status_item)

        finally:
            session.close()

    # ===========================================================================
    # FUNCIONES DE REPORTES DE PROFESORES
    # ===========================================================================

    def generate_teacher_report(self):
        """Generar reporte de profesores."""
        teacher_id = self.teacher_combo.currentData()
        start_date = datetime.combine(self.teacher_start_date.date().toPyDate(), datetime.min.time())
        end_date = datetime.combine(self.teacher_end_date.date().toPyDate(), datetime.max.time())
        metric = self.teacher_metric.currentText()

        try:
            if metric == "Rendimiento General":
                self.generate_teacher_performance(teacher_id, start_date, end_date)
            elif metric == "Ganancias Detalladas":
                self.generate_teacher_earnings(teacher_id, start_date, end_date)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al generar reporte: {str(e)}")

    def generate_teacher_performance(self, teacher_id, start_date, end_date):
        """Generar rendimiento de profesores."""
        session = get_session()
        try:
            # Obtener todos los profesores o uno específico
            if teacher_id:
                teachers = [session.get(User, teacher_id)]
            else:
                teachers = get_users_by_role(Role.TEACHER)

            # Configurar tabla
            self.teachers_table.setColumnCount(6)
            self.teachers_table.setHorizontalHeaderLabels([
                "Profesor", "Clases", "Estudiantes", "Asistencia", "Ingresos", "Rating"
            ])

            self.teachers_table.setRowCount(len(teachers))

            for row, teacher in enumerate(teachers):
                if not teacher:
                    continue

                # Clases impartidas
                classes = get_classes_by_teacher(teacher.id, None)
                classes_in_period = [c for c in classes if start_date <= c.scheduled_at <= end_date]

                # Estudiantes únicos
                student_ids = set()
                for yoga_class in classes_in_period:
                    reservations = session.exec(
                        select(Reserve).where(Reserve.yogaclass_id == yoga_class.id)
                    ).all()
                    for reservation in reservations:
                        student_ids.add(reservation.student_id)

                # Asistencia promedio
                total_attendance = 0
                total_classes = 0
                for yoga_class in classes_in_period:
                    attendances = session.exec(
                        select(Attendance).where(
                            Attendance.yogaclass_id == yoga_class.id,
                            Attendance.status == "present"
                        )
                    ).all()
                    total_attendance += len(attendances)
                    total_classes += 1

                attendance_rate = (total_attendance / (total_classes * 10)) * 100 if total_classes > 0 else 0  # Asumiendo 10 estudiantes por clase

                # Ingresos
                earnings = get_total_earnings_by_teacher(teacher.id)

                self.teachers_table.setItem(row, 0, QTableWidgetItem(teacher.name))
                self.teachers_table.setItem(row, 1, QTableWidgetItem(str(len(classes_in_period))))
                self.teachers_table.setItem(row, 2, QTableWidgetItem(str(len(student_ids))))

                attendance_item = QTableWidgetItem(f"{attendance_rate:.1f}%")
                if attendance_rate >= 80:
                    attendance_item.setForeground(QColor("green"))
                elif attendance_rate >= 60:
                    attendance_item.setForeground(QColor("orange"))
                else:
                    attendance_item.setForeground(QColor("red"))
                self.teachers_table.setItem(row, 3, attendance_item)

                earnings_item = QTableWidgetItem(f"${earnings:,.2f}")
                earnings_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.teachers_table.setItem(row, 4, earnings_item)

                # Rating (simulado)
                rating = min(5.0, attendance_rate / 20)  # Convertir porcentaje a rating 1-5
                rating_item = QTableWidgetItem("⭐" * int(rating) + "☆" * (5 - int(rating)))
                self.teachers_table.setItem(row, 5, rating_item)

        finally:
            session.close()

    def generate_teacher_earnings(self, teacher_id, start_date, end_date):
        """Generar ganancias detalladas de profesores."""
        session = get_session()
        try:
            # Obtener todos los profesores o uno específico
            if teacher_id:
                teachers = [session.get(User, teacher_id)]
            else:
                teachers = get_users_by_role(Role.TEACHER)

            # Configurar tabla
            self.teachers_table.setColumnCount(5)
            self.teachers_table.setHorizontalHeaderLabels([
                "Profesor", "Clases", "Pagos", "Total", "Por Clase"
            ])

            self.teachers_table.setRowCount(len(teachers))

            for row, teacher in enumerate(teachers):
                if not teacher:
                    continue

                # Clases impartidas en el período
                classes = get_classes_by_teacher(teacher.id, None)
                classes_in_period = [c for c in classes if start_date <= c.scheduled_at <= end_date]

                # Pagos recibidos
                payments = get_payments_by_teacher(teacher.id, start_date, end_date)
                total_earnings = get_total_earnings_by_teacher(teacher.id)

                # Calcular ganancias del período
                period_earnings = 0
                for payment in payments:
                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    if yoga_class:
                        teacher_share = payment.amount * (yoga_class.teacher_share_percentage / 100)
                        period_earnings += teacher_share

                avg_per_class = period_earnings / len(classes_in_period) if classes_in_period else 0

                self.teachers_table.setItem(row, 0, QTableWidgetItem(teacher.name))
                self.teachers_table.setItem(row, 1, QTableWidgetItem(str(len(classes_in_period))))
                self.teachers_table.setItem(row, 2, QTableWidgetItem(str(len(payments))))

                earnings_item = QTableWidgetItem(f"${period_earnings:,.2f}")
                earnings_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.teachers_table.setItem(row, 3, earnings_item)

                avg_item = QTableWidgetItem(f"${avg_per_class:,.2f}")
                avg_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.teachers_table.setItem(row, 4, avg_item)

        finally:
            session.close()

    # ===========================================================================
    # FUNCIONES DEL DASHBOARD EJECUTIVO
    # ===========================================================================

    def update_executive_dashboard(self):
        """Actualizar dashboard ejecutivo."""
        session = get_session()
        try:
            # Ingresos totales
            payments = get_all_payments()
            total_revenue = sum(p.amount for p in payments)
            self.kpi_total_revenue.layout().itemAt(0).widget().setText(f"${total_revenue:,.2f}")

            # Usuarios activos
            users = session.exec(select(User).where(User.is_active == True)).all()
            self.kpi_total_users.layout().itemAt(0).widget().setText(str(len(users)))

            # Clases este mes
            today = datetime.now()
            first_day = datetime(today.year, today.month, 1)
            if today.month == 12:
                last_day = datetime(today.year + 1, 1, 1)
            else:
                last_day = datetime(today.year, today.month + 1, 1)

            classes_this_month = session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at >= first_day,
                    YogaClass.scheduled_at < last_day
                )
            ).all()
            self.kpi_total_classes.layout().itemAt(0).widget().setText(str(len(classes_this_month)))

            # Tasa de ocupación
            total_capacity = sum(c.max_capacity for c in classes_this_month)
            total_booked = sum(c.current_capacity for c in classes_this_month)
            occupancy_rate = (total_booked / total_capacity * 100) if total_capacity > 0 else 0
            self.kpi_occupancy_rate.layout().itemAt(0).widget().setText(f"{occupancy_rate:.1f}%")

            # Asistencia promedio
            attendances = session.exec(
                select(Attendance).where(
                    Attendance.attended_at >= first_day,
                    Attendance.status == "present"
                )
            ).all()
            total_classes_with_attendance = len(set(a.yogaclass_id for a in attendances))
            avg_attendance = (len(attendances) / (total_classes_with_attendance * 10) * 100) if total_classes_with_attendance > 0 else 0  # Asumiendo 10 estudiantes por clase
            self.kpi_avg_attendance.layout().itemAt(0).widget().setText(f"{avg_attendance:.1f}%")

            # Nuevos estudiantes este mes
            new_students = session.exec(
                select(User).where(
                    User.role == Role.STUDENT,
                    User.created_at >= first_day
                )
            ).all()
            self.kpi_new_students.layout().itemAt(0).widget().setText(str(len(new_students)))

            # Ingresos mensuales (últimos 6 meses)
            self.revenue_table.setRowCount(6)
            for i in range(6):
                month = today.month - i
                year = today.year
                if month <= 0:
                    month += 12
                    year -= 1

                month_start = datetime(year, month, 1)
                if month == 12:
                    month_end = datetime(year + 1, 1, 1)
                else:
                    month_end = datetime(year, month + 1, 1)

                month_payments = get_all_payments(month_start, month_end)
                month_revenue = sum(p.amount for p in month_payments)

                month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                              "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

                self.revenue_table.setItem(i, 0, QTableWidgetItem(f"{month_names[month-1]} {year}"))
                self.revenue_table.setItem(i, 1, QTableWidgetItem(f"${month_revenue:,.2f}"))

            # Clases más populares
            all_classes = session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at >= first_day
                ).order_by(YogaClass.current_capacity.desc())
            ).all()

            top_classes = all_classes[:5]
            self.classes_popularity_table.setRowCount(len(top_classes))

            for i, yoga_class in enumerate(top_classes):
                teacher = session.get(User, yoga_class.teacher_id)
                occupancy = (yoga_class.current_capacity / yoga_class.max_capacity * 100) if yoga_class.max_capacity > 0 else 0

                self.classes_popularity_table.setItem(i, 0,
                    QTableWidgetItem(f"Clase #{yoga_class.id} ({teacher.name[:10] if teacher else 'N/A'})"))
                self.classes_popularity_table.setItem(i, 1,
                    QTableWidgetItem(f"{occupancy:.1f}%"))

        finally:
            session.close()
