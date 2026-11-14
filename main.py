from pathlib import Path

# FastAPI tools for pages, forms, errors, and dependency injection.
from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request, status

# HTMLResponse returns a page. RedirectResponse sends the browser to another URL.
from fastapi.responses import HTMLResponse, RedirectResponse

# Jinja2Templates connects Python routes to HTML files in the templates folder.
from fastapi.templating import Jinja2Templates

# Session lets us use the database in a route.
from sqlalchemy.orm import Session

# Project files used by this application.
import database
import models
import oauth2
import schemas
import utils


# This creates the FastAPI application.
# The templates object tells FastAPI where our HTML files are stored.


app = FastAPI()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)


# This function runs when the server starts.
# It creates the database tables if they do not exist.
@app.on_event("startup")
def create_tables():
    database.create_tables()


# Find one user in the database by username.
# Both registration and login use this helper.
def find_user(username: str, db: Session):
    return db.query(models.User).filter(
        models.User.username == username
    ).first()


# Check whether the username and password are acceptable.
# HTTPException stops the request and sends an error message.
def validate_user(username: str, password: str):
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required.",
        )
    if len(username) < 3 or len(username) > 80:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must contain 3 to 80 characters.",
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 8 characters.",
        )


# Create a student account and save it in the database.
def register_student(data: schemas.StudentRegister, db: Session):
    validate_user(data.username, data.password)

    if find_user(data.username, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    if data.roll_number:
        roll_number_exists = db.query(models.StudentProfile).filter(
            models.StudentProfile.roll_number == data.roll_number
        ).first()
        if roll_number_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Roll number is already taken.",
            )

    # Hash the password before saving it.
    # We should never save a plain-text password.
    user = models.User(
        username=data.username,
        fullname=data.username,
        password_hash=utils.hash_password(data.password),
        role="Student",
    )
    user.student_profile = models.StudentProfile(
        roll_number=data.roll_number,
        department=data.department,
        programme=data.programme,
        semester=data.semester,
    )

    db.add(user)
    db.commit()


# Check the login details and return the user when they are correct.
def check_login(username: str, password: str, db: Session):
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required.",
        )

    user = find_user(username, db)
    if not user or not utils.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    return user


# GET / displays the login page.
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"message": None, "error": None},
    )


# GET /register displays the registration page.
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"message": None, "error": None, "form_data": {}},
    )


# POST /register-form receives the registration form from register.html.
@app.post("/register-form", response_class=HTMLResponse)
def register_form(
    request: Request,
    # Form(...) reads values sent by HTML inputs.
    username: str = Form(...),
    password: str = Form(...),
    roll_number: str | None = Form(None),
    department: str | None = Form(None),
    programme: str | None = Form(None),
    semester: int | None = Form(None),
    db: Session = Depends(database.get_db),
):
    # Keep the values so Jinja can refill the form after an error.
    form_data = {
        "username": username,
        "roll_number": roll_number or "",
        "department": department or "",
        "programme": programme or "",
        "semester": semester or "",
    }

    try:
        register_student(
            schemas.StudentRegister(
                username=username,
                password=password,
                roll_number=roll_number,
                department=department,
                programme=programme,
                semester=semester,
            ),
            db,
        )
    except HTTPException as error:
        # If validation fails, show the error on the same page.
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "message": None,
                "error": error.detail,
                "form_data": form_data,
            },
            status_code=error.status_code,
        )

    # If everything works, show a success message.
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "message": "Student registered successfully.",
            "error": None,
            "form_data": {},
        },
    )


# GET /login displays the login page.
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"message": None, "error": None},
    )


# POST /login-form receives the login form from login.html.
@app.post("/login-form", response_class=HTMLResponse)
def login_form(
    request: Request,
    # These values come from the HTML form inputs.
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db),
):
    # Check the username and password.
    try:
        user = check_login(username, password, db)
    except HTTPException as error:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"message": None, "error": error.detail},
            status_code=error.status_code,
        )

    # Create a JWT and store it in a browser cookie.
    # The cookie will be sent automatically on future requests.
    response = RedirectResponse("/profile", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        "access_token",
        oauth2.create_access_token(user.id),
        httponly=True,
        max_age=600,
        samesite="lax",
    )
    return response


# GET /profile is protected. The user must have a valid JWT cookie.
@app.get("/profile", response_class=HTMLResponse)
def profile(
    request: Request,
    access_token: str | None = Cookie(None),
    db: Session = Depends(database.get_db),
):
    # No cookie means the user has not logged in.
    if not access_token:
        return RedirectResponse("/login")

    try:
        # Decode the JWT and find the logged-in user.
        user = oauth2.get_user_from_token(access_token, db)
    except HTTPException:
        # Invalid or expired tokens go back to the login page.
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"username": user.username},
    )


# GET /logout removes the JWT cookie and logs the user out.
@app.get("/logout")
def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response
