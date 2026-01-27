from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDateEdit, QGroupBox,
    QProgressBar
)
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from datetime import datetime, timedelta
from database.db import (
    get_session, select, YogaClass, User, Center,
    Add_Reservation, get_available_classes_for_date,
    Add_Payment, Payment, Reserve
)

class ClassReservationDialog(QDialog):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.selected_class_id = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("🧘 Reservar Clases")
        self.setFixedSize(900, 650)

        main_layout = QVBoxLayout()

        # Título
        title_label = QLabel("📅 Reserva de Clases")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Panel de información del usuario
        user_info_group = QGroupBox("👤 Información del Alumno")
        user_layout = QHBoxLayout()

        user_info = QLabel(f"<b>Alumno:</b> {self.user.name}<br>"
                          f"<b>Email:</b> {self.user.email}<br>"
                          f"<b>Reservas activas:</b> {self.get_active_reservations_count()}")
        user_info.setStyleSheet("padding: 10px;")

        user_layout.addWidget(user_info)
        user_layout.addStretch()

        user_info_group.setLayout(user_layout)
        main_layout.addWidget(user_info_group)

        # Filtro por fecha
        filter_group = QGroupBox("🔍 Filtros de Búsqueda")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("📅 Fecha:"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setMinimumDate(QDate.currentDate())
        self.date_input.dateChanged.connect(self.load_available_classes)
        filter_layout.addWidget(self.date_input)

        filter_layout.addWidget(QLabel("🏢 Centro:"))
        self.center_combo = QComboBox()
        self.center_combo.addItem("Todos los centros", None)
        self.load_centers()
        self.center_combo.currentIndexChanged.connect(self.load_available_classes)
        filter_layout.addWidget(self.center_combo)

        filter_layout.addStretch()

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_available_classes)
        filter_layout.addWidget(refresh_btn)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # Tabla de clases disponibles
        table_group = QGroupBox("📋 Clases Disponibles")
        table_layout = QVBoxLayout()

        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(7)
        self.classes_table.setHorizontalHeaderLabels([
            "Hora", "Clase", "Profesor", "Centro", "Precio", "Disponibilidad", "Acción"
        ])
        self.classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.classes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Configurar anchos de columnas
        self.classes_table.setColumnWidth(0, 80)   # Hora
        self.classes_table.setColumnWidth(1, 70)   # Clase
        self.classes_table.setColumnWidth(4, 80)   # Precio
        self.classes_table.setColumnWidth(5, 120)  # Disponibilidad
        self.classes_table.setColumnWidth(6, 100)  # Acción

        table_layout.addWidget(self.classes_table)
        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group)

        # Panel de información de la clase seleccionada
        self.info_group = QGroupBox("ℹ️ Información de la Clase")
        self.info_group.setVisible(False)
        info_layout = QVBoxLayout()

        self.class_info_label = QLabel("Seleccione una clase para ver los detalles")
        self.class_info_label.setWordWrap(True)
        self.class_info_label.setStyleSheet("padding: 10px; background-color: #f8f9fa; border-radius: 5px;")
        info_layout.addWidget(self.class_info_label)

        # Barra de progreso de disponibilidad
        self.availability_bar = QProgressBar()
        self.availability_bar.setVisible(False)
        info_layout.addWidget(self.availability_bar)

        self.info_group.setLayout(info_layout)
        main_layout.addWidget(self.info_group)

        # Botones de acción
        button_layout = QHBoxLayout()

        self.reserve_btn = QPushButton("✅ Reservar y Pagar")
        self.reserve_btn.clicked.connect(self.reserve_and_pay)
        self.reserve_btn.setEnabled(False)
        self.reserve_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 12px 24px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QPushButton:hover:!disabled {
                background-color: #27ae60;
            }
        """)

        close_btn = QPushButton("❌ Cerrar")
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 12px 24px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        button_layout.addWidget(self.reserve_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Cargar clases iniciales
        self.load_available_classes()

        # Conectar selección de fila
        self.classes_table.itemSelectionChanged.connect(self.on_class_selected)

    def load_centers(self):
        """Cargar centros en el combo box."""
        session = get_session()
        try:
            centers = session.exec(select(Center)).all()
            for center in centers:
                self.center_combo.addItem(center.name, center.id)
        finally:
            session.close()

    def get_active_reservations_count(self):
        """Obtener número de reservas activas del usuario."""
        session = get_session()
        try:
            reservations = session.exec(
                select(Reserve).where(
                    Reserve.student_id == self.user.id,
                    Reserve.status == "active"
                )
            ).all()
            return len(reservations)
        finally:
            session.close()

    def load_available_classes(self):
        """Cargar clases disponibles para la fecha seleccionada."""
        session = get_session()
        try:
            py_date = self.date_input.date().toPyDate()
            center_id = self.center_combo.currentData()

            # Obtener todas las clases para la fecha
            start_date = datetime.combine(py_date, datetime.min.time())
            end_date = datetime.combine(py_date, datetime.max.time())

            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at <= end_date,
                YogaClass.current_capacity < YogaClass.max_capacity
            )

            if center_id:
                query = query.where(YogaClass.center_id == center_id)

            classes = session.exec(query.order_by(YogaClass.scheduled_at.asc())).all()

            # Excluir clases ya reservadas por el estudiante
            if classes:
                reserved_classes = session.exec(
                    select(Reserve.yogaclass_id).where(
                        Reserve.student_id == self.user.id,
                        Reserve.status == "active"
                    )
                ).all()

                if reserved_classes:
                    classes = [c for c in classes if c.id not in reserved_classes]

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
                    QTableWidgetItem(f"#{yoga_class.id}")
                )

                # Profesor
                teacher = session.get(User, yoga_class.teacher_id)
                teacher_name = teacher.name if teacher else "No asignado"
                self.classes_table.setItem(
                    row, 2,
                    QTableWidgetItem(teacher_name)
                )

                # Centro
                center = session.get(Center, yoga_class.center_id)
                center_name = center.name if center else "Desconocido"
                self.classes_table.setItem(
                    row, 3,
                    QTableWidgetItem(center_name)
                )

                # Precio
                price_item = QTableWidgetItem(f"${yoga_class.price:.2f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.classes_table.setItem(row, 4, price_item)

                # Disponibilidad
                available = yoga_class.max_capacity - yoga_class.current_capacity
                capacity_percentage = (yoga_class.current_capacity / yoga_class.max_capacity * 100) if yoga_class.max_capacity > 0 else 0

                if available <= 2:
                    availability_text = f"⚠️ {available} cupos"
                    availability_color = QColor("#e74c3c")
                elif available <= 5:
                    availability_text = f"{available} cupos"
                    availability_color = QColor("#f39c12")
                else:
                    availability_text = f"{available} cupos"
                    availability_color = QColor("#2ecc71")

                availability_item = QTableWidgetItem(availability_text)
                availability_item.setForeground(availability_color)
                availability_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.classes_table.setItem(row, 5, availability_item)

                # Botón para reservar
                reserve_btn = QPushButton("📝 Reservar")
                reserve_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #2980b9;
                    }
                """)
                reserve_btn.clicked.connect(
                    lambda checked, class_id=yoga_class.id: self.select_class(class_id)
                )
                self.classes_table.setCellWidget(row, 6, reserve_btn)

        finally:
            session.close()

    def select_class(self, class_id):
        """Seleccionar una clase específica."""
        self.selected_class_id = class_id
        self.update_class_info(class_id)
        self.reserve_btn.setEnabled(True)

        # Seleccionar la fila correspondiente
        for row in range(self.classes_table.rowCount()):
            if self.classes_table.item(row, 1).text() == f"#{class_id}":
                self.classes_table.selectRow(row)
                break

    def on_class_selected(self):
        """Cuando se selecciona una fila en la tabla."""
        selected_rows = self.classes_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            class_id_text = self.classes_table.item(row, 1).text()
            class_id = int(class_id_text.replace("#", ""))
            self.select_class(class_id)

    def update_class_info(self, class_id):
        """Actualizar información de la clase seleccionada."""
        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            if yoga_class:
                teacher = session.get(User, yoga_class.teacher_id)
                center = session.get(Center, yoga_class.center_id)

                available = yoga_class.max_capacity - yoga_class.current_capacity
                capacity_percentage = (yoga_class.current_capacity / yoga_class.max_capacity * 100)

                info_html = f"""
                <div style='font-size: 14px;'>
                    <h3 style='color: #2c3e50;'>Clase #{yoga_class.id}</h3>
                    <p><b>📅 Fecha y Hora:</b> {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}</p>
                    <p><b>👨‍🏫 Profesor:</b> {teacher.name if teacher else 'No asignado'}</p>
                    <p><b>🏢 Centro:</b> {center.name if center else 'Desconocido'}</p>
                    <p><b>💰 Precio:</b> <span style='color: #27ae60; font-weight: bold;'>${yoga_class.price:.2f}</span></p>
                    <p><b>👥 Capacidad:</b> {yoga_class.current_capacity}/{yoga_class.max_capacity} alumnos</p>
                    <p><b>🎫 Disponibles:</b> {available} cupos</p>
                </div>
                """

                self.class_info_label.setText(info_html)

                # Configurar barra de progreso
                self.availability_bar.setVisible(True)
                self.availability_bar.setRange(0, yoga_class.max_capacity)
                self.availability_bar.setValue(yoga_class.current_capacity)
                self.availability_bar.setFormat(f"{yoga_class.current_capacity}/{yoga_class.max_capacity} (%p%)")

                if capacity_percentage >= 80:
                    self.availability_bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
                elif capacity_percentage >= 50:
                    self.availability_bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
                else:
                    self.availability_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")

                self.info_group.setVisible(True)

        finally:
            session.close()

    def reserve_and_pay(self):
        """Reservar y pagar la clase seleccionada."""
        if not self.selected_class_id:
            QMessageBox.warning(self, "Error", "Seleccione una clase primero")
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, self.selected_class_id)
            if not yoga_class:
                QMessageBox.warning(self, "Error", "Clase no encontrada")
                return

            # Verificar disponibilidad
            if yoga_class.current_capacity >= yoga_class.max_capacity:
                QMessageBox.warning(self, "Clase Llena", "Lo sentimos, esta clase ya está llena.")
                return

            # Verificar si ya tiene reserva
            existing_reservation = session.exec(
                select(Reserve).where(
                    Reserve.student_id == self.user.id,
                    Reserve.yogaclass_id == self.selected_class_id,
                    Reserve.status == "active"
                )
            ).first()

            if existing_reservation:
                QMessageBox.warning(self, "Ya Reservado", "Ya tienes una reserva activa para esta clase.")
                return

            # Confirmar reserva y pago
            reply = QMessageBox.question(
                self,
                "Confirmar Reserva y Pago",
                f"¿Desea reservar y pagar esta clase?\n\n"
                f"Clase: #{yoga_class.id}\n"
                f"Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"Precio: ${yoga_class.price:.2f}\n\n"
                f"Esta acción reservará tu lugar y procesará el pago.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Crear reserva
                reservation = Add_Reservation(self.user.id, self.selected_class_id)

                if reservation:
                    # Crear pago automáticamente
                    payment = Add_Payment(
                        student_id=self.user.id,
                        yogaclass_id=self.selected_class_id,
                        amount=yoga_class.price,
                        payment_method="Tarjeta de Débito"  # Por defecto
                    )

                    QMessageBox.information(
                        self,
                        "🎉 ¡Reserva Exitosa!",
                        f"¡Felicidades {self.user.name}!\n\n"
                        f"✅ Clase reservada correctamente\n"
                        f"✅ Pago procesado: ${yoga_class.price:.2f}\n"
                        f"📅 Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
                        f"🏢 Centro: {session.get(Center, yoga_class.center_id).name}\n\n"
                        f"Recuerda llegar 15 minutos antes de la clase."
                    )

                    # Recargar clases disponibles
                    self.load_available_classes()
                    self.selected_class_id = None
                    self.reserve_btn.setEnabled(False)
                    self.info_group.setVisible(False)

                else:
                    QMessageBox.warning(
                        self,
                        "Error en la Reserva",
                        "No se pudo realizar la reserva. La clase puede estar llena o haber un problema con el sistema."
                    )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar la reserva: {str(e)}")
        finally:
            session.close()
