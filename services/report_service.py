from datetime import datetime, timedelta
from typing import List, Dict, Any
from database.db import get_session, select, Payment, YogaClass, User, Attendance, Center
from sqlalchemy import func

class ReportService:
    @staticmethod
    def generate_attendance_report(center_id: int = None, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Generate attendance report with filters."""
        session = get_session()
        try:
            query = select(Attendance)

            if center_id:
                query = query.join(YogaClass).where(YogaClass.center_id == center_id)

            if start_date and end_date:
                query = query.where(
                    Attendance.attended_at >= start_date,
                    Attendance.attended_at <= end_date
                )

            attendances = session.exec(query).all()

            # Process data
            total_attendance = len(attendances)
            unique_students = len(set(a.student_id for a in attendances))

            return {
                "total_attendance": total_attendance,
                "unique_students": unique_students,
                "attendances": attendances
            }
        finally:
            session.close()

    @staticmethod
    def generate_financial_report(start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Generate financial report with detailed breakdown."""
        session = get_session()
        try:
            query = select(Payment)

            if start_date and end_date:
                query = query.where(
                    Payment.paid_at >= start_date,
                    Payment.paid_at <= end_date
                )

            payments = session.exec(query).all()

            total_revenue = sum(p.amount for p in payments)

            # Group by payment method
            payment_methods = {}
            for p in payments:
                payment_methods[p.payment_method] = payment_methods.get(p.payment_method, 0) + p.amount

            # Group by status
            status_counts = {}
            for p in payments:
                status_counts[p.status] = status_counts.get(p.status, 0) + 1

            return {
                "total_revenue": total_revenue,
                "payment_methods": payment_methods,
                "status_counts": status_counts,
                "payments": payments
            }
        finally:
            session.close()

    @staticmethod
    def generate_class_report(center_id: int = None) -> Dict[str, Any]:
        """Generate class statistics report."""
        session = get_session()
        try:
            query = select(YogaClass)

            if center_id:
                query = query.where(YogaClass.center_id == center_id)

            classes = session.exec(query).all()

            total_classes = len(classes)
            total_capacity = sum(c.max_capacity for c in classes)
            total_booked = sum(c.current_capacity for c in classes)
            occupancy_rate = (total_booked / total_capacity * 100) if total_capacity > 0 else 0

            return {
                "total_classes": total_classes,
                "total_capacity": total_capacity,
                "total_booked": total_booked,
                "occupancy_rate": occupancy_rate,
                "classes": classes
            }
        finally:
            session.close()
