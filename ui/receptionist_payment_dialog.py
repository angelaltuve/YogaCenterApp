from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QGroupBox,
    QFormLayout, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QDateEdit
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta
from database.db import (
    get_session, select, YogaClass, Reserve, Add_Payment,
    Payment, User, Role, get_users_by_role, get_available_classes_for_date
)

class ReceptionistPaymentDialog(QDialog):
    def __init__(self, user):
        super().__init__()
        self.receptionist = user
        self.init_ui()
        self.load_students()
        self.load_unpaid_reservations()

    def init_ui(self):
        self.setWindowTitle("💳 Sistema de Pagos - Recepcionista")
        self.setFixedSize(800, 600)

        main_layout = QVBoxLayout()

        # Título
        title_label = QLabel("💳 Sistema de Gestión de Pagos")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Panel de información del recepcionista
        receptionist_info = QLabel(f"👤 <b>Recepcionista:</b> {self.receptionist.name}")
        receptionist_info.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 5px;")
        main_layout.addWidget(receptionist_info)

        # Contenedor principal (dos columnas)
        container_layout = QHBoxLayout()

        # Columna izquierda - Formulario de pago
        left_column = QVBoxLayout()

        payment_form_group = QGroupBox("📝 Registrar Nuevo Pago")
        payment_form_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        form_layout = QFormLayout()

        # Selección de estudiante
        self.student_combo = QComboBox()
        self.student_combo.currentIndexChanged.connect(self.load_student_reservations)
        form_layout.addRow("👤 Estudiante:", self.student_combo)

        # Selección de clase (reservas sin pagar)
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.update_payment_info)
        form_layout.addRow("🎯 Clase a Pagar:", self.class_combo)

        # Monto
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 1000)
        self.amount_input.setPrefix("$ ")
        self.amount_input.setDecimals(2)
        self.amount_input.setReadOnly(True)
        form_layout.addRow("💰 Monto:", self.amount_input)

        # Método de pago
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "💵 Efectivo",
            "💳 Tarjeta de Crédito",
            "🏦 Tarjeta de Débito",
            "📤 Transferencia Bancaria",
            "📱 Pago Móvil"
        ])
        form_layout.addRow("💳 Método de Pago:", self.method_combo)

        # Referencia/Número de transacción (opcional)
        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Número de transacción, referencia, etc.")
        form_layout.addRow("🔢 Referencia:", self.reference_input)

        payment_form_group.setLayout(form_layout)
        left_column.addWidget(payment_form_group)

        # Botón de procesar pago
        process_btn = QPushButton("✅ Procesar Pago")
        process_btn.clicked.connect(self.process_payment)
        process_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 12px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        left_column.addWidget(process_btn)
        left_column.addStretch()

        # Columna derecha - Información y lista de pagos recientes
        right_column = QVBoxLayout()

        # Información de la clase seleccionada
        self.class_info_group = QGroupBox("ℹ️ Información de la Clase")
        self.class_info_group.setVisible(False)
        class_info_layout = QVBoxLayout()

        self.class_info_label = QLabel("Seleccione una clase para ver los detalles")
        self.class_info_label.setWordWrap(True)
        self.class_info_label.setStyleSheet("padding: 10px;")
        class_info_layout.addWidget(self.class_info_label)

        self.class_info_group.setLayout(class_info_layout)
        right_column.addWidget(self.class_info_group)

        # Lista de pagos recientes del estudiante
        payments_group = QGroupBox("📋 Historial de Pagos Recientes")
        payments_layout = QVBoxLayout()

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels([
            "Fecha", "Clase", "Monto", "Método", "Estado"
        ])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payments_table.setMaximumHeight(200)

        payments_layout.addWidget(self.payments_table)
        payments_group.setLayout(payments_layout)
        right_column.addWidget(payments_group)

        # Filtro rápido por fecha
        filter_group = QGroupBox("🔍 Filtro Rápido")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Ver pagos desde:"))
        self.filter_date = QDateEdit()
        self.filter_date.setDate(QDate.currentDate().addMonths(-1))
        self.filter_date.dateChanged.connect(self.load_student_payments)
        filter_layout.addWidget(self.filter_date)

        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        right_column.addWidget(filter_group)

        # Agregar columnas al contenedor
        container_layout.addLayout(left_column, 2)
        container_layout.addLayout(right_column, 3)

        main_layout.addLayout(container_layout)

        # Botones de cierre
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def load_students(self):
        """Cargar todos los estudiantes en el combo box."""
        session = get_session()
        try:
            students = get_users_by_role(Role.STUDENT)
            self.student_combo.clear()
            self.student_combo.addItem("-- Seleccionar Estudiante --", None)

            for student in students:
                self.student_combo.addItem(
                    f"{student.name} ({student.email})",
                    student.id
                )
        finally:
            session.close()

    def load_student_reservations(self):
        """Cargar reservas sin pagar del estudiante seleccionado."""
        student_id = self.student_combo.currentData()
        if not student_id:
            self.class_combo.clear()
            self.class_info_group.setVisible(False)
            self.payments_table.setRowCount(0)
            return

        session = get_session()
        try:
            # Cargar reservas activas sin pago
            reservations = session.exec(
                select(Reserve).where(
                    Reserve.student_id == student_id,
                    Reserve.status == "active"
                )
            ).all()

            self.class_combo.clear()
            self.class_combo.addItem("-- Seleccionar Clase --", None)

            for reserve in reservations:
                yoga_class = session.get(YogaClass, reserve.yogaclass_id)
                if yoga_class:
                    # Verificar si ya tiene pago
                    existing_payment = session.exec(
                        select(Payment).where(
                            Payment.student_id == student_id,
                            Payment.yogaclass_id == yoga_class.id,
                            Payment.status == "paid"
                        )
                    ).first()

                    if not existing_payment:
                        class_date = yoga_class.scheduled_at.strftime("%Y-%m-%d %H:%M")
                        self.class_combo.addItem(
                            f"Clase #{yoga_class.id} - {class_date} - ${yoga_class.price:.2f}",
                            yoga_class.id
                        )

            # Cargar historial de pagos del estudiante
            self.load_student_payments()

        finally:
            session.close()

    def load_student_payments(self):
        """Cargar pagos del estudiante seleccionado."""
        student_id = self.student_combo.currentData()
        if not student_id:
            return

        session = get_session()
        try:
            start_date = datetime.combine(self.filter_date.date().toPyDate(), datetime.min.time())

            payments = session.exec(
                select(Payment).where(
                    Payment.student_id == student_id,
                    Payment.paid_at >= start_date
                ).order_by(Payment.paid_at.desc())
            ).all()

            self.payments_table.setRowCount(len(payments))

            for row, payment in enumerate(payments):
                # Fecha
                self.payments_table.setItem(
                    row, 0,
                    QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d %H:%M"))
                )

                # Clase
                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                class_info = f"Clase #{yoga_class.id}" if yoga_class else "N/A"
                self.payments_table.setItem(row, 1, QTableWidgetItem(class_info))

                # Monto
                amount_item = QTableWidgetItem(f"${payment.amount:.2f}")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.payments_table.setItem(row, 2, amount_item)

                # Método
                self.payments_table.setItem(row, 3, QTableWidgetItem(payment.payment_method))

                # Estado
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

                self.payments_table.setItem(row, 4, status_item)

        finally:
            session.close()

    def load_unpaid_reservations(self):
        """Cargar todas las reservas sin pagar (para vista rápida)."""
        pass  # Podría implementarse para mostrar todas las deudas pendientes

    def update_payment_info(self):
        """Actualizar información cuando se selecciona una clase."""
        class_id = self.class_combo.currentData()
        student_id = self.student_combo.currentData()

        if not class_id or not student_id:
            self.class_info_group.setVisible(False)
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            student = session.get(User, student_id)

            if yoga_class and student:
                teacher = session.get(User, yoga_class.teacher_id)
                from database.db import Center
                center = session.get(Center, yoga_class.center_id)

                info_html = f"""
                <div style='font-size: 13px;'>
                    <h4 style='color: #2c3e50;'>Detalles del Pago</h4>
                    <p><b>👤 Estudiante:</b> {student.name}</p>
                    <p><b>📅 Clase:</b> #{yoga_class.id} - {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}</p>
                    <p><b>👨‍🏫 Profesor:</b> {teacher.name if teacher else 'No asignado'}</p>
                    <p><b>🏢 Centro:</b> {center.name if center else 'Desconocido'}</p>
                    <p><b>💰 Monto a Pagar:</b> <span style='color: #27ae60; font-weight: bold;'>${yoga_class.price:.2f}</span></p>
                    <hr style='border: 1px solid #eee;'>
                    <p><i>⚠️ Verificar que el estudiante tenga reserva activa para esta clase</i></p>
                </div>
                """

                self.class_info_label.setText(info_html)
                self.class_info_group.setVisible(True)
                self.amount_input.setValue(yoga_class.price)

        finally:
            session.close()

    def process_payment(self):
        """Procesar el pago."""
        student_id = self.student_combo.currentData()
        class_id = self.class_combo.currentData()
        amount = self.amount_input.value()
        method = self.method_combo.currentText().split(" ")[-1]  # Extraer solo el método
        reference = self.reference_input.text().strip()

        if not student_id or not class_id:
            QMessageBox.warning(self, "Error", "Seleccione un estudiante y una clase")
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            student = session.get(User, student_id)

            if not yoga_class or not student:
                QMessageBox.warning(self, "Error", "Información no válida")
                return

            # Verificar que el estudiante tenga reserva activa
            reserve = session.exec(
                select(Reserve).where(
                    Reserve.student_id == student_id,
                    Reserve.yogaclass_id == class_id,
                    Reserve.status == "active"
                )
            ).first()

            if not reserve:
                QMessageBox.warning(
                    self,
                    "Sin Reserva",
                    f"El estudiante {student.name} no tiene una reserva activa para esta clase."
                )
                return

            # Verificar si ya pagó
            existing_payment = session.exec(
                select(Payment).where(
                    Payment.student_id == student_id,
                    Payment.yogaclass_id == class_id,
                    Payment.status == "paid"
                )
            ).first()

            if existing_payment:
                QMessageBox.warning(
                    self,
                    "Pago Existente",
                    f"El estudiante {student.name} ya pagó esta clase el {existing_payment.paid_at.strftime('%Y-%m-%d')}."
                )
                return

            # Confirmar pago
            reply = QMessageBox.question(
                self,
                "Confirmar Pago",
                f"¿Desea procesar el pago?\n\n"
                f"👤 Estudiante: {student.name}\n"
                f"🎯 Clase: #{yoga_class.id}\n"
                f"📅 Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"💰 Monto: ${amount:.2f}\n"
                f"💳 Método: {method}\n"
                f"🔢 Referencia: {reference if reference else 'N/A'}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Crear el pago
                payment = Add_Payment(
                    student_id=student_id,
                    yogaclass_id=class_id,
                    amount=amount,
                    payment_method=method
                )

                if payment:
                    # Actualizar referencia si se proporcionó
                    if reference:
                        payment.reference = reference
                        session.commit()

                    # Generar comprobante
                    receipt_info = self.generate_receipt(payment, student, yoga_class)

                    QMessageBox.information(
                        self,
                        "✅ Pago Procesado",
                        f"¡Pago procesado exitosamente!\n\n"
                        f"📄 Comprobante: {payment.id}\n"
                        f"👤 Estudiante: {student.name}\n"
                        f"🎯 Clase: #{yoga_class.id}\n"
                        f"💰 Monto: ${amount:.2f}\n"
                        f"💳 Método: {method}\n"
                        f"📅 Fecha: {payment.paid_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"{receipt_info}"
                    )

                    # Limpiar formulario
                    self.reference_input.clear()
                    self.load_student_reservations()
                    self.class_info_group.setVisible(False)

                else:
                    QMessageBox.critical(self, "Error", "No se pudo procesar el pago")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar el pago: {str(e)}")
        finally:
            session.close()

    def generate_receipt(self, payment, student, yoga_class):
        """Generar información del comprobante."""
        session = get_session()
        try:
            from database.db import Center
            center = session.get(Center, yoga_class.center_id)
            teacher = session.get(User, yoga_class.teacher_id)

            receipt = f"""
            ------------------------------
            🧘 COMPROBANTE DE PAGO
            ------------------------------
            Número: {payment.id:06d}
            Fecha: {payment.paid_at.strftime('%Y-%m-%d %H:%M:%S')}

            ESTUDIANTE
            Nombre: {student.name}
            Email: {student.email}

            CLASE
            ID: #{yoga_class.id}
            Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}
            Profesor: {teacher.name if teacher else 'N/A'}
            Centro: {center.name if center else 'N/A'}

            PAGO
            Monto: ${payment.amount:.2f}
            Método: {payment.payment_method}
            Estado: {payment.status}

            ------------------------------
            📞 Centro: {center.phone if center else 'N/A'}
            🏢 Dirección: {center.address if center else 'N/A'}
            ------------------------------
            """

            return receipt

        finally:
            session.close()
