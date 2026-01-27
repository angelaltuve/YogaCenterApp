from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import Any

class UserTableModel(QAbstractTableModel):
    def __init__(self, users=None):
        super().__init__()
        self.users = users or []
        self.headers = ["ID", "Nombre", "Email", "Teléfono", "Rol"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.users)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            user = self.users[index.row()]
            column = index.column()

            if column == 0:
                return str(user.id)
            elif column == 1:
                return user.name
            elif column == 2:
                return user.email
            elif column == 3:
                return user.phone or ""
            elif column == 4:
                return user.role.value

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None
