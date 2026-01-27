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
    get_session, select, YogaClass, User, Role, Payment, Center, Attendance,
    get_available_classes_for_date, get_student_statistics, get_teacher_statistics
)
# ELIMINA esta línea: from sqlalchemy import func


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

        # Calendario con clases disponibles
        calendar_frame = self.create_calendar_with_classes()

        layout.addWidget(header)
        layout.addLayout(stats_layout)
        layout.addWidget(calendar_frame)

        self.setLayout(layout)

    def create_student_stats(self):
        """Estadísticas para estudiantes."""
        layout = QGridLayout()

        stats = get_student_statistics(self.user.id)

        stat_cards = [
            ("📊 Clases Asistidas", str(stats.get("classes_attended", 0)), "primary"),
            ("📅 Clases Reservadas", str(stats.get("classes_reserved", 0)), "success"),
            ("💰 Total Pagado", f"${stats.get('total_paid', 0):.2f}", "warning"),
            ("🎯 Tasa de Asistencia", f"{stats.get('attendance_rate', 0):.1f}%", "info"),
        ]

        for i, (title, value, color) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, i // 2, i % 2)

        return layout

    def create_teacher_stats(self):
        """Estadísticas para profesores."""
        layout = QGridLayout()

        stats = get_teacher_statistics(self.user.id)

        stat_cards = [
            ("🎓 Clases Impartidas", str(stats.get("total_classes", 0)), "primary"),
            ("📅 Próximas Clases", str(stats.get("upcoming_classes", 0)), "success"),
            ("💰 Ganancias Totales", f"${stats.get('total_earnings', 0):.2f}", "warning"),
            ("👥 Alumnos Únicos", self.get_unique_students_count(self.user.id), "info"),
        ]

        for i, (title, value, color) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, i // 2, i % 2)

        return layout

    def create_admin_stats(self):
        """Estadísticas para administradores/recepcionistas."""
        layout = QGridLayout()

        session = get_session()
        try:
            today = datetime.now().date()

            # Clases hoy
            classes_today = session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at >= datetime.combine(today, datetime.min.time()),
                    YogaClass.scheduled_at < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                )
            ).all()

            # Ingresos del día
            today_payments_result = session.exec(
                select(Payment).where(
                    Payment.paid_at >= datetime.combine(today, datetime.min.time()),
                    Payment.paid_at < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                    Payment.status == "paid"
                )
            ).all()

            today_payments = sum(p.amount for p in today_payments_result)

            # Usuarios activos
            active_users = session.exec(
                select(User).where(User.is_active == True)
            ).all()

            # Centros activos
            active_centers = session.exec(
                select(Center)
            ).all()

            stat_cards = [
                ("🎯 Clases Hoy", str(len(classes_today)), "primary"),
                ("💰 Ingresos Hoy", f"${today_payments:.2f}", "success"),
                ("👥 Usuarios Activos", str(len(active_users)), "warning"),
                ("🏢 Centros", str(len(active_centers)), "info"),
            ]

            for i, (title, value, color) in enumerate(stat_cards):
                card = self.create_stat_card(title, value, color)
                layout.addWidget(card, i // 2, i % 2)

        finally:
            session.close()

        return layout

    def create_general_stats(self):
        """Estadísticas generales para roles no específicos."""
        layout = QGridLayout()

        session = get_session()
        try:
            # Estadísticas básicas
            total_classes = session.exec(select(YogaClass)).all()
            active_users = session.exec(select(User).where(User.is_active == True)).all()

            stat_cards = [
                ("🎯 Total de Clases", str(len(total_classes)), "primary"),
                ("👥 Usuarios Activos", str(len(active_users)), "success"),
            ]

            for i, (title, value, color) in enumerate(stat_cards):
                card = self.create_stat_card(title, value, color)
                layout.addWidget(card, i // 2, i % 2)

        finally:
            session.close()

        return layout

    def create_stat_card(self, title: str, value: str, color: str) -> QWidget:
        """Crear una tarjeta de estadística."""
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
            "info": "#17a2b8"
        }
        value_label.setStyleSheet(f"color: {color_map.get(color, '#3498db')};")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        card.setLayout(layout)
        return card

    def create_calendar_with_classes(self):
        """Calendario que muestra clases disponibles."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()

        calendar_label = QLabel("📅 Calendario de Clases")
        calendar_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        # Calendario
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_date_selected)

        # Tabla de clases para la fecha seleccionada
        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(5)
        self.classes_table.setHorizontalHeaderLabels([
            "Hora", "Clase", "Profesor", "Precio", "Disponibles"
        ])
        self.classes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(calendar_label)
        layout.addWidget(self.calendar)
        layout.addWidget(self.classes_table)

        frame.setLayout(layout)

        # Cargar clases para hoy por defecto
        self.load_classes_for_date(QDate.currentDate())

        return frame

    def on_date_selected(self, date):
        """Cargar clases cuando se selecciona una fecha."""
        self.load_classes_for_date(date)

    def load_classes_for_date(self, date):
        """Cargar clases disponibles para una fecha específica."""
        session = get_session()
        try:
            py_date = date.toPyDate()
            classes = get_available_classes_for_date(
                datetime.combine(py_date, datetime.min.time()),
                self.user.id if self.user.role == Role.STUDENT else None
            )

            self.classes_table.setRowCount(len(classes))

            for row, yoga_class in enumerate(classes):
                # Hora
                self.classes_table.setItem(
                    row, 0,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%H:%M"))
                )

                # Información de la clase
                self.classes_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"Clase {yoga_class.id}")
                )

                # Profesor
                teacher = session.get(User, yoga_class.teacher_id)
                teacher_name = teacher.name if teacher else "No asignado"
                self.classes_table.setItem(
                    row, 2,
                    QTableWidgetItem(teacher_name)
                )

                # Precio
                self.classes_table.setItem(
                    row, 3,
                    QTableWidgetItem(f"${yoga_class.price:.2f}")
                )

                # Disponibles
                available = yoga_class.max_capacity - yoga_class.current_capacity
                self.classes_table.setItem(
                    row, 4,
                    QTableWidgetItem(str(available))
                )

        finally:
            session.close()

    def get_unique_students_count(self, teacher_id: int) -> str:
        """Obtener número de estudiantes únicos para un profesor."""
        session = get_session()
        try:
            # Obtener todos los estudiantes únicos que han asistido a clases del profesor
            attendances = session.exec(
                select(Attendance)
                .join(YogaClass, Attendance.yogaclass_id == YogaClass.id)
                .where(YogaClass.teacher_id == teacher_id)
            ).all()

            unique_students = set(attendance.student_id for attendance in attendances)
            return str(len(unique_students))
        finally:
            session.close()
