"""
Database module for yoga centers.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum, unique
from pathlib import Path
from typing import Optional, List, cast
import bcrypt
from sqlmodel import (
    Field,
    Relationship,
    Session,
    SQLModel,
    create_engine,
    select,
    update,
    delete,
    and_,
    func,
    desc,
    asc,
)
from sqlalchemy.orm import selectinload

# ------------------- Database configuration ------------------
DB_PATH = Path(__file__).parent.parent / "data" / "database.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)


# ------------------- Enums ------------------
@unique
class Role(str, Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    RECEPTIONIST = "RECEPTIONIST"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


# ------------------- Models ------------------
class UserCenter(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    center_id: int | None = Field(
        default=None, foreign_key="center.id", primary_key=True
    )


class Center(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    address: str = Field(max_length=200)
    phone: str = Field(max_length=20)

    classes: list["YogaClass"] = Relationship(back_populates="center")
    users: list["User"] = Relationship(back_populates="centers", link_model=UserCenter)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(max_length=120, unique=True, index=True)
    phone: str | None = Field(max_length=20, default=None)
    password_hash: str = Field(max_length=250)
    role: Role = Field(default=Role.STUDENT)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)

    classes_taught: list["YogaClass"] = Relationship(back_populates="teacher")
    reservations: list["Reserve"] = Relationship(back_populates="student")
    attendances: list["Attendance"] = Relationship(back_populates="student")
    payments: list["Payment"] = Relationship(back_populates="student")
    packages: list["StudentPackage"] = Relationship(back_populates="student")
    centers: list["Center"] = Relationship(
        back_populates="users", link_model=UserCenter
    )


class YogaClass(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    scheduled_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    max_capacity: int = Field(gt=0)
    current_capacity: int = Field(default=0)
    price: float = Field(default=0.0)
    teacher_share_percentage: float = Field(default=70.0)

    teacher_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    center_id: int = Field(foreign_key="center.id")

    teacher: User = Relationship(back_populates="classes_taught")
    center: Center = Relationship(back_populates="classes")
    reservations: list["Reserve"] = Relationship(back_populates="yogaclass")
    attendances: list["Attendance"] = Relationship(back_populates="yogaclass")
    payments: list["Payment"] = Relationship(back_populates="yogaclass")
    package_usages: list["PackageUsage"] = Relationship(back_populates="yogaclass")


class Reserve(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    reserved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    status: str = Field(default="active", max_length=20)

    student: User = Relationship(back_populates="reservations")
    yogaclass: YogaClass = Relationship(back_populates="reservations")


class Attendance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    attended_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    status: str = Field(default="present", max_length=20)

    student: User = Relationship(back_populates="attendances")
    yogaclass: YogaClass = Relationship(back_populates="attendances")


class Payment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int | None = Field(default=None, foreign_key="yogaclass.id")
    package_id: int | None = Field(default=None, foreign_key="package.id")
    amount: float = Field(default=0.0)
    paid_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    payment_method: str = Field(default="cash", max_length=50)
    status: str = Field(default="paid", max_length=20)  # paid, pending, refunded, cancelled
    reference: str | None = Field(default=None, max_length=100)

    student: User = Relationship(back_populates="payments")
    yogaclass: Optional["YogaClass"] = Relationship(back_populates="payments")
    package: Optional["Package"] = Relationship(back_populates="payments")


class Package(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    description: str | None = None
    total_classes: int = Field(gt=0)
    validity_days: int | None = Field(default=None)
    price: float = Field(gt=0)
    is_active: bool = Field(default=True)

    student_packages: list["StudentPackage"] = Relationship(back_populates="package")
    payments: list["Payment"] = Relationship(back_populates="package")


class StudentPackage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    package_id: int = Field(foreign_key="package.id")
    purchased_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    remaining_classes: int = Field(default=0)
    status: str = Field(default="active")   # active, used, cancelled, reserved

    student: User = Relationship(back_populates="packages")
    package: Package = Relationship(back_populates="student_packages")
    usages: list["PackageUsage"] = Relationship(back_populates="student_package")


class PackageUsage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_package_id: int = Field(foreign_key="studentpackage.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    student_package: StudentPackage = Relationship(back_populates="usages")
    yogaclass: YogaClass = Relationship(back_populates="package_usages")


# ------------------- Create tables ------------------
def create_tables():
    """Create all tables in the database."""
    SQLModel.metadata.create_all(engine)


# ------------------- Utils ------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def authenticate(email: str, password: str) -> User | None:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user and check_password(password, user.password_hash) and user.is_active:
            return user
    return None


# ------------------- Center CRUD ------------------
def add_center(name: str, address: str, phone: str) -> Center:
    center = Center(name=name, address=address, phone=phone)
    with Session(engine) as session:
        session.add(center)
        session.commit()
        session.refresh(center)
    return center


def get_all_centers() -> list[Center]:
    with Session(engine) as session:
        return list(session.exec(select(Center)).all())


def get_center_by_id(center_id: int) -> Center | None:
    with Session(engine) as session:
        return session.get(Center, center_id)


def update_center(center_id: int, **kwargs) -> bool:
    with Session(engine) as session:
        center = session.get(Center, center_id)
        if center:
            for key, value in kwargs.items():
                if hasattr(center, key) and value is not None:
                    setattr(center, key, value)
            session.commit()
            return True
    return False


def delete_center(center_id: int) -> bool:
    with Session(engine) as session:
        center = session.get(Center, center_id)
        if center:
            session.delete(center)
            session.commit()
            return True
    return False


# ------------------- User CRUD ------------------
def assign_user_to_center(user_id: int, center_id: int) -> UserCenter | None:
    with Session(engine) as session:
        existing = session.exec(
            select(UserCenter).where(
                UserCenter.user_id == user_id, UserCenter.center_id == center_id
            )
        ).first()
        if existing:
            return existing
        link = UserCenter(user_id=user_id, center_id=center_id)
        session.add(link)
        session.commit()
        session.refresh(link)
        return link


def get_user_centers(user_id: int) -> list[Center]:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return []
        session.refresh(user, ["centers"])
        return list(user.centers)


def get_user_center_ids(user_id: int) -> list[int]:
    """Retorna lista de IDs de centros a los que pertenece un usuario."""
    with Session(engine) as session:
        centers = session.exec(
            select(Center.id).join(UserCenter).where(UserCenter.user_id == user_id)
        ).all()
        return list(centers)


def add_user(
    name: str, email: str, phone: str | None, password: str, role: Role
) -> User | None:
    if user_exists(email):
        return None
    user = User(
        name=name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
    )
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def create_student_user(
    name: str, email: str, phone: str | None, password: str
) -> User | None:
    return add_user(name, email, phone, password, Role.STUDENT)


def create_teacher_user(
    name: str, email: str, phone: str | None, password: str
) -> User | None:
    return add_user(name, email, phone, password, Role.TEACHER)


def user_exists(email: str) -> bool:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        return user is not None


def get_user_by_email(email: str) -> User | None:
    with Session(engine) as session:
        return session.exec(select(User).where(User.email == email)).first()


def get_user_by_id(user_id: int) -> User | None:
    with Session(engine) as session:
        return session.get(User, user_id)


def get_all_users() -> list[User]:
    with Session(engine) as session:
        return list(session.exec(select(User)).all())


def get_users_by_role(role: Role) -> list[User]:
    with Session(engine) as session:
        return list(session.exec(select(User).where(User.role == role)).all())


def update_user(user_id: int, **kwargs) -> bool:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            for key, value in kwargs.items():
                if key == "password" and value:
                    user.password_hash = hash_password(value)
                elif hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            session.commit()
            return True
    return False


def delete_user(user_id: int) -> bool:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
    return False


def update_role(user_id: int, role: Role) -> bool:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            user.role = role
            session.commit()
            return True
    return False


def search_users(search_term: str) -> list[User]:
    with Session(engine) as session:
        return list(
            session.exec(
                select(User).where(
                    (User.name.contains(search_term)) | (User.email.contains(search_term))
                )
            ).all()
        )


# ------------------- Class CRUD ------------------
def add_yogaclass(
    scheduled_at: datetime,
    max_capacity: int,
    teacher_id: int,
    center_id: int,
    price: float = 0.0,
    teacher_share_percentage: float = 70.0,
) -> YogaClass:
    yogaclass = YogaClass(
        scheduled_at=scheduled_at,
        max_capacity=max_capacity,
        teacher_id=teacher_id,
        center_id=center_id,
        price=price,
        teacher_share_percentage=teacher_share_percentage,
    )
    with Session(engine) as session:
        session.add(yogaclass)
        session.commit()
        session.refresh(yogaclass)
    return yogaclass


def get_classes_by_date(date: datetime) -> list[YogaClass]:
    with Session(engine) as session:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return list(
            session.exec(
                select(YogaClass).where(
                    YogaClass.scheduled_at >= start_date, YogaClass.scheduled_at <= end_date
                )
            ).all()
        )


def get_classes_by_teacher(
    teacher_id: int, date: datetime | None = None
) -> list[YogaClass]:
    with Session(engine) as session:
        query = select(YogaClass).where(YogaClass.teacher_id == teacher_id)
        if date:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(
                YogaClass.scheduled_at >= start_date, YogaClass.scheduled_at <= end_date
            )
        return list(session.exec(query).all())


def get_class_by_id(class_id: int) -> YogaClass | None:
    with Session(engine) as session:
        return session.get(YogaClass, class_id)


def update_class(class_id: int, **kwargs) -> bool:
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, class_id)
        if yogaclass:
            for key, value in kwargs.items():
                if hasattr(yogaclass, key) and value is not None:
                    setattr(yogaclass, key, value)
            session.commit()
            return True
    return False


def delete_class(class_id: int) -> bool:
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, class_id)
        if yogaclass:
            session.delete(yogaclass)
            session.commit()
            return True
    return False


def get_available_classes_for_date(
    date: datetime, student_id: int | None = None
) -> list[YogaClass]:
    with Session(engine) as session:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = select(YogaClass).where(
            YogaClass.scheduled_at >= start_date,
            YogaClass.scheduled_at <= end_date,
            YogaClass.current_capacity < YogaClass.max_capacity,
        )
        if student_id:
            reserved_classes = session.exec(
                select(Reserve.yogaclass_id).where(
                    Reserve.student_id == student_id, Reserve.status == "active"
                )
            ).all()
            if reserved_classes:
                reserved_ids = [r for r in reserved_classes]
                query = query.where(YogaClass.id.not_in(reserved_ids))
        return list(session.exec(query).all())


def get_student_statistics(student_id: int) -> dict:
    with Session(engine) as session:
        attended = (
            session.exec(
                select(func.count(Attendance.id)).where(
                    Attendance.student_id == student_id, Attendance.status == "present"
                )
            ).first()
            or 0
        )
        reserved = (
            session.exec(
                select(func.count(Reserve.id)).where(
                    Reserve.student_id == student_id, Reserve.status == "active"
                )
            ).first()
            or 0
        )
        payments = (
            session.exec(
                select(func.sum(Payment.amount)).where(
                    Payment.student_id == student_id, Payment.status == "paid"
                )
            ).first()
            or 0.0
        )
        return {
            "classes_attended": attended,
            "classes_reserved": reserved,
            "total_paid": float(payments) if payments else 0.0,
            "attendance_rate": (attended / reserved * 100) if reserved > 0 else 0,
        }


def get_teacher_statistics(teacher_id: int) -> dict:
    with Session(engine) as session:
        total_classes = (
            session.exec(
                select(func.count(YogaClass.id)).where(
                    YogaClass.teacher_id == teacher_id
                )
            ).first()
            or 0
        )
        upcoming = (
            session.exec(
                select(func.count(YogaClass.id)).where(
                    YogaClass.teacher_id == teacher_id,
                    YogaClass.scheduled_at >= datetime.now(timezone.utc),
                )
            ).first()
            or 0
        )
        earnings = (
            session.exec(
                select(
                    func.sum(Payment.amount * YogaClass.teacher_share_percentage / 100)
                )
                .join(YogaClass, Payment.yogaclass_id == YogaClass.id)
                .where(YogaClass.teacher_id == teacher_id)
            ).first()
            or 0.0
        )
        return {
            "total_classes": total_classes,
            "upcoming_classes": upcoming,
            "total_earnings": float(earnings) if earnings else 0.0,
        }


# ------------------- Reservation CRUD ------------------
def add_reservation(student_id: int, yogaclass_id: int) -> Reserve | None:
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, yogaclass_id)
        if not yogaclass or yogaclass.current_capacity >= yogaclass.max_capacity:
            return None
        existing = session.exec(
            select(Reserve).where(
                Reserve.student_id == student_id,
                Reserve.yogaclass_id == yogaclass_id,
                Reserve.status == "active",
            )
        ).first()
        if existing:
            return None
        reserve = Reserve(student_id=student_id, yogaclass_id=yogaclass_id)
        yogaclass.current_capacity += 1
        session.add(reserve)
        session.commit()
        session.refresh(reserve)
        return reserve


def get_reservations_by_student(student_id: int) -> list[Reserve]:
    with Session(engine) as session:
        return list(session.exec(select(Reserve).where(Reserve.student_id == student_id)).all())


def get_reservations_by_class(class_id: int) -> list[Reserve]:
    with Session(engine) as session:
        return list(session.exec(select(Reserve).where(Reserve.yogaclass_id == class_id)).all())


# ------------------- Attendance CRUD ------------------
def add_attendance(
    student_id: int, yogaclass_id: int, attended_at: datetime | None = None
) -> Attendance:
    attendance = Attendance(
        student_id=student_id,
        yogaclass_id=yogaclass_id,
        attended_at=attended_at or datetime.now(timezone.utc),
    )
    with Session(engine) as session:
        session.add(attendance)
        session.commit()
        session.refresh(attendance)
    return attendance


def get_attendance_by_class(class_id: int) -> list[Attendance]:
    with Session(engine) as session:
        return list(session.exec(select(Attendance).where(Attendance.yogaclass_id == class_id)).all())


def get_attendance_by_student(student_id: int, class_id: int) -> Attendance | None:
    with Session(engine) as session:
        return session.exec(
            select(Attendance).where(
                Attendance.student_id == student_id, Attendance.yogaclass_id == class_id
            )
        ).first()


# ------------------- Payment CRUD ------------------
def add_payment(
    student_id: int,
    yogaclass_id: int | None = None,
    package_id: int | None = None,
    amount: float = 0.0,
    payment_method: str = "cash",
    reference: str | None = None,
) -> Payment | None:
    """Crea un pago"""
    if not yogaclass_id and not package_id:
        return None
    payment = Payment(
        student_id=student_id,
        yogaclass_id=yogaclass_id,
        package_id=package_id,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
    )
    with Session(engine) as session:
        session.add(payment)
        session.commit()
        session.refresh(payment)
    return payment


def get_payments_by_teacher(
    teacher_id: int, start_date: datetime | None = None, end_date: datetime | None = None
) -> list[Payment]:
    with Session(engine) as session:
        query = (
            select(Payment).join(YogaClass, YogaClass.id == Payment.yogaclass_id)
            .where(YogaClass.teacher_id == teacher_id)
        )
        if start_date and end_date:
            query = query.where(
                Payment.paid_at >= start_date, Payment.paid_at <= end_date
            )
        return list(session.exec(query).all())


def get_total_earnings_by_teacher(teacher_id: int) -> float:
    with Session(engine) as session:
        result = session.exec(
            select(func.sum(Payment.amount * YogaClass.teacher_share_percentage / 100))
            .join(YogaClass, YogaClass.id == Payment.yogaclass_id)
            .where(YogaClass.teacher_id == teacher_id)
        ).first()
        return float(result) if result else 0.0


def get_all_payments(
    start_date: datetime | None = None, end_date: datetime | None = None
) -> list[Payment]:
    with Session(engine) as session:
        query = select(Payment)
        if start_date and end_date:
            query = query.where(
                Payment.paid_at >= start_date, Payment.paid_at <= end_date
            )
        return list(session.exec(query.order_by(desc(Payment.paid_at))).all())


def update_payment_status(payment_id: int, status: str) -> bool:
    with Session(engine) as session:
        payment = session.get(Payment, payment_id)
        if payment:
            payment.status = status
            session.commit()
            return True
    return False


# ------------------- Package CRUD ------------------
def get_active_packages() -> list[Package]:
    """Retorna todos los paquetes activos."""
    with Session(engine) as session:
        return list(session.exec(select(Package).where(Package.is_active == True)).all())


def get_package_by_id(package_id: int) -> Package | None:
    """Obtiene un paquete por su ID."""
    with Session(engine) as session:
        return session.get(Package, package_id)


def purchase_package(
    student_id: int,
    package_id: int,
    payment_method: str = "cash",
    reference: str | None = None,
) -> StudentPackage | None:
    """
    Compra de un paquete por un estudiante.
    - Crea StudentPackage (status='active')
    - Crea un Payment asociado (sin clase)
    """
    with Session(engine) as session:
        package = session.get(Package, package_id)
        if not package or not package.is_active:
            return None

        expires_at = None
        if package.validity_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=package.validity_days)

        student_package = StudentPackage(
            student_id=student_id,
            package_id=package_id,
            expires_at=expires_at,
            remaining_classes=package.total_classes,
            status='active'
        )
        session.add(student_package)
        session.flush()
        if student_package.id is None:
            return None

        payment = Payment(
            student_id=student_id,
            package_id=package_id,
            amount=package.price,
            payment_method=payment_method,
            reference=reference,
            status='paid',
            paid_at=datetime.now(timezone.utc)
        )
        session.add(payment)

        session.commit()
        session.refresh(student_package)
        return student_package


def reserve_package(
    student_id: int,
    package_id: int,
    payment_method: str = "cash",
    reference: str | None = None,
) -> StudentPackage | None:
    """
    Reserva un paquete sin pago inmediato (pago pendiente).
    Crea StudentPackage con status='reserved' y Payment con status='pending'.
    """
    with Session(engine) as session:
        package = session.get(Package, package_id)
        if not package or not package.is_active:
            return None

        expires_at = None
        if package.validity_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=package.validity_days)

        student_package = StudentPackage(
            student_id=student_id,
            package_id=package_id,
            expires_at=expires_at,
            remaining_classes=package.total_classes,
            status='reserved'
        )
        session.add(student_package)
        session.flush()
        if student_package.id is None:
            return None

        payment = Payment(
            student_id=student_id,
            package_id=package_id,
            amount=package.price,
            payment_method=payment_method,
            reference=reference,
            status='pending',
            paid_at=None
        )
        session.add(payment)

        session.commit()
        session.refresh(student_package)
        return student_package


def confirm_package_payment(sp_id: int, payment_id: int) -> bool:
    """Cambia el estado de StudentPackage a 'active' y Payment a 'paid'."""
    with Session(engine) as session:
        sp = session.get(StudentPackage, sp_id)
        payment = session.get(Payment, payment_id)
        if not sp or not payment or sp.status != 'reserved' or payment.status != 'pending':
            return False
        sp.status = 'active'
        payment.status = 'paid'
        payment.paid_at = datetime.now(timezone.utc)
        session.commit()
        return True


def cancel_reserved_package(sp_id: int) -> bool:
    """Cancela un paquete reservado (no pagado)."""
    with Session(engine) as session:
        sp = session.get(StudentPackage, sp_id)
        if not sp or sp.status != 'reserved':
            return False
        # Buscar el pago pendiente asociado
        payment = session.exec(
            select(Payment).where(
                Payment.package_id == sp.package_id,
                Payment.student_id == sp.student_id,
                Payment.status == "pending"
            )
        ).first()
        if payment:
            payment.status = 'cancelled'
        sp.status = 'cancelled'
        session.commit()
        return True


def get_student_packages(student_id: int) -> list[StudentPackage]:
    """Retorna todos los paquetes comprados por un estudiante, con la relación 'package' cargada."""
    with Session(engine) as session:
        return list(
            session.exec(
                select(StudentPackage)
                .where(StudentPackage.student_id == student_id)
                .options(selectinload(StudentPackage.package))
                .order_by(desc(StudentPackage.purchased_at))
            ).all()
        )


def get_active_student_packages(student_id: int) -> list[StudentPackage]:
    """Retorna los paquetes activos del estudiante (status='active' y con créditos)."""
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        return list(
            session.exec(
                select(StudentPackage)
                .where(
                    StudentPackage.student_id == student_id,
                    StudentPackage.status == 'active',
                    StudentPackage.remaining_classes > 0,
                    (StudentPackage.expires_at == None) | (StudentPackage.expires_at > now)
                )
                .options(selectinload(StudentPackage.package))
                .order_by(asc(StudentPackage.expires_at))
            ).all()
        )


def cancel_student_package(sp_id: int) -> bool:
    """Cancela un paquete activo."""
    with Session(engine) as session:
        sp = session.get(StudentPackage, sp_id)
        if sp and sp.status == 'active':
            sp.status = 'cancelled'
            session.commit()
            return True
    return False


def reserve_class_with_package(student_id: int, yogaclass_id: int) -> tuple[bool, str]:
    """
    Reserva una clase usando un paquete activo.
    """
    with Session(engine) as session:
        yoga_class = session.get(YogaClass, yogaclass_id)
        if not yoga_class:
            return False, "Clase no encontrada"
        if yoga_class.current_capacity >= yoga_class.max_capacity:
            return False, "Clase llena"

        existing = session.exec(
            select(Reserve).where(
                Reserve.student_id == student_id,
                Reserve.yogaclass_id == yogaclass_id,
                Reserve.status == "active"
            )
        ).first()
        if existing:
            return False, "Ya tienes una reserva activa para esta clase"

        now = datetime.now(timezone.utc)
        sp = session.exec(
            select(StudentPackage)
            .where(
                StudentPackage.student_id == student_id,
                StudentPackage.status == 'active',
                StudentPackage.remaining_classes > 0,
                (StudentPackage.expires_at == None) | (StudentPackage.expires_at > now)
            )
            .order_by(asc(StudentPackage.expires_at))
        ).first()

        if not sp:
            return False, "No tienes un paquete activo con clases disponibles"

        reserve = Reserve(student_id=student_id, yogaclass_id=yogaclass_id)
        yoga_class.current_capacity += 1
        session.add(reserve)

        if sp.id is None:
            return False, "Error interno: paquete sin ID"
        usage = PackageUsage(
            student_package_id=sp.id,
            yogaclass_id=yogaclass_id
        )
        sp.remaining_classes -= 1
        if sp.remaining_classes == 0:
            sp.status = 'used'
        session.add(usage)

        session.commit()
        session.refresh(reserve)
        return True, "Reserva exitosa usando paquete"


# ------------------- Helper Functions ------------------
def get_student_enrolled_classes(
    student_id: int, date: datetime | None = None
) -> list[YogaClass]:
    """Retorna las clases donde el estudiante tiene reserva activa."""
    with Session(engine) as session:
        query = (
            select(YogaClass)
            .join(Reserve, Reserve.yogaclass_id == YogaClass.id)
            .where(Reserve.student_id == student_id, Reserve.status == "active")
        )
        if date:
            start = datetime.combine(date.date(), datetime.min.time())
            end = datetime.combine(date.date(), datetime.max.time())
            query = query.where(
                YogaClass.scheduled_at >= start, YogaClass.scheduled_at <= end
            )
        return list(session.exec(query.order_by(asc(YogaClass.scheduled_at))).all())


def has_usable_package(student_id: int) -> bool:
    """Verifica si el estudiante tiene al menos un paquete activo con créditos."""
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        sp = session.exec(
            select(StudentPackage)
            .where(
                StudentPackage.student_id == student_id,
                StudentPackage.status == 'active',
                StudentPackage.remaining_classes > 0,
                (StudentPackage.expires_at == None) | (StudentPackage.expires_at > now)
            )
        ).first()
        return sp is not None


def has_administrator() -> bool:
    with Session(engine) as session:
        admin = session.exec(
            select(User).where(User.role == Role.ADMINISTRATOR)
        ).first()
        return admin is not None


def has_centers() -> bool:
    with Session(engine) as session:
        center = session.exec(select(Center)).first()
        return center is not None


def get_session():
    return Session(engine)


# ------------------- Package CRUD (adicional) ------------------
def add_package(name: str, description: str | None, total_classes: int,
                validity_days: int | None, price: float, is_active: bool = True) -> Package | None:
    """Crea un nuevo paquete."""
    with Session(engine) as session:
        package = Package(
            name=name,
            description=description,
            total_classes=total_classes,
            validity_days=validity_days,
            price=price,
            is_active=is_active
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return package


def update_package(package_id: int, **kwargs) -> bool:
    """Actualiza un paquete existente."""
    with Session(engine) as session:
        package = session.get(Package, package_id)
        if not package:
            return False
        for key, value in kwargs.items():
            if hasattr(package, key) and value is not None:
                setattr(package, key, value)
        session.commit()
        return True


def delete_package(package_id: int) -> bool:
    """Elimina un paquete """
    with Session(engine) as session:
        package = session.get(Package, package_id)
        if package:
            if package.student_packages:
                return False
            session.delete(package)
            session.commit()
            return True
    return False


def get_unpaid_reservations(student_id: int) -> list[Reserve]:
    """Retorna las reservas activas que no tienen un pago asociado."""
    with Session(engine) as session:
        unpaid = session.exec(
            select(Reserve)
            .where(
                Reserve.student_id == student_id,
                Reserve.status == "active",
                ~Reserve.id.in_(
                    select(Payment.yogaclass_id)
                    .where(Payment.student_id == student_id)
                    .where(Payment.yogaclass_id.isnot(None))
                )
            )
        ).all()
        return list(unpaid)


def get_reservation_with_package(reserve_id: int) -> PackageUsage | None:
    """Retorna el uso de paquete asociado a una reserva, si existe."""
    with Session(engine) as session:
        return session.exec(
            select(PackageUsage).where(PackageUsage.yogaclass_id == reserve_id)
        ).first()


def get_package_usage_by_reserve(reserve_id: int) -> PackageUsage | None:
    with Session(engine) as session:
        reserve = session.get(Reserve, reserve_id)
        if not reserve:
            return None
        return session.exec(
            select(PackageUsage).where(
                PackageUsage.yogaclass_id == reserve.yogaclass_id,
                PackageUsage.student_package.has(student_id=reserve.student_id)
            )
        ).first()


def cancel_reservation(reserve_id: int) -> tuple[bool, str]:
    """
    Cancela una reserva activa.
    """
    with Session(engine) as session:
        reserve = session.get(Reserve, reserve_id)
        if not reserve:
            return False, "Reserva no encontrada"
        if reserve.status != "active":
            return False, "La reserva no está activa"

        yoga_class = session.get(YogaClass, reserve.yogaclass_id)
        if not yoga_class:
            return False, "Clase no encontrada"

        usage = session.exec(
            select(PackageUsage).where(
                PackageUsage.yogaclass_id == reserve.yogaclass_id,
                PackageUsage.student_package.has(student_id=reserve.student_id)
            )
        ).first()

        if usage:
            sp = usage.student_package
            sp.remaining_classes += 1
            if sp.status == "used":
                sp.status = "active"
            session.delete(usage)

        yoga_class.current_capacity -= 1

        reserve.status = "cancelled"
        session.commit()
        return True, "Reserva cancelada correctamente"
