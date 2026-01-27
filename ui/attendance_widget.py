from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QComboBox, QDateEdit,
    QMessageBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
from database.db import get_session, select, YogaClass, User, Attendance, Reserve, Role

class AttendanceWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_classes_by_date(self.date_input.date())

    def init_ui(self):
        layout = QVBoxLayout()

        # Grupo de filtros
        filter_group = QGroupBox("Filtros de Asistencia")
        filter_layout = QVBoxLayout()

        # Fila 1: Fecha y clase
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("Fecha:"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.dateChanged.connect(self.load_classes_by_date)
        row1_layout.addWidget(self.date_input)

        row1_layout.addWidget(QLabel("Clase:"))
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.load_attendance_for_class)
        row1_layout.addWidget(self.class_combo)

        row1_layout.addStretch()
        filter_layout.addLayout(row1_layout)

        # Fila 2: Botones
        row2_layout = QHBoxLayout()
        self.class_info_label = QLabel("Seleccione una clase")
        self.class_info_label.setStyleSheet("color: #666; font-style: italic;")
        row2_layout.addWidget(self.class_info_label)

        row2_layout.addStretch()

        mark_all_btn = QPushButton("📋 Marcar Todos Presentes")
        mark_all_btn.clicked.connect(self.mark_all_present)
        row2_layout.addWidget(mark_all_btn)

        filter_layout.addLayout(row2_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Tabla de asistencia
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels([
            "ID", "Alumno", "Email", "Asistió", "Observaciones"
        ])
        self.attendance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.attendance_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Área de observaciones
        notes_group = QGroupBox("Observaciones Generales")
        notes_layout = QVBoxLayout()
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(80)
        self.notes_text.setPlaceholderText("Observaciones sobre la clase (opcional)...")
        notes_layout.addWidget(self.notes_text)
        notes_group.setLayout(notes_layout)

        # Botones de acción
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Guardar Asistencia")
        save_btn.clicked.connect(self.save_attendance)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        clear_btn = QPushButton("🔄 Limpiar")
        clear_btn.clicked.connect(self.clear_attendance)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        # Estadísticas
        self.stats_label = QLabel("👥 0 alumnos | ✅ 0 presentes | ❌ 0 ausentes")
        self.stats_label.setStyleSheet("font-size: 14px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;")

        layout.addWidget(self.attendance_table)
        layout.addWidget(notes_group)
        layout.addWidget(self.stats_label)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_classes_by_date(self, date):
        """Cargar clases del profesor para la fecha seleccionada."""
        session = get_session()
        try:
            selected_date = date.toPyDate()
            classes = session.exec(
                select(YogaClass).where(
                    YogaClass.teacher_id == self.current_user.id,
                    YogaClass.scheduled_at >= datetime.combine(selected_date, datetime.min.time()),
                    YogaClass.scheduled_at < datetime.combine(selected_date + timedelta(days=1), datetime.min.time())
                ).order_by(YogaClass.scheduled_at.asc())
            ).all()

            self.class_combo.clear()
            self.class_combo.addItem("-- Seleccione una clase --", None)

            for yoga_class in classes:
                # Verificar si la clase ya pasó
                class_time = yoga_class.scheduled_at
                current_time = datetime.now()

                time_status = "🟢" if class_time > current_time else "🔴"
                self.class_combo.addItem(
                    f"{time_status} Clase {yoga_class.id} - {yoga_class.scheduled_at.strftime('%H:%M')}",
                    yoga_class.id
                )
        finally:
            session.close()

    def load_attendance_for_class(self):
        """Cargar asistencia para la clase seleccionada."""
        class_id = self.class_combo.currentData()
        if not class_id:
            self.attendance_table.setRowCount(0)
            self.class_info_label.setText("Seleccione una clase")
            self.update_stats()
            return

        session = get_session()
        try:
            # Obtener información de la clase
            yoga_class = session.get(YogaClass, class_id)
            if yoga_class:
                teacher = session.get(User, yoga_class.teacher_id)
                teacher_name = teacher.name if teacher else "Desconocido"
                self.class_info_label.setText(
                    f"🎯 Clase {yoga_class.id} | 🕒 {yoga_class.scheduled_at.strftime('%H:%M')} | "
                    f"👨‍🏫 {teacher_name} | 👥 {yoga_class.current_capacity}/{yoga_class.max_capacity}"
                )

            # Obtener alumnos inscritos en esta clase
            reservations = session.exec(
                select(Reserve).where(
                    Reserve.yogaclass_id == class_id,
                    Reserve.status == "active"
                )
            ).all()

            student_ids = [r.student_id for r in reservations]

            if student_ids:
                students = session.exec(
                    select(User).where(User.id.in_(student_ids)).order_by(User.name.asc())
                ).all()

                # Obtener asistencia existente
                attendances = session.exec(
                    select(Attendance).where(Attendance.yogaclass_id == class_id)
                ).all()

                attendance_dict = {a.student_id: a for a in attendances}

                self.attendance_table.setRowCount(len(students))

                for row, student in enumerate(students):
                    # ID
                    self.attendance_table.setItem(row, 0, QTableWidgetItem(str(student.id)))

                    # Nombre
                    self.attendance_table.setItem(row, 1, QTableWidgetItem(student.name))

                    # Email
                    self.attendance_table.setItem(row, 2, QTableWidgetItem(student.email or ""))

                    # Checkbox para asistencia
                    attended_checkbox = QCheckBox()
                    attended_checkbox.setStyleSheet("QCheckBox { margin-left: 50%; margin-right: 50%; }")

                    if student.id in attendance_dict:
                        attendance = attendance_dict[student.id]
                        attended_checkbox.setChecked(attendance.status == "present")
                        if attendance.status == "late":
                            attended_checkbox.setText("Tarde")
                    else:
                        # Por defecto, marcar como presente si la clase ya pasó
                        if yoga_class and yoga_class.scheduled_at < datetime.now():
                            attended_checkbox.setChecked(True)

                    self.attendance_table.setCellWidget(row, 3, attended_checkbox)

                    # Observaciones
                    notes_item = QTableWidgetItem()
                    if student.id in attendance_dict:
                        attendance = attendance_dict[student.id]
                        # Podríamos agregar un campo de observaciones en el modelo Attendance
                        pass
                    self.attendance_table.setItem(row, 4, notes_item)
            else:
                self.attendance_table.setRowCount(0)
                self.class_info_label.setText("No hay alumnos inscritos en esta clase")

        finally:
            session.close()

        self.update_stats()

    def mark_all_present(self):
        """Marcar a todos los alumnos como presentes."""
        for row in range(self.attendance_table.rowCount()):
            checkbox = self.attendance_table.cellWidget(row, 3)
            if checkbox:
                checkbox.setChecked(True)
        self.update_stats()

    def clear_attendance(self):
        """Limpiar todas las marcas de asistencia."""
        for row in range(self.attendance_table.rowCount()):
            checkbox = self.attendance_table.cellWidget(row, 3)
            if checkbox:
                checkbox.setChecked(False)
        self.update_stats()

    def update_stats(self):
        """Actualizar estadísticas de asistencia."""
        total = self.attendance_table.rowCount()
        present = 0

        for row in range(self.attendance_table.rowCount()):
            checkbox = self.attendance_table.cellWidget(row, 3)
            if checkbox and checkbox.isChecked():
                present += 1

        absent = total - present
        self.stats_label.setText(f"👥 {total} alumnos | ✅ {present} presentes | ❌ {absent} ausentes")

    def save_attendance(self):
        """Guardar la asistencia de todos los estudiantes."""
        class_id = self.class_combo.currentData()
        if not class_id:
            QMessageBox.warning(self, "Error", "Seleccione una clase primero")
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            if not yoga_class:
                QMessageBox.warning(self, "Error", "Clase no encontrada")
                return

            for row in range(self.attendance_table.rowCount()):
                student_id_item = self.attendance_table.item(row, 0)
                if not student_id_item:
                    continue

                student_id = int(student_id_item.text())
                checkbox = self.attendance_table.cellWidget(row, 3)
                notes_item = self.attendance_table.item(row, 4)
                notes = notes_item.text() if notes_item else ""

                if not checkbox:
                    continue

                # Buscar registro de asistencia existente
                attendance = session.exec(
                    select(Attendance).where(
                        Attendance.student_id == student_id,
                        Attendance.yogaclass_id == class_id
                    )
                ).first()

                if checkbox.isChecked():
                    status = "present"
                    if checkbox.text() == "Tarde":
                        status = "late"

                    if not attendance:
                        # Crear nueva asistencia
                        attendance = Attendance(
                            student_id=student_id,
                            yogaclass_id=class_id,
                            attended_at=datetime.now(),
                            status=status
                        )
                        session.add(attendance)
                    else:
                        # Actualizar asistencia existente
                        attendance.attended_at = datetime.now()
                        attendance.status = status
                else:
                    if attendance:
                        # Marcar como ausente
                        attendance.status = "absent"
                        attendance.attended_at = None

            session.commit()

            # Registrar observaciones si las hay
            notes_text = self.notes_text.toPlainText().strip()
            if notes_text:
                # Podríamos guardar esto en una tabla de observaciones de clase
                pass

            QMessageBox.information(
                self,
                "✅ Asistencia Guardada",
                f"La asistencia de {self.attendance_table.rowCount()} alumnos ha sido guardada correctamente.\n\n"
                f"Clase: {yoga_class.id}\n"
                f"Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}"
            )

            self.load_attendance_for_class()  # Recargar para mostrar cambios

        except Exception as e:
            session.rollback()
            QMessageBox.critical(
                self,
                "❌ Error",
                f"No se pudo guardar la asistencia:\n{str(e)}"
            )
        finally:
            session.close()
