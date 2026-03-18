from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QComboBox,
    QLineEdit,
    QDialogButtonBox,
    QFormLayout,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database.db import get_active_packages, purchase_package, reserve_package


class PackagePurchaseDialog(QDialog):
    def __init__(self, student_id, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.selected_package_id = None
        self.setWindowTitle("🛒 Comprar / Reservar Paquete")
        self.setFixedSize(650, 550)
        self.init_ui()
        self.load_packages()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Selecciona un paquete")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Tabla de paquetes
        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(5)
        self.packages_table.setHorizontalHeaderLabels(
            ["Paquete", "Clases", "Precio", "Vigencia", "Seleccionar"]
        )
        self.packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.packages_table)

        # Detalles del pago
        form_layout = QFormLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems(
            [
                "Efectivo",
                "Tarjeta de Crédito",
                "Tarjeta de Débito",
                "Transferencia",
                "Pago Móvil",
            ]
        )
        form_layout.addRow("Método de pago:", self.method_combo)

        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("Número de referencia (opcional)")
        form_layout.addRow("Referencia:", self.reference_input)

        # ADDED: Checkbox para pagar después
        self.pay_later_check = QCheckBox("Pagar después (reservar)")
        form_layout.addRow(self.pay_later_check)

        layout.addLayout(form_layout)

        # Botones
        btn_layout = QHBoxLayout()
        buy_btn = QPushButton("💳 Comprar ahora")
        buy_btn.clicked.connect(self.purchase)
        reserve_btn = QPushButton("📦 Reservar (pagar después)")
        reserve_btn.clicked.connect(self.reserve)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(buy_btn)
        btn_layout.addWidget(reserve_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_packages(self):
        packages = get_active_packages()
        self.packages_table.setRowCount(len(packages))

        for row, pkg in enumerate(packages):
            self.packages_table.setItem(row, 0, QTableWidgetItem(pkg.name))
            self.packages_table.setItem(
                row, 1, QTableWidgetItem(str(pkg.total_classes))
            )
            self.packages_table.setItem(row, 2, QTableWidgetItem(f"${pkg.price:.2f}"))
            vigencia = (
                f"{pkg.validity_days} días" if pkg.validity_days else "Sin expiración"
            )
            self.packages_table.setItem(row, 3, QTableWidgetItem(vigencia))

            btn_select = QPushButton("Seleccionar")
            btn_select.clicked.connect(
                lambda checked, pid=pkg.id: self.select_package(pid)
            )
            self.packages_table.setCellWidget(row, 4, btn_select)

    def select_package(self, package_id):
        self.selected_package_id = package_id
        # Resaltar fila
        for row in range(self.packages_table.rowCount()):
            if (
                self.packages_table.cellWidget(row, 4)
                and self.packages_table.cellWidget(row, 4).text() == "Seleccionar"
            ):
                self.packages_table.cellWidget(row, 4).setStyleSheet("")
        sender = self.sender()
        if sender:
            sender.setStyleSheet("background-color: #2ecc71; color: white;")
        QMessageBox.information(
            self, "Paquete seleccionado", "Ahora presione 'Comprar ahora' o 'Reservar'."
        )

    def purchase(self):
        if not self.selected_package_id:
            QMessageBox.warning(self, "Error", "Debe seleccionar un paquete.")
            return

        method = self.method_combo.currentText()
        reference = self.reference_input.text().strip()

        sp = purchase_package(
            student_id=self.student_id,
            package_id=self.selected_package_id,
            payment_method=method,
            reference=reference,
        )
        if sp:
            QMessageBox.information(self, "Éxito", "Paquete comprado exitosamente.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudo realizar la compra.")

    def reserve(self):
        """Reserva el paquete (pago pendiente)."""
        if not self.selected_package_id:
            QMessageBox.warning(self, "Error", "Debe seleccionar un paquete.")
            return

        method = self.method_combo.currentText()
        reference = self.reference_input.text().strip()

        sp = reserve_package(
            student_id=self.student_id,
            package_id=self.selected_package_id,
            payment_method=method,
            reference=reference,
        )
        if sp:
            QMessageBox.information(
                self,
                "Reserva exitosa",
                "Paquete reservado correctamente. Deberá completar el pago desde la sección de pagos."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudo reservar el paquete.")
