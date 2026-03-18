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
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from database.db import (
    get_session,
    select,
    Package,
    get_active_packages,
    get_package_by_id,
    add_package,
    update_package,
    delete_package,
)


class PackageManagementWidget(QWidget):
    """Widget para gestionar paquetes (solo administradores)."""

    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.init_ui()
        self.load_packages()

    def init_ui(self):
        layout = QVBoxLayout()

        # Barra de herramientas
        toolbar = QHBoxLayout()

        add_btn = QPushButton("➕ Nuevo Paquete")
        add_btn.clicked.connect(self.show_add_dialog)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_packages)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabla de paquetes
        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(8)
        self.packages_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Nombre",
                "Descripción",
                "Clases",
                "Vigencia (días)",
                "Precio",
                "Activo",
                "Acciones",
            ]
        )
        self.packages_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        # Ajustar anchos específicos
        self.packages_table.setColumnWidth(0, 50)  # ID
        self.packages_table.setColumnWidth(2, 200)  # Descripción
        self.packages_table.setColumnWidth(6, 80)  # Activo
        self.packages_table.setColumnWidth(7, 120)  # Acciones

        layout.addWidget(self.packages_table)
        self.setLayout(layout)

    def load_packages(self):
        """Carga todos los paquetes desde la base de datos."""
        session = get_session()
        try:
            packages = session.exec(select(Package)).all()
            self.display_packages(packages)
        finally:
            session.close()

    def display_packages(self, packages):
        """Muestra los paquetes en la tabla."""
        self.packages_table.setRowCount(len(packages))

        for row, pkg in enumerate(packages):
            # ID
            self.packages_table.setItem(row, 0, QTableWidgetItem(str(pkg.id)))

            # Nombre
            self.packages_table.setItem(row, 1, QTableWidgetItem(pkg.name))

            # Descripción (acortada si es muy larga)
            desc = pkg.description or ""
            if len(desc) > 50:
                desc = desc[:47] + "..."
            self.packages_table.setItem(row, 2, QTableWidgetItem(desc))

            # Clases totales
            self.packages_table.setItem(
                row, 3, QTableWidgetItem(str(pkg.total_classes))
            )

            # Vigencia (días)
            validity = str(pkg.validity_days) if pkg.validity_days else "∞"
            self.packages_table.setItem(row, 4, QTableWidgetItem(validity))

            # Precio
            price_item = QTableWidgetItem(f"${pkg.price:.2f}")
            price_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.packages_table.setItem(row, 5, price_item)

            # Activo
            active_item = QTableWidgetItem("✅ Sí" if pkg.is_active else "❌ No")
            active_item.setForeground(
                QColor("green") if pkg.is_active else QColor("red")
            )
            self.packages_table.setItem(row, 6, active_item)

            # Botones de acción
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setToolTip("Editar paquete")
            edit_btn.clicked.connect(lambda checked, pid=pkg.id: self.edit_package(pid))

            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setToolTip("Eliminar paquete")
            delete_btn.clicked.connect(
                lambda checked, pid=pkg.id: self.delete_package(pid)
            )

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            action_widget.setLayout(action_layout)
            self.packages_table.setCellWidget(row, 7, action_widget)

    # ----------------------------------------------------------------------
    # Diálogos y operaciones
    # ----------------------------------------------------------------------
    def show_add_dialog(self):
        """Abre el diálogo para agregar un nuevo paquete."""
        dialog = PackageDialog(self)
        if dialog.exec():
            self.load_packages()

    def edit_package(self, package_id):
        """Abre el diálogo para editar un paquete existente."""
        dialog = PackageDialog(self, package_id)
        if dialog.exec():
            self.load_packages()

    def delete_package(self, package_id):
        """Elimina un paquete después de confirmación."""
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro que desea eliminar este paquete?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if delete_package(package_id):
                QMessageBox.information(
                    self, "Éxito", "Paquete eliminado correctamente."
                )
                self.load_packages()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el paquete.")


class PackageDialog(QDialog):
    """Diálogo para crear o editar un paquete."""

    def __init__(self, parent=None, package_id=None):
        super().__init__(parent)
        self.package_id = package_id
        self.setWindowTitle("Nuevo Paquete" if not package_id else "Editar Paquete")
        self.setFixedSize(500, 400)
        self.init_ui()
        if package_id:
            self.load_package_data()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)

        # Nombre
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Pack 10 clases")
        layout.addRow("📛 Nombre:", self.name_input)

        # Descripción
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Descripción del paquete (opcional)")
        self.desc_input.setMaximumHeight(80)
        layout.addRow("📝 Descripción:", self.desc_input)

        # Clases totales
        self.classes_input = QSpinBox()
        self.classes_input.setRange(1, 999)
        self.classes_input.setValue(10)
        layout.addRow("🧘 Clases totales:", self.classes_input)

        # Días de vigencia (opcional)
        self.validity_input = QSpinBox()
        self.validity_input.setRange(0, 3650)
        self.validity_input.setValue(30)
        self.validity_input.setSpecialValueText("Sin expiración")
        layout.addRow("⏳ Vigencia (días):", self.validity_input)
        layout.addRow(QLabel("   (0 = sin fecha de expiración)"))

        # Precio
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 10000)
        self.price_input.setValue(100.00)
        self.price_input.setPrefix("$ ")
        self.price_input.setDecimals(2)
        layout.addRow("💰 Precio:", self.price_input)

        # Activo
        self.active_check = QCheckBox("Paquete activo (disponible para venta)")
        self.active_check.setChecked(True)
        layout.addRow(self.active_check)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_package)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_package_data(self):
        """Carga los datos del paquete existente en el formulario."""
        session = get_session()
        try:
            pkg = session.get(Package, self.package_id)
            if pkg:
                self.name_input.setText(pkg.name)
                self.desc_input.setPlainText(pkg.description or "")
                self.classes_input.setValue(pkg.total_classes)
                self.validity_input.setValue(pkg.validity_days or 0)
                self.price_input.setValue(pkg.price)
                self.active_check.setChecked(pkg.is_active)
        finally:
            session.close()

    def save_package(self):
        """Guarda el paquete (crea o actualiza)."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "El nombre es obligatorio.")
            return

        total_classes = self.classes_input.value()
        validity_days = self.validity_input.value()
        if validity_days == 0:
            validity_days = None

        price = self.price_input.value()
        description = self.desc_input.toPlainText().strip() or None
        is_active = self.active_check.isChecked()

        try:
            if self.package_id:
                # Actualizar paquete existente
                success = update_package(
                    package_id=self.package_id,
                    name=name,
                    description=description,
                    total_classes=total_classes,
                    validity_days=validity_days,
                    price=price,
                    is_active=is_active,
                )
                if success:
                    QMessageBox.information(
                        self, "Éxito", "Paquete actualizado correctamente."
                    )
                    self.accept()
                else:
                    QMessageBox.critical(
                        self, "Error", "No se pudo actualizar el paquete."
                    )
            else:
                # Crear nuevo paquete
                pkg = add_package(
                    name=name,
                    description=description,
                    total_classes=total_classes,
                    validity_days=validity_days,
                    price=price,
                    is_active=is_active,
                )
                if pkg:
                    QMessageBox.information(
                        self, "Éxito", "Paquete creado correctamente."
                    )
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear el paquete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {str(e)}")
