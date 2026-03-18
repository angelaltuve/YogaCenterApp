from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDateEdit,
    QTabWidget,
    QWidget,
    QCheckBox,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta
from functools import partial

from database.db import (
    get_session,
    select,
    YogaClass,
    Reserve,
    add_payment,
    Payment,
    User,
    Role,
    get_users_by_role,
    get_available_classes_for_date,
    Package,
    get_active_packages,
    purchase_package,
    get_student_packages,
    cancel_student_package,
    get_all_centers,
    Center,
    get_user_center_ids,
    reserve_package,
    confirm_package_payment,
    add_reservation,
    StudentPackage,
)

from sqlalchemy import desc
from sqlalchemy.orm import selectinload


class ReceptionistPaymentDialog(QDialog):
    def __init__(self, user):
        super().__init__()
        self.receptionist = user
        self.center_ids = get_user_center_ids(self.receptionist.id)
        self.setWindowTitle("💳 Sistema de Pagos - Recepcionista")
        self.setFixedSize(950, 700)
        self.init_ui()
        self.load_students()

    def init_ui(self):
        main_layout = QVBoxLayout()

        title = QLabel("💳 Sistema de Gestión de Pagos")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        receptionist_info = QLabel(f"👤 <b>Recepcionista:</b> {self.receptionist.name}")
        main_layout.addWidget(title)
        main_layout.addWidget(receptionist_info)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_payment_tab(), "💵 Pago por clase")
        self.tabs.addTab(self.create_package_tab(), "📦 Venta de paquetes")
        self.tabs.addTab(self.create_reservation_tab(), "📅 Reservar clase")

        main_layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    # ----------------------------------------------------------------------
    # PESTAÑA 1: PAGO POR CLASE INDIVIDUAL
    # ----------------------------------------------------------------------
    def create_payment_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout()

        left_column = QVBoxLayout()

        payment_form_group = QGroupBox("📝 Registrar Nuevo Pago")
        payment_form_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        form_layout = QFormLayout()

        self.student_combo = QComboBox()
        self.student_combo.currentIndexChanged.connect(self.load_student_reservations)
        form_layout.addRow("👤 Estudiante:", self.student_combo)

        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.update_payment_info)
        form_layout.addRow("🎯 Clase a Pagar:", self.class_combo)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 1000)
        self.amount_input.setPrefix("$ ")
        self.amount_input.setDecimals(2)
        self.amount_input.setReadOnly(True)
        form_layout.addRow("💰 Monto:", self.amount_input)

        self.method_combo = QComboBox()
        self.method_combo.addItems(
            [
                "💵 Efectivo",
                "💳 Tarjeta de Crédito",
                "🏦 Tarjeta de Débito",
                "📤 Transferencia Bancaria",
                "📱 Pago Móvil",
            ]
        )
        form_layout.addRow("💳 Método de Pago:", self.method_combo)

        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText(
            "Número de transacción, referencia, etc."
        )
        form_layout.addRow("🔢 Referencia:", self.reference_input)

        payment_form_group.setLayout(form_layout)
        left_column.addWidget(payment_form_group)

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

        right_column = QVBoxLayout()

        self.class_info_group = QGroupBox("ℹ️ Información de la Clase")
        self.class_info_group.setVisible(False)
        class_info_layout = QVBoxLayout()
        self.class_info_label = QLabel("Seleccione una clase para ver los detalles")
        self.class_info_label.setWordWrap(True)
        self.class_info_label.setStyleSheet("padding: 10px;")
        class_info_layout.addWidget(self.class_info_label)
        self.class_info_group.setLayout(class_info_layout)
        right_column.addWidget(self.class_info_group)

        payments_group = QGroupBox("📋 Historial de Pagos Recientes")
        payments_layout = QVBoxLayout()
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels(
            ["Fecha", "Clase", "Monto", "Método", "Estado"]
        )
        self.payments_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.payments_table.setMaximumHeight(200)
        payments_layout.addWidget(self.payments_table)
        payments_group.setLayout(payments_layout)
        right_column.addWidget(payments_group)

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

        layout.addLayout(left_column, 2)
        layout.addLayout(right_column, 3)
        tab.setLayout(layout)
        return tab

    # ----------------------------------------------------------------------
    # PESTAÑA 2: VENTA DE PAQUETES
    # ----------------------------------------------------------------------
    def create_package_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.pkg_student_combo = QComboBox()
        form_layout.addRow("👤 Estudiante:", self.pkg_student_combo)

        self.package_combo = QComboBox()
        self.load_available_packages()
        self.package_combo.currentIndexChanged.connect(self.update_package_info)
        form_layout.addRow("📦 Paquete:", self.package_combo)

        self.package_info_label = QLabel("")
        self.package_info_label.setWordWrap(True)
        self.package_info_label.setStyleSheet(
            "padding: 10px; background-color: #f8f9fa; border-radius: 5px;"
        )

        self.pkg_method_combo = QComboBox()
        self.pkg_method_combo.addItems(
            [
                "💵 Efectivo",
                "💳 Tarjeta de Crédito",
                "🏦 Tarjeta de Débito",
                "📤 Transferencia Bancaria",
                "📱 Pago Móvil",
            ]
        )
        form_layout.addRow("💳 Método de Pago:", self.pkg_method_combo)

        self.pkg_reference_input = QLineEdit()
        self.pkg_reference_input.setPlaceholderText(
            "Número de transacción, referencia, etc."
        )
        form_layout.addRow("🔢 Referencia:", self.pkg_reference_input)

        self.pay_later_check = QCheckBox("Reservar")
        form_layout.addRow(self.pay_later_check)

        layout.addLayout(form_layout)
        layout.addWidget(self.package_info_label)

        btn_layout = QHBoxLayout()
        purchase_btn = QPushButton("🛒 Comprar Ahora")
        purchase_btn.clicked.connect(self.purchase_package)

        reserve_btn = QPushButton("📦 Reservar")
        reserve_btn.clicked.connect(self.reserve_package)

        btn_layout.addWidget(purchase_btn)
        btn_layout.addWidget(reserve_btn)
        layout.addLayout(btn_layout)

        pending_group = QGroupBox("⏳ Paquetes reservados pendientes de pago")
        pending_layout = QVBoxLayout()
        self.pending_packages_table = QTableWidget()
        self.pending_packages_table.setColumnCount(5)
        self.pending_packages_table.setHorizontalHeaderLabels(
            ["Paquete", "Fecha reserva", "Monto", "Método", "Acción"]
        )
        self.pending_packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        pending_layout.addWidget(self.pending_packages_table)
        pending_group.setLayout(pending_layout)
        layout.addWidget(pending_group)

        layout.addWidget(QLabel("📋 Paquetes del estudiante:"))
        self.student_packages_table = QTableWidget()
        self.student_packages_table.setColumnCount(6)
        self.student_packages_table.setHorizontalHeaderLabels(
            ["Paquete", "Comprado", "Expira", "Clases rest.", "Estado", "Acciones"]
        )
        self.student_packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.pkg_student_combo.currentIndexChanged.connect(self.load_student_packages)
        self.pkg_student_combo.currentIndexChanged.connect(self.load_pending_packages)
        layout.addWidget(self.student_packages_table)

        tab.setLayout(layout)
        return tab

    # ----------------------------------------------------------------------
    # PESTAÑA 3: RESERVAR CLASE PARA ESTUDIANTE
    # ----------------------------------------------------------------------
    def create_reservation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()

        form_group = QGroupBox("Reservar clase para estudiante")
        form_layout = QFormLayout()

        self.res_student_combo = QComboBox()
        form_layout.addRow("👤 Estudiante:", self.res_student_combo)

        self.res_date_input = QDateEdit()
        self.res_date_input.setDate(QDate.currentDate())
        self.res_date_input.dateChanged.connect(
            self.load_available_classes_for_reservation
        )
        self.res_student_combo.currentIndexChanged.connect(
            self.load_available_classes_for_reservation
        )
        form_layout.addRow("📅 Fecha:", self.res_date_input)

        self.res_class_combo = QComboBox()
        self.res_class_combo.currentIndexChanged.connect(self.update_reservation_info)
        form_layout.addRow("🎯 Clase disponible:", self.res_class_combo)

        self.res_info_label = QLabel("")
        self.res_info_label.setWordWrap(True)
        self.res_info_label.setStyleSheet(
            "padding: 10px; background-color: #f8f9fa; border-radius: 5px;"
        )
        form_layout.addRow(self.res_info_label)

        reserve_btn = QPushButton("✅ Reservar clase")
        reserve_btn.clicked.connect(self.reserve_class_for_student)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        layout.addWidget(reserve_btn)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    # ----------------------------------------------------------------------
    # MÉTODOS DE CARGA DE DATOS
    # ----------------------------------------------------------------------
    def load_students(self):
        session = get_session()
        try:
            students = get_users_by_role(Role.STUDENT)

            self.student_combo.clear()
            self.pkg_student_combo.clear()
            self.res_student_combo.clear()

            self.student_combo.addItem("-- Seleccionar Estudiante --", None)
            self.pkg_student_combo.addItem("-- Seleccionar Estudiante --", None)
            self.res_student_combo.addItem("-- Seleccionar Estudiante --", None)

            for student in students:
                display_text = f"{student.name} ({student.email})"
                self.student_combo.addItem(display_text, student.id)
                self.pkg_student_combo.addItem(display_text, student.id)
                self.res_student_combo.addItem(display_text, student.id)
        finally:
            session.close()

    def load_available_packages(self):
        packages = get_active_packages()
        self.package_combo.clear()
        self.package_combo.addItem("-- Seleccionar Paquete --", None)
        for pkg in packages:
            text = f"{pkg.name} - {pkg.total_classes} clases - ${pkg.price:.2f}"
            if pkg.validity_days:
                text += f" (válido {pkg.validity_days} días)"
            self.package_combo.addItem(text, pkg.id)

    def update_package_info(self):
        pkg_id = self.package_combo.currentData()
        if not pkg_id:
            self.package_info_label.setText("")
            return

        session = get_session()
        try:
            pkg = session.get(Package, pkg_id)
            if pkg:
                info = f"<b>Descripción:</b> {pkg.description or 'Sin descripción'}<br>"
                info += f"<b>Precio:</b> ${pkg.price:.2f}<br>"
                info += f"<b>Clases:</b> {pkg.total_classes}<br>"
                if pkg.validity_days:
                    info += f"<b>Válido por:</b> {pkg.validity_days} días"
                else:
                    info += "<b>Sin fecha de expiración</b>"
                self.package_info_label.setText(info)
        finally:
            session.close()

    # ----------------------------------------------------------------------
    # OPERACIONES DE PAGO DE CLASE INDIVIDUAL
    # ----------------------------------------------------------------------
    def load_student_reservations(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            self.class_combo.clear()
            self.class_info_group.setVisible(False)
            self.payments_table.setRowCount(0)
            return

        session = get_session()
        try:
            reservations = session.exec(
                select(Reserve).where(
                    Reserve.student_id == student_id, Reserve.status == "active"
                )
            ).all()

            self.class_combo.clear()
            self.class_combo.addItem("-- Seleccionar Clase --", None)

            for reserve in reservations:
                yoga_class = session.get(YogaClass, reserve.yogaclass_id)
                if yoga_class:
                    if self.center_ids and yoga_class.center_id not in self.center_ids:
                        continue
                    existing_payment = session.exec(
                        select(Payment).where(
                            Payment.student_id == student_id,
                            Payment.yogaclass_id == yoga_class.id,
                            Payment.status == "paid",
                        )
                    ).first()

                    if not existing_payment:
                        class_date = yoga_class.scheduled_at.strftime("%Y-%m-%d %H:%M")
                        self.class_combo.addItem(
                            f"Clase #{yoga_class.id} - {class_date} - ${yoga_class.price:.2f}",
                            yoga_class.id,
                        )

            self.load_student_payments()

        finally:
            session.close()

    def update_payment_info(self):
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
        student_id = self.student_combo.currentData()
        class_id = self.class_combo.currentData()
        amount = self.amount_input.value()
        method = self.method_combo.currentText().split(" ")[-1]
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

            if yoga_class.center_id not in self.center_ids:
                QMessageBox.warning(
                    self,
                    "Acceso denegado",
                    "No tiene permisos para procesar pagos de esta clase (centro no asignado).",
                )
                return

            reserve = session.exec(
                select(Reserve).where(
                    Reserve.student_id == student_id,
                    Reserve.yogaclass_id == class_id,
                    Reserve.status == "active",
                )
            ).first()
            if not reserve:
                QMessageBox.warning(
                    self,
                    "Sin Reserva",
                    f"El estudiante {student.name} no tiene una reserva activa para esta clase.",
                )
                return

            existing = session.exec(
                select(Payment).where(
                    Payment.student_id == student_id,
                    Payment.yogaclass_id == class_id,
                    Payment.status == "paid",
                )
            ).first()
            if existing:
                QMessageBox.warning(
                    self,
                    "Pago Existente",
                    f"El estudiante {student.name} ya pagó esta clase el {existing.paid_at.strftime('%Y-%m-%d')}.",
                )
                return

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
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                payment = add_payment(
                    student_id=student_id,
                    yogaclass_id=class_id,
                    amount=amount,
                    payment_method=method,
                )
                if payment:
                    if reference:
                        payment.reference = reference
                        session.commit()

                    receipt_info = self.generate_receipt(payment, student, yoga_class)

                    QMessageBox.information(
                        self,
                        "✅ Pago Procesado",
                        f"¡Pago procesado exitosamente!\n\n"
                        f"📄 Comprobante: {payment.id:06d}\n"
                        f"👤 Estudiante: {student.name}\n"
                        f"🎯 Clase: #{yoga_class.id}\n"
                        f"💰 Monto: ${amount:.2f}\n"
                        f"💳 Método: {method}\n"
                        f"📅 Fecha: {payment.paid_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"{receipt_info}",
                    )

                    self.reference_input.clear()
                    self.load_student_reservations()
                    self.class_info_group.setVisible(False)
                else:
                    QMessageBox.critical(self, "Error", "No se pudo procesar el pago")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al procesar el pago: {str(e)}")
        finally:
            session.close()

    def generate_receipt(self, payment, student, yoga_class) -> str:
        session = get_session()
        try:
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

    # ----------------------------------------------------------------------
    # OPERACIONES DE PAQUETES
    # ----------------------------------------------------------------------
    def load_student_packages(self):
        student_id = self.pkg_student_combo.currentData()
        if not student_id:
            self.student_packages_table.setRowCount(0)
            return

        packages = get_student_packages(student_id)
        self.student_packages_table.setRowCount(len(packages))

        for row, sp in enumerate(packages):
            self.student_packages_table.setItem(
                row, 0, QTableWidgetItem(sp.package.name)
            )

            purchased = sp.purchased_at.strftime("%Y-%m-%d") if sp.purchased_at else ""
            self.student_packages_table.setItem(row, 1, QTableWidgetItem(purchased))

            expires = (
                sp.expires_at.strftime("%Y-%m-%d")
                if sp.expires_at
                else "Sin expiración"
            )
            self.student_packages_table.setItem(row, 2, QTableWidgetItem(expires))

            self.student_packages_table.setItem(
                row, 3, QTableWidgetItem(str(sp.remaining_classes))
            )

            status_item = QTableWidgetItem(sp.status)
            if sp.status == "active":
                status_item.setForeground(QColor("green"))
            elif sp.status == "used":
                status_item.setForeground(QColor("gray"))
            elif sp.status == "cancelled":
                status_item.setForeground(QColor("red"))
            elif sp.status == "reserved":
                status_item.setForeground(QColor("orange"))
            self.student_packages_table.setItem(row, 4, status_item)

            if sp.status == "active":
                cancel_btn = QPushButton("Cancelar")
                cancel_btn.setFixedSize(80, 30)
                cancel_btn.clicked.connect(partial(self.cancel_package, sp.id))
                self.student_packages_table.setCellWidget(row, 5, cancel_btn)

    def load_pending_packages(self):
        student_id = self.pkg_student_combo.currentData()
        if not student_id:
            self.pending_packages_table.setRowCount(0)
            return

        session = get_session()
        try:
            pending = session.exec(
                select(StudentPackage)
                .where(
                    StudentPackage.student_id == student_id,
                    StudentPackage.status == "reserved",
                )
                .options(selectinload(StudentPackage.package))
                .order_by(desc(StudentPackage.purchased_at))
            ).all()

            self.pending_packages_table.setRowCount(len(pending))

            for row, sp in enumerate(pending):
                self.pending_packages_table.setItem(
                    row, 0, QTableWidgetItem(sp.package.name)
                )

                self.pending_packages_table.setItem(
                    row, 1, QTableWidgetItem(sp.purchased_at.strftime("%Y-%m-%d %H:%M"))
                )

                self.pending_packages_table.setItem(
                    row, 2, QTableWidgetItem(f"${sp.package.price:.2f}")
                )

                payment = session.exec(
                    select(Payment).where(
                        Payment.package_id == sp.package_id,
                        Payment.student_id == student_id,
                        Payment.status == "pending",
                    )
                ).first()
                method = payment.payment_method if payment else "N/A"
                self.pending_packages_table.setItem(row, 3, QTableWidgetItem(method))

                pay_btn = QPushButton("💳 Pagar")
                pay_btn.clicked.connect(partial(self.complete_package_payment, sp.id))
                self.pending_packages_table.setCellWidget(row, 4, pay_btn)

        finally:
            session.close()

    def purchase_package(self):
        student_id = self.pkg_student_combo.currentData()
        package_id = self.package_combo.currentData()
        method = self.pkg_method_combo.currentText().split(" ")[-1]
        reference = self.pkg_reference_input.text().strip()

        if not student_id or not package_id:
            QMessageBox.warning(self, "Error", "Seleccione estudiante y paquete")
            return

        if self.pay_later_check.isChecked():
            self.reserve_package()
            return

        result = purchase_package(
            student_id=student_id,
            package_id=package_id,
            payment_method=method,
            reference=reference,
        )
        if result:
            QMessageBox.information(self, "Éxito", "Paquete comprado exitosamente")
            self.load_student_packages()
            self.pkg_reference_input.clear()
        else:
            QMessageBox.critical(self, "Error", "No se pudo comprar el paquete")

    def reserve_package(self):
        student_id = self.pkg_student_combo.currentData()
        package_id = self.package_combo.currentData()
        method = self.pkg_method_combo.currentText().split(" ")[-1]
        reference = self.pkg_reference_input.text().strip()

        if not student_id or not package_id:
            QMessageBox.warning(self, "Error", "Seleccione estudiante y paquete")
            return

        result = reserve_package(
            student_id=student_id,
            package_id=package_id,
            payment_method=method,
            reference=reference,
        )
        if result:
            QMessageBox.information(
                self,
                "Éxito",
                "Paquete reservado correctamente. El pago queda pendiente.",
            )
            self.load_pending_packages()
            self.load_student_packages()
            self.pkg_reference_input.clear()
        else:
            QMessageBox.critical(self, "Error", "No se pudo reservar el paquete")

    def complete_package_payment(self, sp_id: int):
        session = get_session()
        try:
            sp = session.get(StudentPackage, sp_id)
            if not sp:
                QMessageBox.critical(self, "Error", "Paquete no encontrado")
                return
            payment = session.exec(
                select(Payment).where(
                    Payment.package_id == sp.package_id,
                    Payment.student_id == sp.student_id,
                    Payment.status == "pending",
                )
            ).first()
            if not payment:
                QMessageBox.critical(self, "Error", "No se encontró el pago pendiente")
                return

            reply = QMessageBox.question(
                self,
                "Confirmar pago",
                f"¿Desea confirmar el pago del paquete '{sp.package.name}' por ${sp.package.price:.2f}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if confirm_package_payment(sp_id, payment.id):
                    QMessageBox.information(
                        self, "Éxito", "Pago confirmado. El paquete ahora está activo."
                    )
                    self.load_pending_packages()
                    self.load_student_packages()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo confirmar el pago")
        finally:
            session.close()

    def cancel_package(self, sp_id: int):
        reply = QMessageBox.question(
            self,
            "Cancelar Paquete",
            "¿Está seguro que desea cancelar este paquete? No se realizará reembolso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if cancel_student_package(sp_id):
                QMessageBox.information(
                    self, "Cancelado", "El paquete ha sido cancelado."
                )
                self.load_student_packages()
            else:
                QMessageBox.critical(self, "Error", "No se pudo cancelar el paquete.")

    # ----------------------------------------------------------------------
    # OPERACIONES DE RESERVA DE CLASE
    # ----------------------------------------------------------------------
    def load_available_classes_for_reservation(self):
        student_id = self.res_student_combo.currentData()
        if not student_id:
            self.res_class_combo.clear()
            self.res_info_label.setText("")
            return

        date = self.res_date_input.date().toPyDate()
        session = get_session()
        try:
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date, datetime.max.time())

            query = select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at <= end_date,
                YogaClass.current_capacity < YogaClass.max_capacity,
                YogaClass.center_id.in_(self.center_ids),
            )
            if self.center_ids:
                query = query.where(YogaClass.center_id.in_(self.center_ids))
            classes = session.exec(query).all()

            reserved_ids = session.exec(
                select(Reserve.yogaclass_id).where(
                    Reserve.student_id == student_id, Reserve.status == "active"
                )
            ).all()
            reserved_set = set(r for r in reserved_ids)
            available = [c for c in classes if c.id not in reserved_set]

            self.res_class_combo.clear()
            self.res_class_combo.addItem("-- Seleccionar clase --", None)
            for c in available:
                teacher = session.get(User, c.teacher_id)
                teacher_name = teacher.name if teacher else "N/A"
                text = f"Clase #{c.id} - {c.scheduled_at.strftime('%H:%M')} - {teacher_name} - ${c.price:.2f}"
                self.res_class_combo.addItem(text, c.id)
        finally:
            session.close()

    def update_reservation_info(self):
        class_id = self.res_class_combo.currentData()
        if not class_id:
            self.res_info_label.setText("")
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            if yoga_class:
                teacher = session.get(User, yoga_class.teacher_id)
                center = session.get(Center, yoga_class.center_id)
                info = f"<b>Profesor:</b> {teacher.name if teacher else 'N/A'}<br>"
                info += f"<b>Centro:</b> {center.name if center else 'N/A'}<br>"
                info += f"<b>Capacidad:</b> {yoga_class.current_capacity}/{yoga_class.max_capacity}<br>"
                info += f"<b>Precio:</b> ${yoga_class.price:.2f}"
                self.res_info_label.setText(info)
        finally:
            session.close()

    def reserve_class_for_student(self):
        student_id = self.res_student_combo.currentData()
        class_id = self.res_class_combo.currentData()

        if not student_id or not class_id:
            QMessageBox.warning(self, "Error", "Seleccione estudiante y clase")
            return

        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            if yoga_class and yoga_class.center_id not in self.center_ids:
                QMessageBox.warning(
                    self,
                    "Acceso denegado",
                    "No tiene permisos para reservar esta clase (centro no asignado).",
                )
                return
        finally:
            session.close()

        reserve = add_reservation(student_id, class_id)
        if reserve:
            QMessageBox.information(
                self,
                "Reserva exitosa",
                f"Se ha creado la reserva para el estudiante.\n"
                f"Recuérdeles pagar antes de la clase.",
            )
            self.load_available_classes_for_reservation()
        else:
            QMessageBox.warning(
                self, "Error", "No se pudo reservar (clase llena o ya reservada)."
            )

    # ----------------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # ----------------------------------------------------------------------
    def load_student_payments(self):
        student_id = self.student_combo.currentData()
        if not student_id:
            return

        session = get_session()
        try:
            start_date = datetime.combine(
                self.filter_date.date().toPyDate(), datetime.min.time()
            )
            payments = session.exec(
                select(Payment)
                .where(Payment.student_id == student_id, Payment.paid_at >= start_date)
                .order_by(Payment.paid_at.desc())
            ).all()

            self.payments_table.setRowCount(len(payments))
            for row, payment in enumerate(payments):
                # Fecha
                self.payments_table.setItem(
                    row, 0, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d %H:%M"))
                )

                # Clase (puede ser None si es pago de paquete)
                if payment.yogaclass_id:
                    yoga_class = session.get(YogaClass, payment.yogaclass_id)
                    class_info = f"Clase #{yoga_class.id}" if yoga_class else "N/A"
                else:
                    class_info = "Paquete"
                self.payments_table.setItem(row, 1, QTableWidgetItem(class_info))

                # Monto
                amount_item = QTableWidgetItem(f"${payment.amount:.2f}")
                amount_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.payments_table.setItem(row, 2, amount_item)

                # Método
                self.payments_table.setItem(
                    row, 3, QTableWidgetItem(payment.payment_method)
                )

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
