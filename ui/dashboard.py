from datetime import datetime, timedelta

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.db import (
    get_session,
    select,
    YogaClass,
    User,
    Role,
    Payment,
    Center,
    Attendance,
    get_student_enrolled_classes,
    get_student_packages,
    get_active_student_packages,
    get_teacher_statistics,
    get_total_earnings_by_teacher,
    get_users_by_role,
    func,
    Reserve,
    StudentPackage,
)


class DashboardWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Encabezado
        header = QLabel(f"Bienvenido, {self.user.name}")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mostrar estadísticas según el rol
        if self.user.role == Role.STUDENT:
            stats_layout = self.create_student_stats()
        elif self.user.role == Role.TEACHER:
            stats_layout = self.create_teacher_stats()
        elif self.user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            stats_layout = self.create_admin_stats()
        else:
            stats_layout = self.create_general_stats()

        # Calendario con clases
        calendar_frame = self.create_calendar_with_classes()

        layout.addWidget(header)
        layout.addLayout(stats_layout)
        layout.addWidget(calendar_frame)

        self.setLayout(layout)

    # =========================================================================
    # ESTADÍSTICAS POR ROL
    # =========================================================================

    def create_student_stats(self):
        """
        Estadísticas para estudiantes:
        - Clases asistidas
        - Clases reservadas (próximas)
        - Paquetes activos (créditos restantes)
        - Historial resumido de paquetes
        """
        layout = QGridLayout()

        # Datos básicos
        session = get_session()
        try:
            attended = (
                session.exec(
                    select(func.count(Attendance.id)).where(
                        Attendance.student_id == self.user.id,
                        Attendance.status == "present",
                    )
                ).first()
                or 0
            )

            reserved = (
                session.exec(
                    select(func.count(Reserve.id)).where(
                        Reserve.student_id == self.user.id, Reserve.status == "active"
                    )
                ).first()
                or 0
            )

            # Paquetes activos y total de créditos
            active_packages = get_active_student_packages(self.user.id)
            total_credits = sum(p.remaining_classes for p in active_packages)

            # Paquetes comprados
            all_packages = get_student_packages(self.user.id)
            packages_purchased = len(all_packages)

        finally:
            session.close()

        # Tarjetas principales
        stat_cards = [
            ("📊 Clases Asistidas", str(attended), "primary"),
            ("📅 Próximas Reservas", str(reserved), "success"),
            ("📦 Créditos Disponibles", str(total_credits), "warning"),
            ("🎟️ Paquetes Comprados", str(packages_purchased), "info"),
        ]

        for i, (title, value, color) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, i // 2, i % 2)

        return layout

    def create_teacher_stats(self):
        """
        Estadísticas para profesores:
        - Clases impartidas (totales)
        - Próximas clases
        - Alumnos inscritos (distintos) en sus clases (con reserva activa)
        - Ganancias totales
        """
        layout = QGridLayout()

        stats = get_teacher_statistics(self.user.id)
        earnings = get_total_earnings_by_teacher(self.user.id)

        # Alumnos distintos con reserva activa en clases de este profesor
        enrolled_students = self.get_enrolled_students_count(self.user.id)

        stat_cards = [
            ("🎓 Clases Impartidas", str(stats.get("total_classes", 0)), "primary"),
            ("📅 Próximas Clases", str(stats.get("upcoming_classes", 0)), "success"),
            ("👥 Alumnos Inscritos", str(enrolled_students), "info"),
            ("💰 Ganancias Totales", f"${earnings:.2f}", "warning"),
        ]

        for i, (title, value, color) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, i // 2, i % 2)

        return layout

    def create_admin_stats(self):
        """
        Estadísticas para administradores y recepcionistas:
        - Clases hoy
        - Ingresos hoy
        - Total de alumnos
        - Total de profesores
        - Paquetes vendidos
        - Centros activos
        """
        layout = QGridLayout()

        session = get_session()
        try:
            today = datetime.now().date()

            # Clases hoy
            classes_today = session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at
                    >= datetime.combine(today, datetime.min.time()),
                    YogaClass.scheduled_at
                    < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                )
            ).all()

            # Ingresos del día
            today_payments_result = session.exec(
                select(Payment).where(
                    Payment.paid_at >= datetime.combine(today, datetime.min.time()),
                    Payment.paid_at
                    < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                    Payment.status == "paid",
                )
            ).all()
            today_payments = sum(p.amount for p in today_payments_result)

            # Usuarios por rol
            total_students = (
                session.exec(
                    select(func.count(User.id)).where(User.role == Role.STUDENT)
                ).first()
                or 0
            )

            total_teachers = (
                session.exec(
                    select(func.count(User.id)).where(User.role == Role.TEACHER)
                ).first()
                or 0
            )

            # Paquetes vendidos (total de compras)
            total_packages_sold = (
                session.exec(select(func.count(StudentPackage.id))).first() or 0
            )

            # Centros activos
            active_centers = session.exec(select(func.count(Center.id))).first() or 0

        finally:
            session.close()

        # Tarjetas – 3 columnas para mejor distribución
        stat_cards = [
            ("🎯 Clases Hoy", str(len(classes_today)), "primary"),
            ("💰 Ingresos Hoy", f"${today_payments:.2f}", "success"),
            ("👨‍🎓 Alumnos", str(total_students), "info"),
            ("👨‍🏫 Profesores", str(total_teachers), "warning"),
            ("📦 Paq. Vendidos", str(total_packages_sold), "danger"),
            ("🏢 Centros", str(active_centers), "secondary"),
        ]

        # Posiciones manuales para 3 columnas
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for i, (title, value, color) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, positions[i][0], positions[i][1])

        return layout

    def create_general_stats(self):
        """Estadísticas genéricas (por si acaso)."""
        layout = QGridLayout()

        session = get_session()
        try:
            total_classes = session.exec(select(func.count(YogaClass.id))).first() or 0
            active_users = (
                session.exec(
                    select(func.count(User.id)).where(User.is_active == True)
                ).first()
                or 0
            )

            stat_cards = [
                ("🎯 Total de Clases", str(total_classes), "primary"),
                ("👥 Usuarios Activos", str(active_users), "success"),
            ]

            for i, (title, value, color) in enumerate(stat_cards):
                card = self.create_stat_card(title, value, color)
                layout.addWidget(card, i // 2, i % 2)

        finally:
            session.close()

        return layout

    # =========================================================================
    # CALENDARIO Y CLASES
    # =========================================================================

    def create_calendar_with_classes(self):
        """
        Crea el calendario y la tabla de clases.
        - Para estudiantes: muestra SOLO las clases en las que están inscritos.
        - Para otros roles: muestra todas las clases disponibles.
        """
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()

        calendar_label = QLabel("📅 Calendario de Clases")
        calendar_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        # Calendario
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_date_selected)

        # Tabla de clases
        self.classes_table = QTableWidget()
        if self.user.role == Role.STUDENT:
            headers = ["Hora", "Clase", "Profesor", "Centro", "Estado"]
        else:
            headers = ["Hora", "Clase", "Profesor", "Precio", "Disponibles"]

        self.classes_table.setColumnCount(len(headers))
        self.classes_table.setHorizontalHeaderLabels(headers)
        self.classes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(calendar_label)
        layout.addWidget(self.calendar)
        layout.addWidget(self.classes_table)

        frame.setLayout(layout)

        # Cargar clases para hoy
        self.load_classes_for_date(QDate.currentDate())

        return frame

    def on_date_selected(self, date):
        """Actualiza la tabla al seleccionar una fecha."""
        self.load_classes_for_date(date)

    def load_classes_for_date(self, date):
        """
        Carga las clases correspondientes a la fecha seleccionada según el rol.
        """
        session = get_session()
        try:
            py_date = date.toPyDate()
            dt_start = datetime.combine(py_date, datetime.min.time())
            dt_end = datetime.combine(py_date, datetime.max.time())

            if self.user.role == Role.STUDENT:
                # Solo clases en las que el estudiante tiene reserva activa
                classes = get_student_enrolled_classes(self.user.id, dt_start)
                # Filtrar solo las de este día (la función ya acepta fecha)
                classes = [c for c in classes if dt_start <= c.scheduled_at <= dt_end]
            else:
                # Todas las clases del día (sin filtrar por disponibilidad)
                classes = session.exec(
                    select(YogaClass)
                    .where(
                        YogaClass.scheduled_at >= dt_start,
                        YogaClass.scheduled_at <= dt_end,
                    )
                    .order_by(YogaClass.scheduled_at.asc())
                ).all()

            self.classes_table.setRowCount(len(classes))

            for row, yoga_class in enumerate(classes):
                # Columna 0: Hora
                self.classes_table.setItem(
                    row, 0, QTableWidgetItem(yoga_class.scheduled_at.strftime("%H:%M"))
                )

                # Columna 1: ID de clase
                self.classes_table.setItem(
                    row, 1, QTableWidgetItem(f"Clase {yoga_class.id}")
                )

                # Columna 2: Profesor
                teacher = session.get(User, yoga_class.teacher_id)
                teacher_name = teacher.name if teacher else "No asignado"
                self.classes_table.setItem(row, 2, QTableWidgetItem(teacher_name))

                if self.user.role == Role.STUDENT:
                    # Columna 3: Centro
                    center = session.get(Center, yoga_class.center_id)
                    center_name = center.name if center else "Desconocido"
                    self.classes_table.setItem(row, 3, QTableWidgetItem(center_name))

                    # Columna 4: Estado (asistió / no asistió / futuro)
                    attendance = session.exec(
                        select(Attendance).where(
                            Attendance.student_id == self.user.id,
                            Attendance.yogaclass_id == yoga_class.id,
                        )
                    ).first()
                    if attendance:
                        status = (
                            "✅ Asistió"
                            if attendance.status == "present"
                            else "❌ Ausente"
                        )
                    else:
                        if yoga_class.scheduled_at < datetime.now():
                            status = "❌ No asistió"
                        else:
                            status = "⏳ Próxima"
                    self.classes_table.setItem(row, 4, QTableWidgetItem(status))

                else:
                    # Columnas para otros roles
                    # Columna 3: Precio
                    self.classes_table.setItem(
                        row, 3, QTableWidgetItem(f"${yoga_class.price:.2f}")
                    )
                    # Columna 4: Disponibilidad
                    available = yoga_class.max_capacity - yoga_class.current_capacity
                    self.classes_table.setItem(row, 4, QTableWidgetItem(str(available)))

        finally:
            session.close()

    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================

    def create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        """Crea una tarjeta de estadística con diseño consistente."""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout()

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setStyleSheet("color: #666;")

        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))

        color_map = {
            "primary": "#3498db",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "info": "#17a2b8",
            "danger": "#e74c3c",
            "secondary": "#95a5a6",
        }
        value_label.setStyleSheet(f"color: {color_map.get(color, '#3498db')};")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        card.setLayout(layout)
        return card

    def get_enrolled_students_count(self, teacher_id: int) -> int:
        """
        Retorna el número de estudiantes DISTINTOS que tienen una reserva activa
        en alguna clase impartida por el profesor.
        """
        session = get_session()
        try:
            # Clases del profesor
            classes = session.exec(
                select(YogaClass.id).where(YogaClass.teacher_id == teacher_id)
            ).all()
            if not classes:
                return 0

            # Estudiantes distintos con reserva activa en esas clases
            result = session.exec(
                select(func.count(func.distinct(Reserve.student_id))).where(
                    Reserve.yogaclass_id.in_(classes), Reserve.status == "active"
                )
            ).first()
            return result or 0
        finally:
            session.close()
