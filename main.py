"""main"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from database.db import (
    Add_User,
    Create_Tables,
    Role,
    has_administrator,
    has_centers,
)
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


class YogaManagerApp(QApplication):
    def __init__(self, argv: list[str]):
        super().__init__(argv)

        # Crear tablas si no existen
        Create_Tables()

        # Crear administrador por defecto si no existe
        self.create_default_admin()

        # Verificar que hay centros
        self.check_centers()

        # Configurar aplicación
        self.setApplicationName("Sistema de Gestión de Centros de Yoga")
        self.setOrganizationName("YogaCenters")

        # Cargar estilos
        self.load_styles()

        # Mostrar login
        self.login_dialog = LoginDialog()
        if self.login_dialog.exec():
            self.user = self.login_dialog.user
            self.main_window = MainWindow(self.user)
            self.main_window.show()
        else:
            sys.exit(0)

    def create_default_admin(self):
        """Crear administrador por defecto si no existe"""
        if not has_administrator():
            try:
                _ = Add_User(
                    name="Administrador",
                    email="admin@yogacenter.com",
                    phone="123456789",
                    password="admin123",
                    role=Role.ADMINISTRATOR,
                )
                print("Administrador creado: admin@yogacenter.com / admin123")

                # Crear un centro por defecto
                from database.db import add_center
                default_center = add_center(
                    name="Centro Principal",
                    address="Calle Principal 123",
                    phone="123-456-7890"
                )
                print(f"Centro por defecto creado: {default_center.name}")

            except Exception as e:
                print(f"No se pudo crear administrador o centro: {e}")
    def check_centers(self):
        """Verificar que hay al menos un centro creado"""
        if not has_centers():
            print(
                "⚠️  No hay centros creados. Crea al menos un centro desde la interfaz de administración."
            )

    def load_styles(self):
        """load_styles"""
        style_path = Path(__file__).parent / "styles" / "styles.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            print(f"Archivo de estilos no encontrado: {style_path}")


def main():
    app = YogaManagerApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
