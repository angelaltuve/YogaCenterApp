from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QTabWidget,
    QDateEdit,
    QComboBox,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QLineEdit,
    QDoubleSpinBox,
    QGroupBox,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from datetime import datetime
from functools import partial

from sqlalchemy.orm import selectinload
from sqlalchemy import desc

from database.db import (
    get_session,
    select,
    Payment,
    User,
    YogaClass,
    Role,
    get_payments_by_teacher,
    get_all_payments,
    get_total_earnings_by_teacher,
    add_payment,
    Reserve,
    get_student_packages,
    cancel_student_package,
    PackageUsage,
    cancel_reservation,
    get_active_student_packages,
    confirm_package_payment,
    cancel_reserved_package,   # ADDED
    StudentPackage,
    Package,
)
from ui.payment_dialog import PaymentDialog
from ui.package_purchase_dialog import PackagePurchaseDialog


class PaymentsWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user

        # Inicializar atributos de las tablas
        self.student_payments_table = None
        self.packages_table = None
        self.teacher_earnings_table = None
        self.admin_payments_table = None
        self.reservations_table = None
        self.pending_packages_table = None

        self.init_ui()

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL
    # -------------------------------------------------------------------------
    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        if self.current_user.role == Role.STUDENT:
            self.tabs.addTab(self.create_student_payments_tab(), "Mis Pagos")

        elif self.current_user.role == Role.TEACHER:
            self.tabs.addTab(self.create_teacher_earnings_tab(), "Mis Ganancias")
            self.load_teacher_earnings()

        elif self.current_user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            self.tabs.addTab(self.create_admin_payments_tab(), "Gestión de Pagos")
            self.load_admin_payments()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # -------------------------------------------------------------------------
    # PESTAÑA PARA ESTUDIANTES (Pagos + Paquetes)
    # -------------------------------------------------------------------------
    def create_student_payments_tab(self):
        """Crea la pestaña completa para estudiantes con subpestañas."""
        widget = QWidget()
        layout = QVBoxLayout()

        inner_tabs = QTabWidget()

        # ---- Subpestaña 1: Reservas activas ----
        reservations_tab = QWidget()
        res_layout = QVBoxLayout()

        # Botón de refrescar
        refresh_btn = QPushButton("🔄 Actualizar reservas")
        refresh_btn.clicked.connect(self.load_student_reservations)
        res_layout.addWidget(refresh_btn)

        # Tabla de reservas
        self.reservations_table = QTableWidget()
        self.reservations_table.setColumnCount(6)
        self.reservations_table.setHorizontalHeaderLabels(
            ["Fecha", "Hora", "Clase", "Profesor", "Estado de pago", "Acciones"]
        )
        self.reservations_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        res_layout.addWidget(self.reservations_table)

        reservations_tab.setLayout(res_layout)
        inner_tabs.addTab(reservations_tab, "📅 Mis Reservas")

        # ---- Subpestaña 2: Paquetes ----
        packages_tab = self.create_student_packages_tab()
        inner_tabs.addTab(packages_tab, "📦 Mis Paquetes")

        layout.addWidget(inner_tabs)
        widget.setLayout(layout)

        # Cargar datos
        self.load_student_reservations()
        self.load_student_packages()
        self.load_pending_packages()

        return widget

    def load_student_reservations(self):
        """Carga las reservas activas del estudiante en la tabla."""
        if not hasattr(self, 'reservations_table'):
            return
        session = get_session()
        try:
            reserves = session.exec(
                select(Reserve)
                .where(Reserve.student_id == self.current_user.id, Reserve.status == "active")
                .order_by(Reserve.reserved_at.desc())
            ).all()

            self.reservations_table.setRowCount(len(reserves))

            for row, res in enumerate(reserves):
                yoga_class = session.get(YogaClass, res.yogaclass_id)
                if not yoga_class:
                    continue
                teacher = session.get(User, yoga_class.teacher_id)

                # Determinar si la reserva está pagada
                payment = session.exec(
                    select(Payment).where(
                        Payment.student_id == self.current_user.id,
                        Payment.yogaclass_id == yoga_class.id,
                        Payment.status == "paid"
                    )
                ).first()
                usage = session.exec(
                    select(PackageUsage).where(
                        PackageUsage.yogaclass_id == yoga_class.id,
                        PackageUsage.student_package.has(student_id=self.current_user.id)
                    )
                ).first()

                if payment:
                    status = "✅ Pagado (efectivo)"
                elif usage:
                    status = "📦 Pagado (paquete)"
                else:
                    status = "⏳ Pendiente"

                # Fecha
                self.reservations_table.setItem(
                    row, 0,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%Y-%m-%d"))
                )
                # Hora
                self.reservations_table.setItem(
                    row, 1,
                    QTableWidgetItem(yoga_class.scheduled_at.strftime("%H:%M"))
                )
                # Clase
                self.reservations_table.setItem(
                    row, 2,
                    QTableWidgetItem(f"Clase #{yoga_class.id}")
                )
                # Profesor
                self.reservations_table.setItem(
                    row, 3,
                    QTableWidgetItem(teacher.name if teacher else "N/A")
                )
                # Estado de pago
                self.reservations_table.setItem(row, 4, QTableWidgetItem(status))

                # Acciones
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(0, 0, 0, 0)

                # Botón Pagar (solo si está pendiente)
                if not payment and not usage:
                    pay_btn = QPushButton("💳 Pagar")
                    pay_btn.clicked.connect(
                        lambda checked, rid=res.id, cid=yoga_class.id, amount=yoga_class.price:
                        self.pay_reservation(rid, cid, amount)
                    )
                    action_layout.addWidget(pay_btn)

                # Botón Cancelar (siempre)
                cancel_btn = QPushButton("❌ Cancelar")
                cancel_btn.clicked.connect(
                    lambda checked, rid=res.id: self.cancel_reservation(rid)
                )
                action_layout.addWidget(cancel_btn)

                action_widget.setLayout(action_layout)
                self.reservations_table.setCellWidget(row, 5, action_widget)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar reservas: {str(e)}")
        finally:
            session.close()

    def pay_reservation(self, reserve_id, class_id, amount):
        """Abre un diálogo para pagar una reserva específica."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Pagar reserva")
        layout = QFormLayout(dialog)

        amount_label = QLabel(f"${amount:.2f}")
        method_combo = QComboBox()
        method_combo.addItems(["Efectivo", "Tarjeta Crédito", "Tarjeta Débito", "Transferencia"])

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(
            lambda: self.process_payment(reserve_id, class_id, amount, method_combo.currentText(), dialog)
        )
        buttons.rejected.connect(dialog.reject)

        layout.addRow("Monto:", amount_label)
        layout.addRow("Método de pago:", method_combo)
        layout.addRow(buttons)

        dialog.setLayout(layout)
        dialog.exec()

    def process_payment(self, reserve_id, class_id, amount, method, dialog):
        """Procesa el pago y cierra el diálogo."""
        payment = add_payment(
            student_id=self.current_user.id,
            yogaclass_id=class_id,
            amount=amount,
            payment_method=method
        )
        if payment:
            QMessageBox.information(self, "Éxito", "Pago realizado correctamente.")
            dialog.accept()
            self.load_student_reservations()
        else:
            QMessageBox.critical(self, "Error", "No se pudo procesar el pago.")

    def cancel_reservation(self, reserve_id):
        """Cancela una reserva llamando a la función de db."""
        reply = QMessageBox.question(
            self,
            "Cancelar reserva",
            "¿Está seguro de cancelar esta reserva?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = cancel_reservation(reserve_id)
            if success:
                QMessageBox.information(self, "Cancelada", msg)
                self.load_student_reservations()
            else:
                QMessageBox.critical(self, "Error", msg)

    def create_student_packages_tab(self):
        """Crea el contenido de la pestaña 'Mis Paquetes'."""
        widget = QWidget()
        layout = QVBoxLayout()

        buy_btn = QPushButton("🛒 Comprar / Reservar nuevo paquete")
        buy_btn.clicked.connect(self.show_buy_package_dialog)
        layout.addWidget(buy_btn)

        # Tabla de paquetes reservados pendientes de pago
        pending_group = QGroupBox("⏳ Paquetes reservados pendientes de pago")
        pending_layout = QVBoxLayout()
        self.pending_packages_table = QTableWidget()
        self.pending_packages_table.setColumnCount(5)
        self.pending_packages_table.setHorizontalHeaderLabels(
            ["Paquete", "Fecha reserva", "Monto", "Método", "Acciones"]
        )
        self.pending_packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        pending_layout.addWidget(self.pending_packages_table)
        pending_group.setLayout(pending_layout)
        layout.addWidget(pending_group)

        # Tabla de paquetes activos/comprados
        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(6)
        self.packages_table.setHorizontalHeaderLabels(
            ["Paquete", "Comprado", "Expira", "Clases rest.", "Estado", "Acciones"]
        )
        self.packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.packages_table)

        widget.setLayout(layout)
        return widget

    def load_student_packages(self):
        """Carga los paquetes del estudiante en la tabla con manejo seguro de sesión."""
        if not self.packages_table:
            return

        try:
            sp_list = get_student_packages(self.current_user.id)
            # Filtrar solo los que no son 'reserved' para esta tabla
            sp_list = [sp for sp in sp_list if sp.status != 'reserved']
            self.packages_table.setRowCount(len(sp_list))

            for row, sp in enumerate(sp_list):
                # Para evitar DetachedInstanceError, obtenemos el nombre del paquete en una nueva sesión
                package_name = "Desconocido"
                session = get_session()
                try:
                    from database.db import StudentPackage, Package
                    sp_refreshed = session.get(StudentPackage, sp.id)
                    if sp_refreshed and sp_refreshed.package:
                        package_name = sp_refreshed.package.name
                except Exception:
                    package_name = "Desconocido"
                finally:
                    session.close()

                self.packages_table.setItem(row, 0, QTableWidgetItem(package_name))

                # Fecha compra
                self.packages_table.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        sp.purchased_at.strftime("%Y-%m-%d") if sp.purchased_at else ""
                    ),
                )

                # Fecha expiración
                expires = (
                    sp.expires_at.strftime("%Y-%m-%d")
                    if sp.expires_at
                    else "Sin expiración"
                )
                self.packages_table.setItem(row, 2, QTableWidgetItem(expires))

                # Clases restantes
                self.packages_table.setItem(
                    row, 3, QTableWidgetItem(str(sp.remaining_classes))
                )

                # Estado
                status_item = QTableWidgetItem(sp.status)
                if sp.status == "active":
                    status_item.setForeground(QColor("green"))
                elif sp.status == "used":
                    status_item.setForeground(QColor("gray"))
                elif sp.status == "cancelled":
                    status_item.setForeground(QColor("red"))
                self.packages_table.setItem(row, 4, status_item)

                # Botón de cancelar (solo si está activo)
                if sp.status == "active":
                    cancel_btn = QPushButton("Cancelar")
                    cancel_btn.setFixedSize(80, 30)
                    cancel_btn.clicked.connect(partial(self.cancel_package, sp.id))
                    self.packages_table.setCellWidget(row, 5, cancel_btn)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar paquetes: {str(e)}")

    def load_pending_packages(self):
        """Carga los paquetes reservados (pendientes de pago) del estudiante."""
        if not self.pending_packages_table:
            return

        session = get_session()
        try:
            pending = session.exec(
                select(StudentPackage)
                .where(
                    StudentPackage.student_id == self.current_user.id,
                    StudentPackage.status == "reserved"
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
                        Payment.student_id == self.current_user.id,
                        Payment.status == "pending"
                    )
                ).first()
                method = payment.payment_method if payment else "N/A"
                self.pending_packages_table.setItem(row, 3, QTableWidgetItem(method))

                # Acciones: Pagar y Cancelar
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(0, 0, 0, 0)

                pay_btn = QPushButton("💳 Pagar")
                pay_btn.clicked.connect(partial(self.complete_package_payment, sp.id))
                action_layout.addWidget(pay_btn)

                cancel_btn = QPushButton("❌ Cancelar")
                cancel_btn.clicked.connect(partial(self.cancel_reserved_package, sp.id))
                action_layout.addWidget(cancel_btn)

                action_widget.setLayout(action_layout)
                self.pending_packages_table.setCellWidget(row, 4, action_widget)

        finally:
            session.close()

    def complete_package_payment(self, sp_id: int):
        """Completa el pago de un paquete reservado."""
        session = get_session()
        try:
            sp = session.get(StudentPackage, sp_id)
            if not sp:
                QMessageBox.critical(self, "Error", "Paquete no encontrado")
                return
            payment = session.exec(
                select(Payment).where(
                    Payment.package_id == sp.package_id,
                    Payment.student_id == self.current_user.id,
                    Payment.status == "pending"
                )
            ).first()
            if not payment:
                QMessageBox.critical(self, "Error", "No se encontró el pago pendiente")
                return

            reply = QMessageBox.question(
                self,
                "Confirmar pago",
                f"¿Desea confirmar el pago del paquete '{sp.package.name}' por ${sp.package.price:.2f}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if confirm_package_payment(sp_id, payment.id):
                    QMessageBox.information(self, "Éxito", "Pago confirmado. El paquete ahora está activo.")
                    self.load_pending_packages()
                    self.load_student_packages()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo confirmar el pago")
        finally:
            session.close()

    def cancel_reserved_package(self, sp_id: int):
        """Cancela un paquete reservado (no pagado)."""
        reply = QMessageBox.question(
            self,
            "Cancelar reserva de paquete",
            "¿Está seguro que desea cancelar esta reserva? El paquete no será activado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if cancel_reserved_package(sp_id):
                QMessageBox.information(self, "Cancelado", "La reserva del paquete ha sido cancelada.")
                self.load_pending_packages()
                self.load_student_packages()
            else:
                QMessageBox.critical(self, "Error", "No se pudo cancelar la reserva.")

    def show_buy_package_dialog(self):
        dialog = PackagePurchaseDialog(self.current_user.id, self)
        if dialog.exec():
            self.load_student_packages()
            self.load_pending_packages()

    def cancel_package(self, sp_id):
        """Cancela un paquete del estudiante."""
        reply = QMessageBox.question(
            self,
            "Cancelar paquete",
            "¿Está seguro que desea cancelar este paquete? No se realizará reembolso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if cancel_student_package(sp_id):
                QMessageBox.information(
                    self, "Cancelado", "El paquete ha sido cancelado."
                )
                self.load_student_packages()
            else:
                QMessageBox.critical(self, "Error", "No se pudo cancelar el paquete.")

    # -------------------------------------------------------------------------
    # PESTAÑA PARA PROFESORES (Ganancias)
    # -------------------------------------------------------------------------
    def create_teacher_earnings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Estadísticas
        stats_layout = QHBoxLayout()
        self.earnings_label = QLabel("💰 Seleccione un período y presione Filtrar")
        self.earnings_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2ecc71;"
        )
        stats_layout.addWidget(self.earnings_label)
        stats_layout.addStretch()

        # Filtros
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

        # Tabla
        self.teacher_earnings_table = QTableWidget()
        self.teacher_earnings_table.setColumnCount(5)
        self.teacher_earnings_table.setHorizontalHeaderLabels(
            ["Fecha", "Clase", "Alumno", "Comisión", "Estado"]
        )
        self.teacher_earnings_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addLayout(stats_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.teacher_earnings_table)

        widget.setLayout(layout)
        return widget

    def load_teacher_earnings(self):
        if not self.teacher_earnings_table:
            return

        start_date = datetime.combine(
            self.teacher_start_date.date().toPyDate(), datetime.min.time()
        )
        end_date = datetime.combine(
            self.teacher_end_date.date().toPyDate(), datetime.max.time()
        )

        session = get_session()
        try:
            payments = get_payments_by_teacher(
                self.current_user.id, start_date, end_date
            )
            self.teacher_earnings_table.setRowCount(len(payments))

            total_earnings_period = 0.0

            for row, payment in enumerate(payments):
                self.teacher_earnings_table.setItem(
                    row, 0, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d"))
                )

                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                class_info = f"Clase {yoga_class.id}" if yoga_class else "N/A"
                self.teacher_earnings_table.setItem(
                    row, 1, QTableWidgetItem(class_info)
                )

                student = session.get(User, payment.student_id)
                student_name = student.name if student else "N/A"
                self.teacher_earnings_table.setItem(
                    row, 2, QTableWidgetItem(student_name)
                )

                # Calcular la comisión real del profesor
                if yoga_class:
                    teacher_share = payment.amount * (
                        yoga_class.teacher_share_percentage / 100
                    )
                else:
                    teacher_share = 0.0
                total_earnings_period += teacher_share

                self.teacher_earnings_table.setItem(
                    row, 3, QTableWidgetItem(f"${teacher_share:.2f}")
                )

                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                self.teacher_earnings_table.setItem(row, 4, status_item)

            # Actualizar la etiqueta con el total del período filtrado
            self.earnings_label.setText(
                f"💰 Ganancias en el período: ${total_earnings_period:.2f}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar ganancias: {str(e)}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # PESTAÑA PARA ADMINISTRADORES/RECEPCIONISTAS (Gestión de Pagos)
    # -------------------------------------------------------------------------
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

        for label in [
            self.total_revenue_label,
            self.monthly_revenue_label,
            self.pending_payments_label,
        ]:
            label.setStyleSheet(
                "font-size: 14px; padding: 5px; background-color: #f8f9fa; border-radius: 5px;"
            )

        stats_layout.addWidget(self.total_revenue_label)
        stats_layout.addWidget(self.monthly_revenue_label)
        stats_layout.addWidget(self.pending_payments_label)
        stats_layout.addStretch()

        # Tabla
        self.admin_payments_table = QTableWidget()
        self.admin_payments_table.setColumnCount(8)
        self.admin_payments_table.setHorizontalHeaderLabels(
            ["ID", "Alumno", "Profesor", "Clase", "Fecha", "Monto", "Método", "Estado"]
        )
        self.admin_payments_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addLayout(filter_layout)
        layout.addLayout(stats_layout)
        layout.addWidget(self.admin_payments_table)
        widget.setLayout(layout)

        return widget

    def load_admin_payments(self):
        if not self.admin_payments_table:
            return

        start_date = datetime.combine(
            self.admin_start_date.date().toPyDate(), datetime.min.time()
        )
        end_date = datetime.combine(
            self.admin_end_date.date().toPyDate(), datetime.max.time()
        )
        status_filter = self.status_combo.currentText()

        session = get_session()
        try:
            payments = get_all_payments(start_date, end_date)

            if status_filter != "Todos":
                payments = [p for p in payments if p.status == status_filter]

            self.admin_payments_table.setRowCount(len(payments))

            total_revenue = 0.0
            monthly_revenue = 0.0
            pending_count = 0
            current_month = datetime.now().month
            current_year = datetime.now().year

            for row, payment in enumerate(payments):
                self.admin_payments_table.setItem(
                    row, 0, QTableWidgetItem(str(payment.id))
                )

                student = session.get(User, payment.student_id)
                student_name = student.name if student else "N/A"
                self.admin_payments_table.setItem(
                    row, 1, QTableWidgetItem(student_name)
                )

                yoga_class = session.get(YogaClass, payment.yogaclass_id)
                teacher_name = "N/A"
                if yoga_class and yoga_class.teacher_id:
                    teacher = session.get(User, yoga_class.teacher_id)
                    teacher_name = teacher.name if teacher else "N/A"
                self.admin_payments_table.setItem(
                    row, 2, QTableWidgetItem(teacher_name)
                )

                class_info = f"Clase {yoga_class.id}" if yoga_class else "N/A"
                self.admin_payments_table.setItem(row, 3, QTableWidgetItem(class_info))

                self.admin_payments_table.setItem(
                    row, 4, QTableWidgetItem(payment.paid_at.strftime("%Y-%m-%d"))
                )
                self.admin_payments_table.setItem(
                    row, 5, QTableWidgetItem(f"${payment.amount:.2f}")
                )
                self.admin_payments_table.setItem(
                    row, 6, QTableWidgetItem(payment.payment_method)
                )

                status_item = QTableWidgetItem(payment.status)
                if payment.status == "paid":
                    status_item.setForeground(QColor("green"))
                elif payment.status == "pending":
                    status_item.setForeground(QColor("orange"))
                    pending_count += 1
                elif payment.status == "refunded":
                    status_item.setForeground(QColor("red"))
                self.admin_payments_table.setItem(row, 7, status_item)

                # Solo los pagos 'paid' se cuentan como ingresos
                if payment.status == "paid":
                    total_revenue += payment.amount
                    if (
                        payment.paid_at.month == current_month
                        and payment.paid_at.year == current_year
                    ):
                        monthly_revenue += payment.amount

            self.total_revenue_label.setText(f"Ingresos Totales: ${total_revenue:.2f}")
            self.monthly_revenue_label.setText(
                f"Ingresos del Mes: ${monthly_revenue:.2f}"
            )
            self.pending_payments_label.setText(f"Pagos Pendientes: {pending_count}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar pagos: {str(e)}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # DIÁLOGO DE PAGO (redirige al diálogo existente)
    # -------------------------------------------------------------------------
    def show_payment_dialog(self):
        dialog = PaymentDialog(self.current_user)
        if dialog.exec():
            self.load_student_payments()
