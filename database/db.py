"""
Database module for yoga centers.
"""
from datetime import datetime, timezone
from enum import Enum, unique
from pathlib import Path
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
    func
)

# <------------------- Database configuration ------------------>
DB_PATH = Path(__file__).parent.parent / "data" / "database.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# echo=False para no mostrar consultas SQL en consola
engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)

# <------------------- Enums ------------------>
@unique
class Role(str, Enum):
    """Represents the different roles of users."""
    ADMINISTRATOR = "ADMINISTRATOR"
    RECEPTIONIST = "RECEPTIONIST"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"

# <------------------- Models ------------------>
class UserCenter(SQLModel, table=True):
    """Represents a link between a user and a center."""
    user_id: int | None = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    center_id: int | None = Field(
        default=None, foreign_key="center.id", primary_key=True
    )

class Center(SQLModel, table=True):
    """Represents a Yoga Center."""
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    address: str = Field(max_length=200)
    phone: str = Field(max_length=20)

    # Relationships
    classes: list["YogaClass"] = Relationship(back_populates="center")
    users: list["User"] = Relationship(
        back_populates="centers", link_model=UserCenter
    )

class User(SQLModel, table=True):
    """Represents a user of the system."""
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(max_length=120, unique=True, index=True)
    phone: str | None = Field(max_length=20, default=None)
    password_hash: str = Field(max_length=250)
    role: Role = Field(default=Role.STUDENT)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_active: bool = Field(default=True)

    # Relationships
    classes_taught: list["YogaClass"] = Relationship(back_populates="teacher")
    reservations: list["Reserve"] = Relationship(back_populates="student")
    attendances: list["Attendance"] = Relationship(back_populates="student")
    payments: list["Payment"] = Relationship(back_populates="student")

    # Relationships with Center
    centers: list["Center"] = Relationship(
        back_populates="users", link_model=UserCenter
    )

class YogaClass(SQLModel, table=True):
    """Represents a class of the system."""
    id: int | None = Field(default=None, primary_key=True)
    scheduled_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    max_capacity: int = Field(gt=0)
    current_capacity: int = Field(default=0)
    price: float = Field(default=0.0)
    teacher_share_percentage: float = Field(default=70.0)

    teacher_id: int | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    center_id: int = Field(foreign_key="center.id")

    # Relationships
    teacher: User = Relationship(back_populates="classes_taught")
    center: Center = Relationship(back_populates="classes")

    reservations: list["Reserve"] = Relationship(back_populates="yogaclass")
    attendances: list["Attendance"] = Relationship(back_populates="yogaclass")
    payments: list["Payment"] = Relationship(back_populates="yogaclass")

class Reserve(SQLModel, table=True):
    """Represents a reservation of a class."""
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    reserved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    status: str = Field(default="active", max_length=20)  # active, cancelled, completed

    # Relationships
    student: User = Relationship(back_populates="reservations")
    yogaclass: YogaClass = Relationship(back_populates="reservations")

    payments: list["Payment"] = Relationship(back_populates="reserve")

class Attendance(SQLModel, table=True):
    """Represents an attendance of a class."""
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    attended_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    check_in_time: datetime | None = Field(default=None)
    status: str = Field(default="present", max_length=20)  # present, absent, late

    # Relationships
    student: User = Relationship(back_populates="attendances")
    yogaclass: YogaClass = Relationship(back_populates="attendances")

class Payment(SQLModel, table=True):
    """Represents a payment of a class."""
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    yogaclass_id: int = Field(foreign_key="yogaclass.id")
    reserve_id: int | None = Field(default=None, foreign_key="reserve.id")

    amount: float = Field(default=0.0)
    paid_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    payment_method: str = Field(default="cash", max_length=50)
    status: str = Field(default="paid", max_length=20)  # paid, pending, refunded

    # Relationships
    student: User = Relationship(back_populates="payments")
    yogaclass: YogaClass = Relationship(back_populates="payments")
    reserve: Reserve | None = Relationship(back_populates="payments")

# <------------------- Create tables ------------------>
def Create_Tables():
    """Create all tables in the database."""
    SQLModel.metadata.create_all(engine)

# <------------------- Utils ------------------>
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    """Check if a password matches the hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def authenticate(email: str, password: str) -> User | None:
    """Authenticates a user with the database."""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user and check_password(password, user.password_hash) and user.is_active:
            return user
    return None

# <------------------- Center CRUD ------------------>
def add_center(name: str, address: str, phone: str) -> Center:
    """Adds a center to the database."""
    center = Center(name=name, address=address, phone=phone)
    with Session(engine) as session:
        session.add(center)
        session.commit()
        session.refresh(center)
    return center

def get_all_centers() -> list[Center]:
    """Get all centers."""
    with Session(engine) as session:
        return session.exec(select(Center)).all()

def get_center_by_id(center_id: int) -> Center | None:
    """Get a center by ID."""
    with Session(engine) as session:
        return session.get(Center, center_id)

def update_center(center_id: int, **kwargs) -> bool:
    """Update a center."""
    with Session(engine) as session:
        center = session.get(Center, center_id)
        if center:
            for key, value in kwargs.items():
                if hasattr(center, key) and value is not None:
                    setattr(center, key, value)
            session.commit()
            session.refresh(center)
            return True
    return False

def delete_center(center_id: int) -> bool:
    """Delete a center."""
    with Session(engine) as session:
        center = session.get(Center, center_id)
        if center:
            session.delete(center)
            session.commit()
            return True
    return False

# <------------------- User CRUD ------------------>
def assign_user_to_center(user_id: int, center_id: int) -> UserCenter:
    """Assign a user to a center."""
    link = UserCenter(user_id=user_id, center_id=center_id)
    with Session(engine) as session:
        existing = session.exec(
            select(UserCenter).where(
                UserCenter.user_id == user_id,
                UserCenter.center_id == center_id,
            )
        ).first()
        if existing:
            return existing
        session.add(link)
        session.commit()
        session.refresh(link)
    return link

def get_user_centers(user_id: int) -> list[Center]:
    """Get all centers for a user."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return []
        session.refresh(user, ["centers"])
        return user.centers

def Add_User(
    name: str, email: str, phone: str | None, password: str, role: Role
) -> User | None:
    """Adds a user to the database."""
    # Check if user already exists
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

def create_student_user(name: str, email: str, phone: str | None, password: str) -> User | None:
    """Create a student user."""
    return Add_User(name, email, phone, password, Role.STUDENT)

def create_teacher_user(name: str, email: str, phone: str | None, password: str) -> User | None:
    """Create a teacher user."""
    return Add_User(name, email, phone, password, Role.TEACHER)

def user_exists(email: str) -> bool:
    """Check if a user exists by email."""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        return user is not None

def get_user_by_email(email: str) -> User | None:
    """Get a user by email."""
    with Session(engine) as session:
        return session.exec(select(User).where(User.email == email)).first()

def get_user_by_id(user_id: int) -> User | None:
    """Get a user by ID."""
    with Session(engine) as session:
        return session.get(User, user_id)

def get_all_users() -> list[User]:
    """Get all users."""
    with Session(engine) as session:
        return session.exec(select(User)).all()

def get_users_by_role(role: Role) -> list[User]:
    """Get users by role."""
    with Session(engine) as session:
        return session.exec(select(User).where(User.role == role)).all()

def update_user(user_id: int, **kwargs) -> bool:
    """Update a user."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            for key, value in kwargs.items():
                if key == 'password' and value:
                    user.password_hash = hash_password(value)
                elif hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            session.commit()
            session.refresh(user)
            return True
    return False

def delete_user(user_id: int) -> bool:
    """Delete a user from the database."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
    return False

def update_role(user_id: int, role: Role) -> bool:
    """Update user role."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            user.role = role
            session.commit()
            return True
    return False

# <------------------- Class CRUD ------------------>
def Add_YogaClass(
    scheduled_at: datetime,
    max_capacity: int,
    teacher_id: int,
    center_id: int,
    price: float = 0.0,
    teacher_share_percentage: float = 70.0
) -> YogaClass:
    """Adds a class to the database with price and teacher share."""
    yogaclass = YogaClass(
        scheduled_at=scheduled_at,
        max_capacity=max_capacity,
        teacher_id=teacher_id,
        center_id=center_id,
        price=price,
        teacher_share_percentage=teacher_share_percentage
    )
    with Session(engine) as session:
        session.add(yogaclass)
        session.commit()
        session.refresh(yogaclass)
    return yogaclass

def get_classes_by_date(date: datetime) -> list[YogaClass]:
    """Get classes by date."""
    with Session(engine) as session:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        return session.exec(
            select(YogaClass).where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at <= end_date
            )
        ).all()

def get_classes_by_teacher(teacher_id: int, date: datetime | None = None) -> list[YogaClass]:
    """Get classes by teacher."""
    with Session(engine) as session:
        query = select(YogaClass).where(YogaClass.teacher_id == teacher_id)

        if date:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(
                YogaClass.scheduled_at >= start_date,
                YogaClass.scheduled_at <= end_date
            )

        return session.exec(query).all()

def get_class_by_id(class_id: int) -> YogaClass | None:
    """Get a class by ID."""
    with Session(engine) as session:
        return session.get(YogaClass, class_id)

def update_class(class_id: int, **kwargs) -> bool:
    """Update a class."""
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, class_id)
        if yogaclass:
            for key, value in kwargs.items():
                if hasattr(yogaclass, key) and value is not None:
                    setattr(yogaclass, key, value)
            session.commit()
            session.refresh(yogaclass)
            return True
    return False

def delete_class(class_id: int) -> bool:
    """Delete a class."""
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, class_id)
        if yogaclass:
            session.delete(yogaclass)
            session.commit()
            return True
    return False

def get_available_classes_for_date(date: datetime, student_id: int = None) -> list[YogaClass]:
    """Get available classes for a specific date (not full and not already reserved by student)."""
    with Session(engine) as session:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        query = select(YogaClass).where(
            YogaClass.scheduled_at >= start_date,
            YogaClass.scheduled_at <= end_date,
            YogaClass.current_capacity < YogaClass.max_capacity
        )

        # Exclude classes already reserved by the student
        if student_id:
            reserved_classes = session.exec(
                select(Reserve.yogaclass_id).where(
                    Reserve.student_id == student_id,
                    Reserve.status == "active"
                )
            ).all()
            if reserved_classes:
                query = query.where(YogaClass.id.not_in(reserved_classes))

        return session.exec(query).all()

def calculate_teacher_earnings(payment_id: int) -> tuple[float, float]:
    """Calculate teacher and center earnings from a payment."""
    with Session(engine) as session:
        payment = session.get(Payment, payment_id)
        if not payment:
            return 0.0, 0.0

        yoga_class = session.get(YogaClass, payment.yogaclass_id)
        if not yoga_class:
            return 0.0, 0.0

        teacher_amount = payment.amount * (yoga_class.teacher_share_percentage / 100)
        center_amount = payment.amount - teacher_amount

        return teacher_amount, center_amount

def get_student_statistics(student_id: int) -> dict:
    """Get statistics for a student."""
    with Session(engine) as session:
        # Total classes attended
        attended = session.exec(
            select(func.count(Attendance.id)).where(
                Attendance.student_id == student_id,
                Attendance.status == "present"
            )
        ).first() or 0

        # Total classes reserved
        reserved = session.exec(
            select(func.count(Reserve.id)).where(
                Reserve.student_id == student_id,
                Reserve.status == "active"
            )
        ).first() or 0

        # Total payments
        payments = session.exec(
            select(func.sum(Payment.amount)).where(
                Payment.student_id == student_id,
                Payment.status == "paid"
            )
        ).first() or 0.0

        return {
            "classes_attended": attended,
            "classes_reserved": reserved,
            "total_paid": float(payments) if payments else 0.0,
            "attendance_rate": (attended / reserved * 100) if reserved > 0 else 0
        }

def get_teacher_statistics(teacher_id: int) -> dict:
    """Get statistics for a teacher."""
    with Session(engine) as session:
        # Total classes taught
        total_classes = session.exec(
            select(func.count(YogaClass.id)).where(
                YogaClass.teacher_id == teacher_id
            )
        ).first() or 0

        # Upcoming classes
        upcoming = session.exec(
            select(func.count(YogaClass.id)).where(
                YogaClass.teacher_id == teacher_id,
                YogaClass.scheduled_at >= datetime.now()
            )
        ).first() or 0

        # Total earnings
        earnings = session.exec(
            select(func.sum(Payment.amount * YogaClass.teacher_share_percentage / 100))
            .join(YogaClass, Payment.yogaclass_id == YogaClass.id)
            .where(YogaClass.teacher_id == teacher_id)
        ).first() or 0.0

        return {
            "total_classes": total_classes,
            "upcoming_classes": upcoming,
            "total_earnings": float(earnings) if earnings else 0.0
        }

# <------------------- Reservation CRUD ------------------>
def Add_Reservation(
    student_id: int, yogaclass_id: int
) -> Reserve | None:
    """Adds a reservation to the database."""
    # Check if class exists and has capacity
    with Session(engine) as session:
        yogaclass = session.get(YogaClass, yogaclass_id)
        if not yogaclass or yogaclass.current_capacity >= yogaclass.max_capacity:
            return None

        # Check if user already has reservation for this class
        existing = session.exec(
            select(Reserve).where(
                Reserve.student_id == student_id,
                Reserve.yogaclass_id == yogaclass_id,
                Reserve.status == "active"
            )
        ).first()

        if existing:
            return None

        reserve = Reserve(
            student_id=student_id,
            yogaclass_id=yogaclass_id,
        )

        # Update class capacity
        yogaclass.current_capacity += 1

        session.add(reserve)
        session.commit()
        session.refresh(reserve)
        return reserve

def get_reservations_by_student(student_id: int) -> list[Reserve]:
    """Get reservations by student."""
    with Session(engine) as session:
        return session.exec(
            select(Reserve).where(Reserve.student_id == student_id)
        ).all()

def get_reservations_by_class(class_id: int) -> list[Reserve]:
    """Get reservations by class."""
    with Session(engine) as session:
        return session.exec(
            select(Reserve).where(Reserve.yogaclass_id == class_id)
        ).all()

# <------------------- Attendance CRUD ------------------>
def Add_Attendance(
    student_id: int, yogaclass_id: int, check_in_time: datetime | None = None
) -> Attendance:
    """Adds an attendance to the database."""
    attendance = Attendance(
        student_id=student_id,
        yogaclass_id=yogaclass_id,
        check_in_time=check_in_time or datetime.now(timezone.utc)
    )
    with Session(engine) as session:
        session.add(attendance)
        session.commit()
        session.refresh(attendance)
    return attendance

def get_attendance_by_class(class_id: int) -> list[Attendance]:
    """Get attendance records for a class."""
    with Session(engine) as session:
        return session.exec(
            select(Attendance).where(Attendance.yogaclass_id == class_id)
        ).all()

def get_attendance_by_student(student_id: int, class_id: int) -> Attendance | None:
    """Get attendance record for a student in a class."""
    with Session(engine) as session:
        return session.exec(
            select(Attendance).where(
                Attendance.student_id == student_id,
                Attendance.yogaclass_id == class_id
            )
        ).first()

# <------------------- Payment CRUD ------------------>
def Add_Payment(
    student_id: int, yogaclass_id: int, amount: float, payment_method: str = "cash"
) -> Payment:
    """Adds a payment to the database."""
    payment = Payment(
        student_id=student_id,
        yogaclass_id=yogaclass_id,
        amount=amount,
        payment_method=payment_method
    )
    with Session(engine) as session:
        session.add(payment)
        session.commit()
        session.refresh(payment)
    return payment

# <------------------- Helper Functions ------------------>
def has_administrator() -> bool:
    """Check if there is at least one administrator."""
    with Session(engine) as session:
        admin = session.exec(
            select(User).where(User.role == Role.ADMINISTRATOR)
        ).first()
        return admin is not None

def has_centers() -> bool:
    """Check if there is at least one center."""
    with Session(engine) as session:
        center = session.exec(select(Center)).first()
        return center is not None

def get_centers_for_registration() -> list[Center]:
    """Get centers for registration."""
    return get_all_centers()

def assign_user_to_default_center(user_id: int) -> bool:
    """Assign user to first available center."""
    centers = get_all_centers()
    if centers:
        result = assign_user_to_center(user_id, centers[0].id)
        return result is not None
    return False

def search_users(search_term: str) -> list[User]:
    """Search users by name or email."""
    with Session(engine) as session:
        return session.exec(
            select(User).where(
                (User.name.contains(search_term)) |
                (User.email.contains(search_term))
            )
        ).all()

def get_session():
    """Retorna una nueva sesión de base de datos"""
    return Session(engine)

def get_payments_by_teacher(teacher_id: int, start_date: datetime = None, end_date: datetime = None) -> list[Payment]:
    """Get payments for classes taught by a teacher."""
    with Session(engine) as session:
        query = select(Payment).join(YogaClass).where(YogaClass.teacher_id == teacher_id)

        if start_date and end_date:
            query = query.where(
                Payment.paid_at >= start_date,
                Payment.paid_at <= end_date
            )

        return session.exec(query).all()

def get_total_earnings_by_teacher(teacher_id: int) -> float:
    """Get total earnings for a teacher."""
    with Session(engine) as session:
        result = session.exec(
            select(func.sum(Payment.amount * YogaClass.teacher_share_percentage / 100))
            .join(YogaClass, Payment.yogaclass_id == YogaClass.id)
            .where(YogaClass.teacher_id == teacher_id)
        ).first()
        return float(result) if result else 0.0

def get_all_payments(start_date: datetime = None, end_date: datetime = None) -> list[Payment]:
    """Get all payments with filters."""
    with Session(engine) as session:
        query = select(Payment)

        if start_date and end_date:
            query = query.where(
                Payment.paid_at >= start_date,
                Payment.paid_at <= end_date
            )

        return session.exec(query.order_by(Payment.paid_at.desc())).all()

def update_payment_status(payment_id: int, status: str) -> bool:
    """Update payment status."""
    with Session(engine) as session:
        payment = session.get(Payment, payment_id)
        if payment:
            payment.status = status
            session.commit()
            return True
    return False
