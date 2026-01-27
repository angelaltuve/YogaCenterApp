from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt
from database.db import get_session, select, YogaClass, Reserve, Add_Payment

class PaymentDialog(QDialog):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        self.load_classes()

    def init_ui(self):
        self.setWindowTitle("Realizar Pago")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        form_layout = QVBoxLayout()

        # Selección de clase
        form_layout.addWidget(QLabel("Selecciona la clase:"))
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.update_amount)
        form_layout.addWidget(self.class_combo)

        # Monto (actualizado automáticamente según la clase)
        form_layout.addWidget(QLabel("Monto a pagar:"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1000)
        self.amount_spin.setValue(20.00)
        self.amount_spin.setPrefix("$ ")
        self.amount_spin.setDecimals(2)
        self.amount_spin.setReadOnly(True)  # Solo lectura, se actualiza automáticamente
        form_layout.addWidget(self.amount_spin)

        # Método de pago
        form_layout.addWidget(QLabel("Método de pago:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Efectivo", "Tarjeta de Crédito", "Tarjeta de Débito", "Transferencia"])
        form_layout.addWidget(self.method_combo)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.process_payment)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def load_classes(self):
        """Cargar clases reservadas pero no pagadas"""
        session = get_session()
        try:
            reservations = session.exec(
                select(Reserve).where(
                    Reserve.student_id == self.user.id,
                    Reserve.status == "active"
                )
            ).all()

            self.class_combo.clear()
            for reserve in reservations:
                yoga_class = session.get(YogaClass, reserve.yogaclass_id)
                if yoga_class:
                    # Verificar si ya se pagó esta clase
                    existing_payment = session.exec(
                        select(Payment).where(
                            Payment.student_id == self.user.id,
                            Payment.yogaclass_id == yoga_class.id,
                            Payment.status == "paid"
                        )
                    ).first()

                    if not existing_payment:
                        class_date = yoga_class.scheduled_at.strftime("%Y-%m-%d %H:%M")
                        self.class_combo.addItem(
                            f"Clase {yoga_class.id} - {class_date} - ${yoga_class.price:.2f}",
                            yoga_class.id
                        )

            if self.class_combo.count() == 0:
                QMessageBox.information(self, "Sin clases pendientes",
                                      "No tienes clases reservadas pendientes de pago.")
                self.reject()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar clases: {str(e)}")
            self.reject()
        finally:
            session.close()

    def update_amount(self):
        """Actualizar el monto cuando se selecciona una clase"""
        session = get_session()
        try:
            class_id = self.class_combo.currentData()
            if class_id:
                yoga_class = session.get(YogaClass, class_id)
                if yoga_class:
                    self.amount_spin.setValue(yoga_class.price)
        finally:
            session.close()

    def process_payment(self):
        class_id = self.class_combo.currentData()
        amount = self.amount_spin.value()
        method = self.method_combo.currentText()

        if not class_id:
            QMessageBox.warning(self, "Error", "Selecciona una clase")
            return

        # Validar que el monto sea correcto
        session = get_session()
        try:
            yoga_class = session.get(YogaClass, class_id)
            if not yoga_class:
                QMessageBox.warning(self, "Error", "Clase no encontrada")
                return

            if abs(amount - yoga_class.price) > 0.01:
                QMessageBox.warning(self, "Error",
                                  f"El monto debe ser ${yoga_class.price:.2f} para esta clase")
                return

            # Verificar si ya existe un pago para esta clase
            existing_payment = session.exec(
                select(Payment).where(
                    Payment.student_id == self.user.id,
                    Payment.yogaclass_id == class_id,
                    Payment.status == "paid"
                )
            ).first()

            if existing_payment:
                QMessageBox.warning(self, "Error", "Ya has pagado esta clase")
                return

            # Crear el pago
            payment = Add_Payment(
                student_id=self.user.id,
                yogaclass_id=class_id,
                amount=amount,
                payment_method=method
            )

            QMessageBox.information(self, "Éxito",
                                  f"Pago realizado correctamente\n"
                                  f"Clase: {yoga_class.id}\n"
                                  f"Monto: ${amount:.2f}\n"
                                  f"Método: {method}\n"
                                  f"Fecha: {yoga_class.scheduled_at.strftime('%Y-%m-%d %H:%M')}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar el pago: {str(e)}")
        finally:
            session.close()
