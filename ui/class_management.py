from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QDoubleSpinBox
)

from database.db import Center, Role, User, YogaClass, get_session, select
from services.services import ClassService


class ClassManagementWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.current_user = user
        self.class_service = ClassService()
        self.init_ui()
        self.load_classes()

    def init_ui(self):
        layout = QVBoxLayout()

        # Barra de herramientas
        toolbar = QHBoxLayout()

        if self.current_user.role in [Role.ADMINISTRATOR, Role.RECEPTIONIST]:
            add_btn = QPushButton("➕ Nueva Clase")
            add_btn.clicked.connect(self.show_add_class_dialog)
            toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_classes)

        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()

        # Tabla de clases
        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(7)
        self.classes_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Fecha/Hora",
                "Profesor",
                "Centro",
                "Capacidad",
                "Disponibles",
                "Acciones",
            ]
        )
        self.classes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addLayout(toolbar)
        layout.addWidget(self.classes_table)
        self.setLayout(layout)

    def load_classes(self):
        session = get_session()
        try:
            classes = session.exec(select(YogaClass)).all()
            self.display_classes(classes)
        finally:
            session.close()

    def display_classes(self, classes):
        self.classes_table.setRowCount(len(classes))

        session = get_session()
        try:
            for row, yoga_class in enumerate(classes):
                self.classes_table.setItem(
                    row, 0, QTableWidgetItem(str(yoga_class.id))
                )
                self.classes_table.setItem(
                    row, 1, QTableWidgetItem(yoga_class.scheduled_at.strftime("%Y-%m-%d %H:%M"))
                )

                # Obtener profesor
                teacher = session.get(User, yoga_class.teacher_id)
                teacher_name = teacher.name if teacher else "No asignado"
                self.classes_table.setItem(
                    row, 2, QTableWidgetItem(teacher_name)
                )

                # Obtener centro
                center = session.get(Center, yoga_class.center_id)
                center_name = center.name if center else "Desconocido"
                self.classes_table.setItem(
                    row, 3, QTableWidgetItem(center_name)
                )

                self.classes_table.setItem(
                    row, 4, QTableWidgetItem(str(yoga_class.max_capacity))
                )

                # Calcular disponibilidad
                available = (
                    yoga_class.max_capacity - yoga_class.current_capacity
                )
                self.classes_table.setItem(
                    row, 5, QTableWidgetItem(str(available))
                )

                # Botones de acción
                if self.current_user.role in [
                    Role.ADMINISTRATOR,
                    Role.RECEPTIONIST,
                ]:
                    action_widget = QWidget()
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)

                    edit_btn = QPushButton("✏️")
                    edit_btn.setFixedSize(30, 30)
                    edit_btn.clicked.connect(
                        lambda checked, class_id=yoga_class.id: self.edit_class(
                            class_id
                        )
                    )

                    delete_btn = QPushButton("🗑️")
                    delete_btn.setFixedSize(30, 30)
                    delete_btn.clicked.connect(
                        lambda checked, class_id=yoga_class.id: self.delete_class(
                            class_id
                        )
                    )

                    action_layout.addWidget(edit_btn)
                    action_layout.addWidget(delete_btn)
                    action_widget.setLayout(action_layout)
                    self.classes_table.setCellWidget(row, 6, action_widget)
                else:
                    self.classes_table.setItem(row, 6, QTableWidgetItem("-"))
        finally:
            session.close()

    def show_add_class_dialog(self):
        dialog = AddClassDialog(self.current_user, self)
        if dialog.exec():
            self.load_classes()

    def edit_class(self, class_id):
        dialog = EditClassDialog(class_id, self.current_user, self)
        if dialog.exec():
            self.load_classes()

    def delete_class(self, class_id):
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro que desea eliminar esta clase?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from database.db import delete_class as db_delete_class
                if db_delete_class(class_id):
                    QMessageBox.information(self, "Éxito", "Clase eliminada correctamente")
                    self.load_classes()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo eliminar la clase")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la clase: {str(e)}")


class AddClassDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Nueva Clase")
        self.setFixedSize(400, 350)
        self.init_ui()
        self.load_teachers_and_centers()

    def init_ui(self):
        layout = QFormLayout()

        self.datetime_input = QDateTimeEdit()
        self.datetime_input.setDateTime(QDateTime.currentDateTime())
        self.datetime_input.setCalendarPopup(True)

        self.capacity_input = QSpinBox()
        self.capacity_input.setMinimum(1)
        self.capacity_input.setMaximum(100)
        self.capacity_input.setValue(20)

        self.teacher_combo = QComboBox()
        self.center_combo = QComboBox()

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 1000)
        self.price_input.setValue(20.00)
        self.price_input.setPrefix("$ ")
        self.price_input.setDecimals(2)

        self.teacher_share_input = QDoubleSpinBox()
        self.teacher_share_input.setRange(0, 100)
        self.teacher_share_input.setValue(70.0)
        self.teacher_share_input.setSuffix(" %")
        self.teacher_share_input.setDecimals(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.create_class)
        buttons.rejected.connect(self.reject)

        layout.addRow("Fecha y Hora:", self.datetime_input)
        layout.addRow("Capacidad:", self.capacity_input)
        layout.addRow("Profesor:", self.teacher_combo)
        layout.addRow("Centro:", self.center_combo)
        layout.addRow("Precio:", self.price_input)
        layout.addRow("Porcentaje Profesor:", self.teacher_share_input)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_teachers_and_centers(self):
        session = get_session()
        try:
            # Cargar profesores
            teachers = session.exec(
                select(User).where(User.role == Role.TEACHER)
            ).all()
            for teacher in teachers:
                self.teacher_combo.addItem(teacher.name, teacher.id)

            # Cargar centros
            centers = session.exec(select(Center)).all()
            for center in centers:
                self.center_combo.addItem(center.name, center.id)

            # Mostrar advertencia si no hay centros
            if not centers:
                QMessageBox.warning(self, "Advertencia",
                                  "No hay centros creados. Por favor, cree un centro primero desde la pestaña 'Centros'.")
                self.reject()
                return

            if not teachers:
                QMessageBox.warning(self, "Advertencia",
                                  "No hay profesores disponibles. Por favor, cree un profesor primero.")
                self.reject()
                return

        finally:
            session.close()

    def create_class(self):
        scheduled_at = self.datetime_input.dateTime().toPyDateTime()
        max_capacity = self.capacity_input.value()
        teacher_id = self.teacher_combo.currentData()
        center_id = self.center_combo.currentData()
        price = self.price_input.value()
        teacher_share = self.teacher_share_input.value()

        if not teacher_id or not center_id:
            QMessageBox.warning(self, "Error", "Seleccione profesor y centro")
            return

        try:
            from database.db import Add_YogaClass
            yoga_class = Add_YogaClass(
                scheduled_at=scheduled_at,
                max_capacity=max_capacity,
                teacher_id=teacher_id,
                center_id=center_id,
                price=price,
                teacher_share_percentage=teacher_share
            )
            if yoga_class:
                QMessageBox.information(
                    self, "Éxito", "Clase creada correctamente"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, "Error", "No se pudo crear la clase"
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo crear la clase: {str(e)}"
            )


class EditClassDialog(QDialog):
    def __init__(self, class_id, user, parent=None):
        super().__init__(parent)
        self.class_id = class_id
        self.user = user
        self.setWindowTitle("Editar Clase")
        self.setFixedSize(400, 350)
        self.init_ui()
        self.load_class_data()

    def init_ui(self):
        layout = QFormLayout()

        self.datetime_input = QDateTimeEdit()
        self.datetime_input.setCalendarPopup(True)

        self.capacity_input = QSpinBox()
        self.capacity_input.setMinimum(1)
        self.capacity_input.setMaximum(100)

        self.teacher_combo = QComboBox()
        self.center_combo = QComboBox()

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 1000)
        self.price_input.setPrefix("$ ")
        self.price_input.setDecimals(2)

        self.teacher_share_input = QDoubleSpinBox()
        self.teacher_share_input.setRange(0, 100)
        self.teacher_share_input.setSuffix(" %")
        self.teacher_share_input.setDecimals(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_changes)
        buttons.rejected.connect(self.reject)

        layout.addRow("Fecha y Hora:", self.datetime_input)
        layout.addRow("Capacidad:", self.capacity_input)
        layout.addRow("Profesor:", self.teacher_combo)
        layout.addRow("Centro:", self.center_combo)
        layout.addRow("Precio:", self.price_input)
        layout.addRow("Porcentaje Profesor:", self.teacher_share_input)
        layout.addRow(buttons)

        self.setLayout(layout)

    def load_class_data(self):
        session = get_session()
        try:
            yoga_class = session.get(YogaClass, self.class_id)
            if not yoga_class:
                QMessageBox.warning(self, "Error", "Clase no encontrada")
                self.reject()
                return

            # Establecer valores actuales
            self.datetime_input.setDateTime(
                QDateTime.fromString(
                    str(yoga_class.scheduled_at), "yyyy-MM-dd HH:mm:ss"
                )
            )
            self.capacity_input.setValue(yoga_class.max_capacity)

            # Cargar profesores
            teachers = session.exec(
                select(User).where(
                    (User.role == Role.TEACHER) & (User.is_active == True)
                )
            ).all()

            current_teacher_index = 0
            for idx, teacher in enumerate(teachers):
                self.teacher_combo.addItem(teacher.name, teacher.id)
                if teacher.id == yoga_class.teacher_id:
                    current_teacher_index = idx

            self.teacher_combo.setCurrentIndex(current_teacher_index)

            # Cargar centros
            centers = session.exec(select(Center)).all()

            current_center_index = 0
            for idx, center in enumerate(centers):
                self.center_combo.addItem(center.name, center.id)
                if center.id == yoga_class.center_id:
                    current_center_index = idx

            self.price_input.setValue(yoga_class.price)
            self.teacher_share_input.setValue(yoga_class.teacher_share_percentage)
            self.center_combo.setCurrentIndex(current_center_index)

        finally:
            session.close()

    def save_changes(self):
        scheduled_at = self.datetime_input.dateTime().toPyDateTime()
        max_capacity = self.capacity_input.value()
        teacher_id = self.teacher_combo.currentData()
        center_id = self.center_combo.currentData()
        price = self.price_input.value()
        teacher_share = self.teacher_share_input.value()

        # Validaciones
        if scheduled_at <= QDateTime.currentDateTime().toPyDateTime():
            QMessageBox.warning(self, "Error", "La fecha debe ser futura")
            return

        if not teacher_id:
            QMessageBox.warning(self, "Error", "Seleccione un profesor")
            return

        if not center_id:
            QMessageBox.warning(self, "Error", "Seleccione un centro")
            return

        try:
            from database.db import update_class
            success = update_class(
                class_id=self.class_id,
                scheduled_at=scheduled_at,
                max_capacity=max_capacity,
                teacher_id=teacher_id,
                center_id=center_id,
                price=price,
                teacher_share_percentage=teacher_share
            )

            if success:
                QMessageBox.information(
                    self, "Éxito", "Clase actualizada correctamente"
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar la clase")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"No se pudo actualizar la clase: {str(e)}"
            )
