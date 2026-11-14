
# models.py
# Defines all database tables, columns and relationships.

from datetime import date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Date,
    Time
)

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


# ==========================================
# 1. USER TABLE
# Admin, Examiner and Student accounts
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    fullname = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default="Student")
    isactive = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False
    )

    examiner_profile = relationship(
        "ExaminerProfile",
        back_populates="user",
        uselist=False
    )


# ==========================================
# 2. STUDENT PROFILE TABLE
# Additional student information
# ==========================================

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    student_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     unique=True, nullable=False)

    student_number = Column(String(30), unique=True)
    roll_number = Column(String(30), unique=True)
    department = Column(String(50))
    programme = Column(String(50))
    semester = Column(Integer)
    year_of_study = Column(Integer)
    contact_details = Column(String(30))


    user = relationship(
        "User",
        back_populates="student_profile"
    )

    bookings = relationship(
        "Booking",
        back_populates="student"
    )

    evaluations = relationship(
        "Evaluation",
        back_populates="student"
    )


# ==========================================
# 3. EXAMINER PROFILE TABLE
# Additional examiner information
# ==========================================

class ExaminerProfile(Base):
    __tablename__ = "examiner_profiles"

    examiner_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     unique=True, nullable=False)

    contact_details = Column(String(30))
    department = Column(String(50))
    designation = Column(String(50))
    employee_code = Column(String(30), unique=True)
    status = Column(String(20), default="active")

    user = relationship(
        "User",
        back_populates="examiner_profile"
    )

    examinations = relationship(
        "Examination",
        back_populates="examiner"
    )

    slots = relationship(
        "ExaminationSlot",
        back_populates="examiner"
    )

    evaluations = relationship(
        "Evaluation",
        back_populates="examiner"
    )


# ==========================================
# 4. COURSE TABLE
# ==========================================

class Course(Base):
    __tablename__ = "courses"

    course_id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(30), unique=True, nullable=False)
    course_name = Column(String(50), nullable=False)
    description = Column(String(255))
    status = Column(String(20), default="active")

    examinations = relationship(
        "Examination",
        back_populates="course"
    )


# ==========================================
# 5. EXAMINATION TABLE
# ==========================================

class Examination(Base):
    __tablename__ = "examinations"

    exam_id = Column(Integer, primary_key=True, index=True)

    course_id = Column(Integer, ForeignKey("courses.course_id"),
                       nullable=False)

    examiner_id = Column(Integer,
                         ForeignKey("examiner_profiles.examiner_id"),
                         nullable=False)

    examination_name = Column(String(50), nullable=False)
    examination_type = Column(String(50), nullable=False)
    duration = Column(Float, nullable=False)
    maximum_marks = Column(Integer, nullable=False)

    slot_creation_start_date = Column(DateTime(timezone=True))
    slot_creation_end_date = Column(DateTime(timezone=True))

    slot_booking_start_date = Column(DateTime(timezone=True))
    slot_booking_end_date = Column(DateTime(timezone=True))

    status = Column(String(30), default="draft")

    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    course = relationship(
        "Course",
        back_populates="examinations"
    )

    examiner = relationship(
        "ExaminerProfile",
        back_populates="examinations"
    )

    rubrics = relationship(
        "ExaminationRubric",
        back_populates="examination"
    )

    slots = relationship(
        "ExaminationSlot",
        back_populates="examination"
    )


# ==========================================
# 6. EXAMINATION RUBRIC TABLE
# Evaluation criteria for examinations
# ==========================================

class ExaminationRubric(Base):
    __tablename__ = "examination_rubrics"

    rubric_id = Column(Integer, primary_key=True, index=True)

    examination_id = Column(Integer,
                            ForeignKey("examinations.exam_id"),
                            nullable=False)

    criterion_name = Column(String(100), nullable=False)
    maximum_marks = Column(Float, nullable=False)
    weightage = Column(Float)
    description = Column(String(255))

    examination = relationship(
        "Examination",
        back_populates="rubrics"
    )


# ==========================================
# 7. EXAMINATION SLOT TABLE
# Examiner-created available time slots
# ==========================================

class ExaminationSlot(Base):
    __tablename__ = "examination_slots"

    slot_id = Column(Integer, primary_key=True, index=True)

    examination_id = Column(Integer,
                            ForeignKey("examinations.exam_id"),
                            nullable=False)

    examiner_id = Column(Integer,
                         ForeignKey("examiner_profiles.examiner_id"),
                         nullable=False)

    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    maximum_student_capacity = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)

    status = Column(String(20), default="available")
    meeting_link = Column(String(255), nullable=True)

    examination = relationship(
        "Examination",
        back_populates="slots"
    )

    examiner = relationship(
        "ExaminerProfile",
        back_populates="slots"
    )

    bookings = relationship(
        "Booking",
        back_populates="slot"
    )


# ==========================================
# 8. BOOKING TABLE
# Student examination slot bookings
# ==========================================

class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer,
                        ForeignKey("student_profiles.student_id"),
                        nullable=False)

    slot_id = Column(Integer,
                     ForeignKey("examination_slots.slot_id"),
                     nullable=False)

    booking_date = Column(Date, default=date.today)
    status = Column(String(20), default="booked")

    student = relationship(
        "StudentProfile",
        back_populates="bookings"
    )

    slot = relationship(
        "ExaminationSlot",
        back_populates="bookings"
    )

    evaluation = relationship(
        "Evaluation",
        back_populates="booking",
        uselist=False
    )

    proctoring_events = relationship(
        "ProctoringEvent",
        back_populates="booking"
    )


# ==========================================
# 9. EVALUATION TABLE
# Marks and feedback
# ==========================================

class Evaluation(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(Integer,
                        ForeignKey("bookings.booking_id"),
                        unique=True, nullable=False)

    student_id = Column(Integer,
                        ForeignKey("student_profiles.student_id"),
                        nullable=False)

    examiner_id = Column(Integer,
                         ForeignKey("examiner_profiles.examiner_id"),
                         nullable=False)

    total_marks = Column(Float, nullable=False)
    remarks = Column(String(255))

    evaluation_date = Column(Date, default=date.today)
    status = Column(String(20), default="draft")

    booking = relationship(
        "Booking",
        back_populates="evaluation"
    )

    student = relationship(
        "StudentProfile",
        back_populates="evaluations"
    )

    examiner = relationship(
        "ExaminerProfile",
        back_populates="evaluations"
    )


# ==========================================
# 10. PROCTORING EVENTS TABLE
# Webcam monitoring observations
# ==========================================

class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"

    event_id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(Integer,
                        ForeignKey("bookings.booking_id"),
                        nullable=False)

    event_type = Column(String(50), nullable=False)
    snapshot_path = Column(String(255))
    detected_faces = Column(Integer)
    review_status = Column(String(20), default="pending")

    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    booking = relationship(
        "Booking",
        back_populates="proctoring_events"
    )







                    
