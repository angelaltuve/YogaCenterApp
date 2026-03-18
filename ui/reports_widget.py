from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QTabWidget,
    QFileDialog,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta
import csv
from sqlmodel import (
    desc,
    func,
)

from database.db import (
    get_session,
    select,
    Payment,
    User,
    YogaClass,
    Role,
    Center,
    Attendance,
    Reserve,
    get_all_payments,
    get_users_by_role,
    get_all_centers,
    get_classes_by_teacher,
    get_payments_by_teacher,
    get_total_earnings_by_teacher,
)


class ReportsWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("📊 Reportes")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.tabs = QTabWidget()

        # Pestañas según el rol
        if self.current_user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.tabs.addTab(self.create_financial_tab(), "💰 Financiero")
            self.tabs.addTab(self.create_attendance_tab(), "📋 Asistencia")
            self.tabs.addTab(self.create_classes_tab(), "🎯 Clases")
            self.tabs.addTab(self.create_users_tab(), "👥 Usuarios")
        if self.current_user.role == Role.TEACHER:
            self.tabs.addTab(self.create_teacher_tab(), "🧘 Mis Reportes")
        if self.current_user.role == Role.STUDENT:
            self.tabs.addTab(self.create_student_tab(), "📊 Mi Actividad")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # ------------------------------------------------------------
    # Métodos de creación de pestañas
    # ------------------------------------------------------------
    def create_financial_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Filtros
        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Desde:"))
        self.fin_start = QDateEdit()
        self.fin_start.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.fin_start)

        filter_layout.addWidget(QLabel("Hasta:"))
        self.fin_end = QDateEdit()
        self.fin_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.fin_end)

        filter_layout.addWidget(QLabel("Centro:"))
        self.fin_center = QComboBox()
        self.fin_center.addItem("Todos", None)
        filter_layout.addWidget(self.fin_center)

        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(lambda: self.generate_report("financial"))
        filter_layout.addWidget(generate_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla
        self.fin_table = QTableWidget()
        self.fin_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.fin_table)

        # Exportar
        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.fin_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        return widget

    def create_attendance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Desde:"))
        self.att_start = QDateEdit()
        self.att_start.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.att_start)

        filter_layout.addWidget(QLabel("Hasta:"))
        self.att_end = QDateEdit()
        self.att_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.att_end)

        filter_layout.addWidget(QLabel("Centro:"))
        self.att_center = QComboBox()
        self.att_center.addItem("Todos", None)
        filter_layout.addWidget(self.att_center)

        filter_layout.addWidget(QLabel("Profesor:"))
        self.att_teacher = QComboBox()
        self.att_teacher.addItem("Todos", None)
        filter_layout.addWidget(self.att_teacher)

        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(lambda: self.generate_report("attendance"))
        filter_layout.addWidget(generate_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.att_table = QTableWidget()
        self.att_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.att_table)

        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.att_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        return widget

    def create_classes_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Desde:"))
        self.class_start = QDateEdit()
        self.class_start.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.class_start)

        filter_layout.addWidget(QLabel("Hasta:"))
        self.class_end = QDateEdit()
        self.class_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.class_end)

        filter_layout.addWidget(QLabel("Centro:"))
        self.class_center = QComboBox()
        self.class_center.addItem("Todos", None)
        filter_layout.addWidget(self.class_center)

        filter_layout.addWidget(QLabel("Profesor:"))
        self.class_teacher = QComboBox()
        self.class_teacher.addItem("Todos", None)
        filter_layout.addWidget(self.class_teacher)

        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(lambda: self.generate_report("classes"))
        filter_layout.addWidget(generate_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.class_table = QTableWidget()
        self.class_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.class_table)

        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.class_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        return widget

    def create_users_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Rol:"))
        self.user_role = QComboBox()
        self.user_role.addItems(
            ["Todos", "STUDENT", "TEACHER", "RECEPTIONIST", "ADMINISTRATOR"]
        )
        filter_layout.addWidget(self.user_role)

        filter_layout.addWidget(QLabel("Estado:"))
        self.user_status = QComboBox()
        self.user_status.addItems(["Todos", "Activos", "Inactivos"])
        filter_layout.addWidget(self.user_status)

        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(lambda: self.generate_report("users"))
        filter_layout.addWidget(generate_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.user_table = QTableWidget()
        self.user_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.user_table)

        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.user_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        return widget

    def create_teacher_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Filtros")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Desde:"))
        self.teacher_start = QDateEdit()
        self.teacher_start.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.teacher_start)

        filter_layout.addWidget(QLabel("Hasta:"))
        self.teacher_end = QDateEdit()
        self.teacher_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.teacher_end)

        generate_btn = QPushButton("Generar")
        generate_btn.clicked.connect(lambda: self.generate_report("teacher"))
        filter_layout.addWidget(generate_btn)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.teacher_table = QTableWidget()
        self.teacher_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.teacher_table)

        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.teacher_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        return widget

    def create_student_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Sin filtros, solo su historial
        self.student_table = QTableWidget()
        self.student_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.student_table)

        export_btn = QPushButton("📥 Exportar CSV")
        export_btn.clicked.connect(lambda: self.export_csv(self.student_table))
        layout.addWidget(export_btn)

        widget.setLayout(layout)
        self.load_student_report()
        return widget

    # ------------------------------------------------------------
    # Carga inicial de combos
    # ------------------------------------------------------------
    def load_initial_data(self):
        session = get_session()
        try:
            centers = get_all_centers()
            for combo in [self.fin_center, self.att_center, self.class_center]:
                combo.clear()
                combo.addItem("Todos", None)
                for c in centers:
                    combo.addItem(c.name, c.id)

            teachers = get_users_by_role(Role.TEACHER)
            for combo in [self.att_teacher, self.class_teacher]:
                combo.clear()
                combo.addItem("Todos", None)
                for t in teachers:
                    combo.addItem(t.name, t.id)
        finally:
            session.close()

    # ------------------------------------------------------------
    # Generación de reportes unificada
    # ------------------------------------------------------------
    def generate_report(self, report_type):
        if report_type == "financial":
            self.generate_financial()
        elif report_type == "attendance":
            self.generate_attendance()
        elif report_type == "classes":
            self.generate_classes()
        elif report_type == "users":
            self.generate_users()
        elif report_type == "teacher":
            self.generate_teacher_report()

    def generate_financial(self):
        start = datetime.combine(self.fin_start.date().toPyDate(), datetime.min.time())
        end = datetime.combine(self.fin_end.date().toPyDate(), datetime.max.time())
        center_id = self.fin_center.currentData()

        session = get_session()
        try:
            payments = get_all_payments(start, end)
            if center_id:
                payments = [
                    p
                    for p in payments
                    if session.get(YogaClass, p.yogaclass_id)
                    and session.get(YogaClass, p.yogaclass_id).center_id == center_id
                ]

            headers = ["Fecha", "ID", "Estudiante", "Monto", "Método", "Estado"]
            self.fin_table.setColumnCount(len(headers))
            self.fin_table.setHorizontalHeaderLabels(headers)
            self.fin_table.setRowCount(len(payments))

            for row, p in enumerate(payments):
                student = session.get(User, p.student_id)
                self.fin_table.setItem(
                    row, 0, QTableWidgetItem(p.paid_at.strftime("%Y-%m-%d %H:%M"))
                )
                self.fin_table.setItem(row, 1, QTableWidgetItem(str(p.id)))
                self.fin_table.setItem(
                    row, 2, QTableWidgetItem(student.name if student else "N/A")
                )
                self.fin_table.setItem(row, 3, QTableWidgetItem(f"${p.amount:.2f}"))
                self.fin_table.setItem(row, 4, QTableWidgetItem(p.payment_method))
                status_item = QTableWidgetItem(p.status)
                if p.status == "paid":
                    status_item.setForeground(QColor("green"))
                elif p.status == "pending":
                    status_item.setForeground(QColor("orange"))
                elif p.status == "refunded":
                    status_item.setForeground(QColor("red"))
                self.fin_table.setItem(row, 5, status_item)
        finally:
            session.close()

    def generate_attendance(self):
        start = datetime.combine(self.att_start.date().toPyDate(), datetime.min.time())
        end = datetime.combine(self.att_end.date().toPyDate(), datetime.max.time())
        center_id = self.att_center.currentData()
        teacher_id = self.att_teacher.currentData()

        session = get_session()
        try:
            query = select(Attendance).where(
                Attendance.attended_at >= start, Attendance.attended_at <= end
            )
            attendances = session.exec(query).all()

            # Filtrar por centro/profesor
            filtered = []
            for a in attendances:
                yc = session.get(YogaClass, a.yogaclass_id)
                if not yc:
                    continue
                if center_id and yc.center_id != center_id:
                    continue
                if teacher_id and yc.teacher_id != teacher_id:
                    continue
                filtered.append(a)

            headers = ["Fecha", "Hora", "Estudiante", "Clase", "Estado"]
            self.att_table.setColumnCount(len(headers))
            self.att_table.setHorizontalHeaderLabels(headers)
            self.att_table.setRowCount(len(filtered))

            for row, a in enumerate(filtered):
                student = session.get(User, a.student_id)
                yc = session.get(YogaClass, a.yogaclass_id)
                self.att_table.setItem(
                    row,
                    0,
                    QTableWidgetItem(
                        a.attended_at.strftime("%Y-%m-%d") if a.attended_at else ""
                    ),
                )
                self.att_table.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        a.attended_at.strftime("%H:%M") if a.attended_at else ""
                    ),
                )
                self.att_table.setItem(
                    row, 2, QTableWidgetItem(student.name if student else "N/A")
                )
                self.att_table.setItem(
                    row, 3, QTableWidgetItem(f"Clase #{yc.id}" if yc else "N/A")
                )
                status_item = QTableWidgetItem(a.status)
                if a.status == "present":
                    status_item.setForeground(QColor("green"))
                elif a.status == "absent":
                    status_item.setForeground(QColor("red"))
                elif a.status == "late":
                    status_item.setForeground(QColor("orange"))
                self.att_table.setItem(row, 4, status_item)
        finally:
            session.close()

    def generate_classes(self):
        start = datetime.combine(
            self.class_start.date().toPyDate(), datetime.min.time()
        )
        end = datetime.combine(self.class_end.date().toPyDate(), datetime.max.time())
        center_id = self.class_center.currentData()
        teacher_id = self.class_teacher.currentData()

        session = get_session()
        try:
            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start, YogaClass.scheduled_at <= end
            )
            if center_id:
                query = query.where(YogaClass.center_id == center_id)
            if teacher_id:
                query = query.where(YogaClass.teacher_id == teacher_id)
            classes = session.exec(query.order_by(YogaClass.scheduled_at)).all()

            headers = [
                "Fecha",
                "Hora",
                "Clase",
                "Profesor",
                "Capacidad",
                "Inscritos",
                "Disponibles",
            ]
            self.class_table.setColumnCount(len(headers))
            self.class_table.setHorizontalHeaderLabels(headers)
            self.class_table.setRowCount(len(classes))

            for row, c in enumerate(classes):
                teacher = session.get(User, c.teacher_id)
                self.class_table.setItem(
                    row, 0, QTableWidgetItem(c.scheduled_at.strftime("%Y-%m-%d"))
                )
                self.class_table.setItem(
                    row, 1, QTableWidgetItem(c.scheduled_at.strftime("%H:%M"))
                )
                self.class_table.setItem(row, 2, QTableWidgetItem(f"Clase #{c.id}"))
                self.class_table.setItem(
                    row, 3, QTableWidgetItem(teacher.name if teacher else "N/A")
                )
                self.class_table.setItem(row, 4, QTableWidgetItem(str(c.max_capacity)))
                self.class_table.setItem(
                    row, 5, QTableWidgetItem(str(c.current_capacity))
                )
                self.class_table.setItem(
                    row, 6, QTableWidgetItem(str(c.max_capacity - c.current_capacity))
                )
        finally:
            session.close()

    def generate_users(self):
        role_filter = self.user_role.currentText()
        status_filter = self.user_status.currentText()

        session = get_session()
        try:
            query = select(User)
            if role_filter != "Todos":
                query = query.where(User.role == role_filter)
            users = session.exec(query).all()

            if status_filter == "Activos":
                users = [u for u in users if u.is_active]
            elif status_filter == "Inactivos":
                users = [u for u in users if not u.is_active]

            headers = ["ID", "Nombre", "Email", "Rol", "Registro", "Estado"]
            self.user_table.setColumnCount(len(headers))
            self.user_table.setHorizontalHeaderLabels(headers)
            self.user_table.setRowCount(len(users))

            for row, u in enumerate(users):
                self.user_table.setItem(row, 0, QTableWidgetItem(str(u.id)))
                self.user_table.setItem(row, 1, QTableWidgetItem(u.name))
                self.user_table.setItem(row, 2, QTableWidgetItem(u.email))
                self.user_table.setItem(row, 3, QTableWidgetItem(u.role.value))
                self.user_table.setItem(
                    row, 4, QTableWidgetItem(u.created_at.strftime("%Y-%m-%d"))
                )
                status_item = QTableWidgetItem("Activo" if u.is_active else "Inactivo")
                status_item.setForeground(
                    QColor("green") if u.is_active else QColor("red")
                )
                self.user_table.setItem(row, 5, status_item)
        finally:
            session.close()

    def generate_teacher_report(self):
        start = datetime.combine(
            self.teacher_start.date().toPyDate(), datetime.min.time()
        )
        end = datetime.combine(self.teacher_end.date().toPyDate(), datetime.max.time())

        session = get_session()
        try:
            # Clases del profesor en el período
            classes = get_classes_by_teacher(self.current_user.id, None)
            classes_in_period = [c for c in classes if start <= c.scheduled_at <= end]

            # Pagos recibidos
            payments = get_payments_by_teacher(self.current_user.id, start, end)
            total_earned = sum(
                p.amount * (c.teacher_share_percentage / 100)
                for p in payments
                if (c := session.get(YogaClass, p.yogaclass_id))
            )

            # Asistencias
            attendances = 0
            for c in classes_in_period:
                count = session.exec(
                    select(func.count(Attendance.id)).where(
                        Attendance.yogaclass_id == c.id, Attendance.status == "present"
                    )
                ).one()
                attendances += count

            headers = ["Concepto", "Valor"]
            self.teacher_table.setColumnCount(2)
            self.teacher_table.setHorizontalHeaderLabels(headers)
            self.teacher_table.setRowCount(5)

            data = [
                ("Clases impartidas", str(len(classes_in_period))),
                (
                    "Alumnos distintos",
                    str(self.count_distinct_students(session, classes_in_period)),
                ),
                ("Asistencias totales", str(attendances)),
                ("Ingresos brutos", f"${total_earned:.2f}"),
                (
                    "Promedio por clase",
                    (
                        f"${(total_earned/len(classes_in_period)):.2f}"
                        if classes_in_period
                        else "$0"
                    ),
                ),
            ]
            for row, (k, v) in enumerate(data):
                self.teacher_table.setItem(row, 0, QTableWidgetItem(k))
                self.teacher_table.setItem(row, 1, QTableWidgetItem(v))
        finally:
            session.close()

    def count_distinct_students(self, session, classes):
        student_ids = set()
        for c in classes:
            reserves = session.exec(
                select(Reserve).where(
                    Reserve.yogaclass_id == c.id, Reserve.status == "active"
                )
            ).all()
            student_ids.update(r.student_id for r in reserves)
        return len(student_ids)

    def load_student_report(self):
        session = get_session()
        try:
            # Asistencias del estudiante (orden descendente por fecha)
            attendances = session.exec(
                select(Attendance)
                .where(Attendance.student_id == self.current_user.id)
                .order_by(desc(Attendance.attended_at))
            ).all()

            headers = ["Fecha", "Hora", "Clase", "Profesor", "Estado"]
            self.student_table.setColumnCount(len(headers))
            self.student_table.setHorizontalHeaderLabels(headers)
            self.student_table.setRowCount(len(attendances))

            for row, a in enumerate(attendances):
                yc = session.get(YogaClass, a.yogaclass_id)
                teacher = session.get(User, yc.teacher_id) if yc else None
                self.student_table.setItem(
                    row,
                    0,
                    QTableWidgetItem(
                        a.attended_at.strftime("%Y-%m-%d") if a.attended_at else ""
                    ),
                )
                self.student_table.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        a.attended_at.strftime("%H:%M") if a.attended_at else ""
                    ),
                )
                self.student_table.setItem(
                    row, 2, QTableWidgetItem(f"Clase #{yc.id}" if yc else "N/A")
                )
                self.student_table.setItem(
                    row, 3, QTableWidgetItem(teacher.name if teacher else "N/A")
                )
                status_item = QTableWidgetItem(a.status)
                if a.status == "present":
                    status_item.setForeground(QColor("green"))
                elif a.status == "absent":
                    status_item.setForeground(QColor("red"))
                elif a.status == "late":
                    status_item.setForeground(QColor("orange"))
                self.student_table.setItem(row, 4, status_item)
        finally:
            session.close()

    # ------------------------------------------------------------
    # Exportación CSV
    # ------------------------------------------------------------
    def export_csv(self, table):
        if table.rowCount() == 0:
            QMessageBox.warning(self, "Sin datos", "No hay datos para exportar")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "", "CSV (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Encabezados
                headers = [
                    table.horizontalHeaderItem(i).text()
                    for i in range(table.columnCount())
                ]
                writer.writerow(headers)
                # Datos
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            QMessageBox.information(self, "Éxito", f"Reporte guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {str(e)}")
