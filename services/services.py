"""
Application services
"""

from datetime import datetime, timedelta
from typing import List, Optional
from database.db import (
    Session, User, YogaClass, Center, Reserve, Attendance, Payment,
    Role, select, get_user_centers, Add_User, Add_YogaClass,
    Add_Reservation, Add_Attendance, Add_Payment, assign_user_to_center, get_session
)

class UserService:
    @staticmethod
    def create_user(name: str, email: str, phone: str,
                   password: str, role: Role, center_ids: List[int]) -> Optional[User]:
        """Crear un nuevo usuario y asignarlo a centros"""
        user = Add_User(name, email, phone, password, role)

        if user:
            for center_id in center_ids:
                assign_user_to_center(user.id, center_id)

        return user

    @staticmethod
    def get_users_by_role(role: Role) -> List[User]:
        """Obtener usuarios por rol"""
        with Session() as session:
            users = session.exec(
                select(User).where(User.role == role)
            ).all()
            return users

    @staticmethod
    def get_all_users() -> List[User]:
        """Obtener todos los usuarios"""
        with Session() as session:
            users = session.exec(select(User)).all()
            return users

class ClassService:
    @staticmethod
    def create_class(scheduled_at: datetime, max_capacity: int,
                    teacher_id: int, center_id: int) -> YogaClass:
        """Crear una nueva clase"""
        return Add_YogaClass(scheduled_at, max_capacity, teacher_id, center_id)

    @staticmethod
    def get_classes_by_teacher(teacher_id: int) -> List[YogaClass]:
        """Obtener clases asignadas a un profesor"""
        with Session() as session:
            classes = session.exec(
                select(YogaClass).where(YogaClass.teacher_id == teacher_id)
            ).all()
            return classes

    @staticmethod
    def get_upcoming_classes(days: int = 7) -> List[YogaClass]:
        """Obtener clases próximas"""
        with Session() as session:
            today = datetime.now().date()
            end_date = today + timedelta(days=days)

            classes = session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at >= today,
                    YogaClass.scheduled_at <= end_date
                )
            ).all()
            return classes

class PaymentService:
    @staticmethod
    def process_payment(student_id: int, class_id: int,
                       amount: float, method: str = "cash") -> Payment:
        """Procesar un pago"""
        # Aquí integrarías con la pasarela de pagos real
        payment = Add_Payment(
            student_id=student_id,
            yogaclass_id=class_id,
            paid_at=datetime.now(),
            payment_method=method
        )
        return payment

class ReportService:
    @staticmethod
    def generate_attendance_report(start_date: datetime,
                                  end_date: datetime) -> dict:
        """Generar reporte de asistencia"""
        with Session() as session:
            # Implementar lógica de reporte
            pass

    @staticmethod
    def generate_financial_report(start_date: datetime,
                                 end_date: datetime) -> dict:
        """Generar reporte financiero"""
        with Session() as session:
            # Implementar lógica de reporte
            pass
