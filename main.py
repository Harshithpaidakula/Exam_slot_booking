from pathlib import Path

from fastapi import (
    FastAPI, Request, Form, Depends,
    Cookie, HTTPException, status
)

from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import database
import models
import utils
import oauth2

app = FastAPI(title="ExamGuard")

templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)


# Create database tables when application starts
@app.on_event("startup")
def startup():
    database.create_tables()


# Display student registration page
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
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
            name="register.html",
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
        name="register.html",
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
        name="login.html",
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
            name="login.html",
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

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user}
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
        name="dashboard.html",
        context={"user": user}
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
        name="dashboard.html",
        context={"user": user}
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
        name="dashboard.html",
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