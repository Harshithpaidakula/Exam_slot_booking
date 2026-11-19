from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, Request, Form, Depends,
    Cookie, HTTPException, status
)

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo

import database
import models
import utils
import oauth2

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.create_tables()
    yield


app = FastAPI(title="ExamGuard", lifespan=lifespan)

templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)


# Display student registration page
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={
            "message": None,
            "error": None
        }
    )


# Find the logged-in user using their JWT cookie
def get_logged_in_user(request: Request, db: Session):

    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        return oauth2.get_user_from_token(token, db)

    except HTTPException:
        return None


# Check whether the user has the required role
def check_role(user, required_role):

    if user.role != required_role:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to access this page."
        )


# Process student registration form
@app.post("/register", response_class=HTMLResponse)
def register_student(
    request: Request,
    username: str = Form(...),
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):

    # Remove unnecessary spaces
    username = username.strip()
    fullname = fullname.strip()
    email = email.strip().lower()

    error = None

    # Basic validation
    if not 3 <= len(username) <= 80:
        error = "Username must contain 3 to 80 characters."

    elif not 1 <= len(fullname) <= 50:
        error = "Full name is required and must be under 50 characters."

    elif "@" not in email:
        error = "Enter a valid email address."

    elif len(password) < 8:
        error = "Password must contain at least 8 characters."

    # Check whether username already exists
    elif db.query(models.User).filter(
        models.User.username == username
    ).first():
        error = "Username already exists."

    # Check whether email already exists
    elif db.query(models.User).filter(
        models.User.email == email
    ).first():
        error = "Email already registered."

    # Show error on registration page
    if error:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={
                "message": None,
                "error": error
            },
            status_code=400
        )

    # Create student account
    student = models.User(
        username=username,
        fullname=fullname,
        email=email,
        password_hash=utils.hash_password(password),
        role="Student",
        isactive=True
    )

    # Create associated student profile
    student.student_profile = models.StudentProfile()

    # Save both records in PostgreSQL
    db.add(student)
    db.commit()

    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={
            "message": "Student registered successfully!",
            "error": None
        }
    )

# Display login page
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"error": None}
    )


# Process login form
@app.post("/login", response_class=HTMLResponse)
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):

    # Find user by username
    user = db.query(models.User).filter(
        models.User.username == username.strip()
    ).first()

    # Check username, password and account status
    if (
        not user
        or not utils.verify_password(password, user.password_hash)
        or not user.isactive
    ):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid username or password."},
            status_code=401
        )

    # Create JWT
    token = oauth2.create_access_token(user.id)

    # Redirect and save JWT in browser cookie
    dashboard_urls = {
    "Admin": "/admin/dashboard",
    "Examiner": "/examiner/dashboard",
    "Student": "/student/dashboard"
     }

    response = RedirectResponse(
    url=dashboard_urls[user.role],
    status_code=status.HTTP_303_SEE_OTHER
     )


    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Local HTTP development only
        samesite="lax",
        max_age=oauth2.TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    return response



# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):

    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login")

    check_role(user, "Admin")
    courses = db.query(models.Course).all()

    return templates.TemplateResponse(
        request=request,
        name="common/dashboard.html",
        context={
            "user": user,
            "courses": courses
        }
    )


@app.get("/admin/courses", response_class=HTMLResponse)
def manage_courses(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    check_role(user, "Admin")

    courses = db.query(models.Course).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/courses.html",
        context={
            "request": request,
            "user": user,
            "courses": courses
        }
    )



@app.post("/admin/courses")
def add_course(
    request: Request,
    course_code: str = Form(...),
    course_name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    course_code = course_code.strip().upper()
    course_name = course_name.strip()

    if not course_code or not course_name:
        courses = db.query(models.Course).all()
        return templates.TemplateResponse(
            request=request,
            name="admin/courses.html",
            context={
                "request": request,
                "user": user,
                "courses": courses,
                "error": "Course code and name are required."
            },
            status_code=400
        )

    existing_course = db.query(models.Course).filter(
        models.Course.course_code == course_code
    ).first()

    if existing_course:
        courses = db.query(models.Course).all()
        return templates.TemplateResponse(
            request=request,
            name="admin/courses.html",
            context={
                "request": request,
                "user": user,
                "courses": courses,
                "error": "This course code already exists."
            },
            status_code=400
        )

    new_course = models.Course(
        course_code=course_code,
        course_name=course_name,
        description=description.strip(),
        status="Active"
    )

    db.add(new_course)
    db.commit()

    courses = db.query(models.Course).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/courses.html",
        context={
            "request": request,
            "user": user,
            "courses": courses
        }
    )


@app.post("/admin/courses/{course_id}/toggle-status")
def toggle_course_status(
    course_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    course = db.query(models.Course).filter(
        models.Course.course_id == course_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.status.lower() == "active":
        course.status = "Inactive"
    else:
        course.status = "Active"

    db.commit()

    return RedirectResponse("/admin/courses", status_code=303)


@app.get("/admin/examiners", response_class=HTMLResponse)
def manage_examiners(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    examiners = db.query(models.User).filter(
        models.User.role == "Examiner"
    ).all()

    
    return templates.TemplateResponse(
        request=request,
        name="admin/examiners.html",
        context={
        "request": request,
        "user": user,
        "examiners": examiners
        }
    )

@app.post("/admin/examiners")
def create_examiner(
    request: Request,
    username: str = Form(...),
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    department: str = Form(...),
    designation: str = Form(...),
    employee_code: str = Form(...),
    contact_details: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    username = username.strip()
    fullname = fullname.strip()
    email = email.strip().lower()
    department = department.strip()
    designation = designation.strip()
    employee_code = employee_code.strip()

    examiners = db.query(models.User).filter(
        models.User.role == "Examiner"
    ).all()

    existing_user = db.query(models.User).filter(
        (models.User.username == username) |
        (models.User.email == email)
    ).first()

    existing_code = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.employee_code == employee_code
    ).first()

    if existing_user or existing_code:
        return templates.TemplateResponse(
            request=request,
            name="admin/examiners.html",
            context={
                "request": request,
                "user": user,
                "examiners": examiners,
                "error": "Username, email, or employee code already exists."
            },
            status_code=400
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="admin/examiners.html",
            context={
                "request": request,
                "user": user,
                "examiners": examiners,
                "error": "Password must contain at least 8 characters."
            },
            status_code=400
        )

    new_user = models.User(
        username=username,
        fullname=fullname,
        email=email,
        password_hash=utils.hash_password(password),
        role="Examiner",
        isactive=True
    )

    try:
        db.add(new_user)
        db.flush()

        new_profile = models.ExaminerProfile(
            user_id=new_user.id,
            department=department,
            designation=designation,
            employee_code=employee_code,
            contact_details=contact_details.strip(),
            status="Active"
        )

        db.add(new_profile)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/admin/examiners",
        status_code=303
    )


@app.get("/admin/examinations", response_class=HTMLResponse)
def manage_examinations(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    courses = db.query(models.Course).filter(
        models.Course.status.ilike("active")
    ).all()

    examiners = db.query(models.User).join(
        models.ExaminerProfile
    ).filter(
        models.User.role == "Examiner",
        models.User.isactive.is_(True),
        models.ExaminerProfile.status.ilike("active")
    ).all()

    examinations = db.query(models.Examination).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/examinations.html",
        context={
            "request": request,
            "user": user,
            "courses": courses,
            "examiners": examiners,
            "examinations": examinations
        }
    )


@app.post("/admin/examinations")
def create_examination(
    request: Request,
    examination_name: str = Form(...),
    examination_type: str = Form(...),
    course_id: int = Form(...),
    examiner_id: int = Form(...),
    duration: float = Form(...),
    maximum_marks: int = Form(...),
    slot_creation_start_date: str = Form(""),
    slot_creation_end_date: str = Form(""),
    slot_booking_start_date: str = Form(""),
    slot_booking_end_date: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    examination_name = examination_name.strip()

    if not examination_name:
        raise HTTPException(status_code=400, detail="Examination name is required.")

    if duration <= 0 or maximum_marks <= 0:
        raise HTTPException(status_code=400, detail="Duration and marks must be positive.")

    # Check whether the selected course exists and is active.
    course = db.query(models.Course).filter(
        models.Course.course_id == course_id,
        models.Course.status.ilike("active")
    ).first()

    if not course:
        raise HTTPException(status_code=400, detail="Invalid or inactive course.")

    # Check whether the selected examiner exists and is active.
    examiner = db.query(models.ExaminerProfile).join(
        models.User,
        models.User.id == models.ExaminerProfile.user_id
    ).filter(
        models.ExaminerProfile.examiner_id == examiner_id,
        models.ExaminerProfile.status.ilike("active"),
        models.User.role == "Examiner",
        models.User.isactive.is_(True)
    ).first()

    if not examiner:
        raise HTTPException(status_code=400, detail="Invalid or inactive examiner.")

    examinations = db.query(models.Examination).all()

    # Convert HTML datetime values into timezone-aware Python values.
    def convert_datetime(value):
        if not value:
            return None

        return datetime.fromisoformat(value).replace(
            tzinfo=ZoneInfo("Asia/Kolkata")
        )

    creation_start = convert_datetime(slot_creation_start_date)
    creation_end = convert_datetime(slot_creation_end_date)

    booking_start = convert_datetime(slot_booking_start_date)
    booking_end = convert_datetime(slot_booking_end_date)

    if creation_start and creation_end and creation_end <= creation_start:
        raise HTTPException(status_code=400, detail="Invalid slot creation date range.")

    if booking_start and booking_end and booking_end <= booking_start:
        raise HTTPException(status_code=400, detail="Invalid booking date range.")

    if booking_end and booking_end <= datetime.now(ZoneInfo("Asia/Kolkata")):
        raise HTTPException(
            status_code=400,
            detail="Booking end date cannot be in the past."
        )

    new_exam = models.Examination(
        examination_name=examination_name,
        examination_type=examination_type,
        course_id=course_id,
        examiner_id=examiner_id,
        duration=duration,
        maximum_marks=maximum_marks,
        slot_creation_start_date=creation_start,
        slot_creation_end_date=creation_end,
        slot_booking_start_date=booking_start,
        slot_booking_end_date=booking_end,
        status="draft"
    )

    try:
        db.add(new_exam)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse("/admin/examinations", status_code=303)


@app.get("/admin/rubrics", response_class=HTMLResponse)
def manage_rubrics(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    examinations = db.query(models.Examination).filter(
        models.Examination.status == "draft"
    ).all()
    rubrics = db.query(models.ExaminationRubric).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/rubrics.html",
        context={
            "request": request,
            "user": user,
            "examinations": examinations,
            "rubrics": rubrics
        }
    )


@app.post("/admin/rubrics")
def add_rubric(
    request: Request,
    examination_id: int = Form(...),
    criterion_name: str = Form(...),
    maximum_marks: float = Form(...),
    weightage: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    examinations = db.query(models.Examination).filter(
        models.Examination.status == "draft"
    ).all()

    examination = db.query(models.Examination).filter(
        models.Examination.exam_id == examination_id,
        models.Examination.status == "draft"
    ).first()

    if not examination:
        return templates.TemplateResponse(
            request=request,
            name="admin/rubrics.html",
            context={
                "request": request,
                "user": user,
                "examinations": examinations,
                "error": "Please select a valid Draft examination."
            },
            status_code=400
        )

    criterion_name = criterion_name.strip()

    if not criterion_name or maximum_marks <= 0:
        return templates.TemplateResponse(
            request=request,
            name="admin/rubrics.html",
            context={
                "request": request,
                "user": user,
                "examinations": examinations,
                "error": "Enter a valid criterion name and maximum marks."
            },
            status_code=400
        )

    weightage_value = None

    if weightage.strip():
        try:
            weightage_value = float(weightage)
        except ValueError:
            weightage_value = -1

        if not 0 <= weightage_value <= 100:
            return templates.TemplateResponse(
                request=request,
                name="admin/rubrics.html",
                context={
                    "request": request,
                    "user": user,
                    "examinations": examinations,
                    "error": "Weightage must be between 0 and 100."
                },
                status_code=400
            )

    existing_rubrics = db.query(
        models.ExaminationRubric
    ).filter(
        models.ExaminationRubric.examination_id == examination_id
    ).all()

    current_total = sum(
        rubric.maximum_marks for rubric in existing_rubrics
    )

    if current_total + maximum_marks > examination.maximum_marks:
        return templates.TemplateResponse(
            request=request,
            name="admin/rubrics.html",
            context={
                "request": request,
                "user": user,
                "examinations": examinations,
                "error": "Total rubric marks cannot exceed examination maximum marks."
            },
            status_code=400
        )

    new_rubric = models.ExaminationRubric(
        examination_id=examination_id,
        criterion_name=criterion_name,
        maximum_marks=maximum_marks,
        weightage=weightage_value,
        description=description.strip()
    )

    try:
        db.add(new_rubric)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/admin/rubrics",
        status_code=303
    )


@app.post("/admin/examinations/{exam_id}/status")
def update_examination_status(
    exam_id: int,
    request: Request,
    new_status: str = Form(...),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    exam = db.query(models.Examination).filter(
        models.Examination.exam_id == exam_id
    ).first()

    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found.")

    current_status = exam.status.lower()
    new_status = new_status.strip().lower()

    # Publish or reactivate an examination
    if new_status == "active":

        if current_status not in ["draft", "inactive"]:
            raise HTTPException(status_code=400, detail="Invalid status change.")

        rubrics = db.query(models.ExaminationRubric).filter(
            models.ExaminationRubric.examination_id == exam_id
        ).all()

        total_marks = sum(r.maximum_marks for r in rubrics)

        if total_marks != exam.maximum_marks:
            raise HTTPException(
                status_code=400,
                detail=f"Rubric marks must total {exam.maximum_marks}. Current total: {total_marks}."
            )

        exam.status = "active"

    # Deactivate an active examination
    elif new_status == "inactive":

        if current_status != "active":
            raise HTTPException(status_code=400, detail="Invalid status change.")

        exam.status = "inactive"

    else:
        raise HTTPException(status_code=400, detail="Invalid examination status.")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/admin/examinations",
        status_code=303
    )

@app.get("/admin/results", response_class=HTMLResponse)
def manage_results(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    evaluations = db.query(models.Evaluation).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/admin_results.html",
        context={
            "request": request,
            "user": user,
            "evaluations": evaluations
        }
    )

@app.post("/admin/results/{evaluation_id}/publish")
def publish_result(
    evaluation_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Admin")

    evaluation = db.query(models.Evaluation).filter(
        models.Evaluation.evaluation_id == evaluation_id
    ).first()

    if not evaluation:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found."
        )

    if evaluation.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="This result has already been published."
        )

    evaluation.status = "published"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/admin/results",
        status_code=303
    )

# Examiner dashboard
@app.get("/examiner/dashboard", response_class=HTMLResponse)
def examiner_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):

    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login")

    check_role(user, "Examiner")

    return templates.TemplateResponse(
        request=request,
        name="common/dashboard.html",
        context={"user": user}
    )


@app.get("/examiner/examinations", response_class=HTMLResponse)
def my_examinations(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Examiner")

    examiner_profile = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.user_id == user.id
    ).first()

    if not examiner_profile:
        raise HTTPException(
            status_code=404,
            detail="Examiner profile not found."
        )

    examinations = db.query(models.Examination).filter(
        models.Examination.examiner_id == examiner_profile.examiner_id
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="examiner/examiner_examinations.html",
        context={
            "request": request,
            "user": user,
            "examinations": examinations
        }
    )

@app.get("/examiner/slots", response_class=HTMLResponse)
def manage_slots(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Examiner")

    examiner_profile = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.user_id == user.id
    ).first()

    if not examiner_profile:
        raise HTTPException(status_code=404, detail="Examiner profile not found.")

    examinations = db.query(models.Examination).filter(
        models.Examination.examiner_id == examiner_profile.examiner_id,
        models.Examination.status == "active"
    ).all()
    slots = db.query(models.ExaminationSlot).filter(
    models.ExaminationSlot.examiner_id == examiner_profile.examiner_id
    ).all()
    bookings = db.query(models.Booking).join(
    models.ExaminationSlot,
    models.Booking.slot_id == models.ExaminationSlot.slot_id
    ).filter(
    models.ExaminationSlot.examiner_id == examiner_profile.examiner_id
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="examiner/examiner_slots.html",
        context={
            "request": request,
            "user": user,
            "examinations": examinations,
            "slots": slots,
            "bookings": bookings
        }
    )

@app.post("/examiner/slots")
def create_slot(
    request: Request,
    examination_id: int = Form(...),
    slot_date: str = Form(..., alias="date"),
    start_time: str = Form(...),
    end_time: str = Form(...),
    maximum_student_capacity: int = Form(...),
    meeting_link: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Examiner")

    examiner_profile = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.user_id == user.id
    ).first()

    if not examiner_profile:
        raise HTTPException(status_code=404, detail="Examiner profile not found.")

    # Check ownership and examination status
    examination = db.query(models.Examination).filter(
        models.Examination.exam_id == examination_id,
        models.Examination.examiner_id == examiner_profile.examiner_id,
        models.Examination.status == "active"
    ).first()

    if not examination:
        raise HTTPException(
            status_code=400,
            detail="Invalid examination or examination is not active."
        )

    # Convert HTML form values into Python date and time objects
    exam_date = datetime.strptime(slot_date, "%Y-%m-%d").date()
    start = datetime.strptime(start_time, "%H:%M").time()
    end = datetime.strptime(end_time, "%H:%M").time()

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="End time must be later than start time."
        )

    if maximum_student_capacity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Student capacity must be greater than zero."
        )

    # Slot duration must match examination duration
    slot_duration = (
        datetime.combine(exam_date, end) -
        datetime.combine(exam_date, start)
    ).total_seconds() / 60

    if abs(slot_duration - examination.duration) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Slot duration must be {examination.duration} minutes."
        )

    new_slot = models.ExaminationSlot(
        examination_id=examination.exam_id,
        examiner_id=examiner_profile.examiner_id,
        date=exam_date,
        start_time=start,
        end_time=end,
        maximum_student_capacity=maximum_student_capacity,
        available_seats=maximum_student_capacity,
        status="available",
        meeting_link=meeting_link.strip() or None
    )

    try:
        db.add(new_slot)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/examiner/slots",
        status_code=303
    )


@app.get("/examiner/evaluations", response_class=HTMLResponse)
def manage_evaluations(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Examiner")

    examiner_profile = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.user_id == user.id
    ).first()

    if not examiner_profile:
        raise HTTPException(
            status_code=404,
            detail="Examiner profile not found."
        )

    bookings = db.query(models.Booking).join(
        models.ExaminationSlot,
        models.Booking.slot_id == models.ExaminationSlot.slot_id
    ).filter(
        models.ExaminationSlot.examiner_id == examiner_profile.examiner_id,
        models.Booking.status == "booked"
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="examiner/examiner_evaluations.html",
        context={
            "request": request,
            "user": user,
            "bookings": bookings
        }
    )

@app.post("/examiner/evaluations")
def save_evaluation(
    request: Request,
    booking_id: int = Form(...),
    total_marks: float = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Examiner")

    # Get the logged-in examiner's profile
    examiner_profile = db.query(models.ExaminerProfile).filter(
        models.ExaminerProfile.user_id == user.id
    ).first()

    if not examiner_profile:
        raise HTTPException(status_code=404, detail="Examiner profile not found.")

    # Find a booking belonging to this examiner
    booking = db.query(models.Booking).join(
        models.ExaminationSlot,
        models.Booking.slot_id == models.ExaminationSlot.slot_id
    ).filter(
        models.Booking.booking_id == booking_id,
        models.ExaminationSlot.examiner_id == examiner_profile.examiner_id,
        models.Booking.status == "booked"
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found or not assigned to you."
        )

    # Prevent duplicate evaluation
    existing_evaluation = db.query(models.Evaluation).filter(
        models.Evaluation.booking_id == booking_id
    ).first()

    if existing_evaluation:
        raise HTTPException(
            status_code=400,
            detail="This student has already been evaluated."
        )

    # Check marks against examination maximum
    maximum_marks = booking.slot.examination.maximum_marks

    if total_marks < 0 or total_marks > maximum_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Marks must be between 0 and {maximum_marks}."
        )

    # Create evaluation
    new_evaluation = models.Evaluation(
        booking_id=booking.booking_id,
        student_id=booking.student_id,
        examiner_id=examiner_profile.examiner_id,
        total_marks=total_marks,
        remarks=remarks.strip(),
        status="draft"
    )

    try:
        db.add(new_evaluation)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/examiner/evaluations",
        status_code=303
    )


# Student dashboard
@app.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(
    request: Request,
    db: Session = Depends(database.get_db)
):

    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login")

    check_role(user, "Student")

    return templates.TemplateResponse(
        request=request,
        name="common/dashboard.html",
        context={"user": user}
    )



@app.get("/student/examinations", response_class=HTMLResponse)
def available_examinations(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    examinations = db.query(models.Examination).filter(
        models.Examination.status == "active"
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="student/student_examinations.html",
        context={
            "request": request,
            "user": user,
            "examinations": examinations
        }
    )


@app.get(
    "/student/examinations/{exam_id}/slots",
    response_class=HTMLResponse
)
def view_available_slots(
    exam_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    examination = db.query(models.Examination).filter(
        models.Examination.exam_id == exam_id,
        models.Examination.status == "active"
    ).first()

    if not examination:
        raise HTTPException(
            status_code=404,
            detail="Examination not found or unavailable."
        )

    slots = db.query(models.ExaminationSlot).filter(
        models.ExaminationSlot.examination_id == exam_id,
        models.ExaminationSlot.status == "available",
        models.ExaminationSlot.available_seats > 0
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="student/student_slots.html",
        context={
            "request": request,
            "user": user,
            "examination": examination,
            "slots": slots
        }
    )


@app.post("/student/book/{slot_id}")
def book_examination_slot(
    slot_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    # Find the student's profile
    student = db.query(models.StudentProfile).filter(
        models.StudentProfile.user_id == user.id
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found.")

    # Find the selected available slot
    slot = db.query(models.ExaminationSlot).filter(
        models.ExaminationSlot.slot_id == slot_id,
        models.ExaminationSlot.status == "available"
    ).first()

    if not slot or slot.available_seats <= 0:
        raise HTTPException(status_code=400, detail="This slot is not available.")

    # Check that its examination is active
    examination = db.query(models.Examination).filter(
        models.Examination.exam_id == slot.examination_id,
        models.Examination.status == "active"
    ).first()

    if not examination:
        raise HTTPException(status_code=400, detail="Examination is not active.")

    # Check the examination's booking window
    now = datetime.now(ZoneInfo("Asia/Kolkata"))

    if examination.slot_booking_start_date and now < examination.slot_booking_start_date:
        raise HTTPException(status_code=400, detail="Booking has not started yet.")

    if examination.slot_booking_end_date and now > examination.slot_booking_end_date:
        raise HTTPException(status_code=400, detail="Booking period has ended.")

    # Prevent the student from booking this examination twice
    existing_booking = db.query(models.Booking).join(
        models.ExaminationSlot,
        models.Booking.slot_id == models.ExaminationSlot.slot_id
    ).filter(
        models.Booking.student_id == student.student_id,
        models.ExaminationSlot.examination_id == examination.exam_id,
        models.Booking.status == "booked"
    ).first()

    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="You have already booked this examination."
        )

    # Create the booking
    new_booking = models.Booking(
        student_id=student.student_id,
        slot_id=slot.slot_id,
        status="booked"
    )

    # Reduce available seats
    slot.available_seats -= 1

    if slot.available_seats == 0:
        slot.status = "full"

    try:
        db.add(new_booking)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/student/examinations",
        status_code=303
    )









# Protected dashboard
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(database.get_db)
):

    # Check whether user is logged in
    if not access_token:
        return RedirectResponse("/login")

    # Verify JWT and get user
    try:
        user = oauth2.get_user_from_token(access_token, db)

    except HTTPException:
        response = RedirectResponse("/login")
        response.delete_cookie("access_token", path="/")
        return response

    # Show dashboard according to user's role
    return templates.TemplateResponse(
        request=request,
        name="common/dashboard.html",
        context={"user": user}
    )


# Logout
@app.post("/logout")
def logout():

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER
    )

    response.delete_cookie("access_token", path="/")

    return response



@app.get("/student/bookings", response_class=HTMLResponse)
def my_bookings(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    student = db.query(models.StudentProfile).filter(
        models.StudentProfile.user_id == user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    bookings = db.query(models.Booking).filter(
        models.Booking.student_id == student.student_id
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="student/student_bookings.html",
        context={
            "request": request,
            "user": user,
            "bookings": bookings
        }
    )

@app.post("/student/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    student = db.query(models.StudentProfile).filter(
        models.StudentProfile.user_id == user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    # Find this student's booking
    booking = db.query(models.Booking).filter(
        models.Booking.booking_id == booking_id,
        models.Booking.student_id == student.student_id,
        models.Booking.status == "booked"
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Active booking not found."
        )

    # Restore the available seat
    slot = booking.slot
    slot.available_seats += 1
    slot.status = "available"

    # Mark booking as cancelled
    booking.status = "cancelled"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/student/bookings",
        status_code=303
    )



@app.get("/student/results", response_class=HTMLResponse)
def student_results(
    request: Request,
    db: Session = Depends(database.get_db)
):
    user = get_logged_in_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)

    check_role(user, "Student")

    student = db.query(models.StudentProfile).filter(
        models.StudentProfile.user_id == user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    results = db.query(models.Evaluation).filter(
        models.Evaluation.student_id == student.student_id,
        models.Evaluation.status == "published"
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="student/student_results.html",
        context={
            "request": request,
            "user": user,
            "results": results
        }
    )
