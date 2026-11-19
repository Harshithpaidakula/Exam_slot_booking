
# Academic Examination Management and Results Portal

## About the Project

Academic Examination Management and Results Portal is a web-based examination slot booking and management system developed using Python and FastAPI.

The main purpose of this project is to make examination management easier for students, examiners and administrators.

Instead of managing examinations manually, Academic Examination Management and Results Portal allows students to view examinations and book available slots. Examiners can manage examination slots and evaluate students. Admins can manage courses, examiners, examinations and publish results.

I built this project to understand how a real-world web application works, including database management, authentication, user roles and backend development.

## Technologies Used

- **Python** — Main programming language.
- **FastAPI** — Backend framework for handling requests and application logic.
- **PostgreSQL** — Database for storing application data.
- **SQLAlchemy** — Used to connect Python objects with database tables.
- **HTML** — Used to create web pages and forms.
- **Jinja2** — Used to display dynamic data in HTML pages.
- **JWT** — Used for user authentication.
- **Passlib** — Used for password hashing.

## User Roles

Academic Examination Management and Results Portal has three types of users.

### 1. Admin

The Admin manages the overall examination system.

- Create and manage courses.
- Create examiner accounts.
- Create examinations.
- Assign courses and examiners.
- Add examination evaluation criteria.
- Activate and deactivate courses.
- Publish examination results.

### 2. Examiner

The Examiner manages assigned examinations.

- View assigned examinations.
- Create examination slots.
- View created slots.
- View students who booked slots.
- Enter student marks and remarks.

### 3. Student

Students use the system to participate in examinations.

- Register and log in.
- View available examinations.
- View available examination slots.
- Book an examination slot.
- View booking history.
- Cancel bookings.
- View published examination results.

## Main Features

**User Authentication:** Users can log in using their username and password. Passwords are stored as hashes, and JWT is used for authentication.

**Role-Based Access Control:** Admin, Examiner and Student have different permissions. Users cannot access pages belonging to other roles.

**Course Management:** Admin can create, view and activate or deactivate courses.

**Examination Management:** Admin can create examinations, assign courses and examiners, and manage examination status.

**Slot Management:** Examiners can create examination slots with dates, timings and student capacity.

**Slot Booking:** Students can book available slots. The system checks available seats and prevents duplicate bookings for the same examination.

**Evaluation and Results:** Examiners can enter marks and remarks. Admin reviews and publishes results, which students can then view.

## Database Design

The project uses PostgreSQL with SQLAlchemy ORM.

The main database tables are:

| Table | Purpose |
|---|---|
| users | Stores user login information and roles |
| student_profiles | Stores student details |
| examiner_profiles | Stores examiner details |
| courses | Stores course information |
| examinations | Stores examination details |
| examination_rubrics | Stores examination evaluation criteria |
| examination_slots | Stores available examination slots |
| bookings | Stores student bookings |
| evaluations | Stores marks and remarks |
| proctoring_events | Stores examination monitoring event records |

The tables are connected using primary keys, foreign keys and SQLAlchemy relationships.

## Project Structure

```text
examguard/
│
├── main.py
├── database.py
├── models.py
├── oauth2.py
├── utils.py
├── schemas.py
├── create_admin.py
│
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── courses.html
│   ├── examiners.html
│   ├── examinations.html
│   ├── rubrics.html
│   ├── examiner_examinations.html
│   ├── examiner_slots.html
│   ├── examiner_evaluations.html
│   ├── admin_results.html
│   ├── student_examinations.html
│   ├── student_slots.html
│   ├── student_bookings.html
│   └── student_results.html
│
├── static/
├── .env
└── README.md
```

## How to Run the Project

### Step 1: Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd examguard
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### Step 3: Install the dependencies

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv python-jose[cryptography] passlib jinja2 python-multipart
```

### Step 4: Create a PostgreSQL database

Create a database named:

```text
exam_guard
```

### Step 5: Configure the environment variables

Create a `.env` file in the project folder.

Add your own database credentials and secret values:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/exam_guard

JWT_SECRET_KEY=YOUR_SECRET_KEY

ADMIN_NAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD
```

### Step 6: Create the Admin account

```bash
python create_admin.py
```

The database tables are created automatically by the project.

### Step 7: Run the application

```bash
uvicorn main:app --reload
```

Open your browser:

```text
http://127.0.0.1:8000/login
```

Log in using your Admin credentials.

## Complete Application Workflow

1. Admin creates courses and examiner accounts.
2. Admin creates examinations and assigns examiners.
3. Admin adds evaluation criteria and publishes examinations.
4. Examiner creates available examination slots.
5. Students register, view examinations and book slots.
6. Examiner views booked students and enters marks.
7. Admin publishes the results.
8. Students view their published results.

## What I Learned From This Project

While developing Academic Examination Management and Results Portal, I learned:

- How FastAPI handles GET and POST requests.
- How to connect Python applications with PostgreSQL.
- How SQLAlchemy ORM works.
- How primary keys, foreign keys and relationships work.
- How JWT authentication works.
- How to hash and verify passwords.
- How to implement role-based access control.
- How to process HTML forms using FastAPI.
- How to save and retrieve data from a database.
- How to build a complete application workflow.

## Future Improvements

Some features that can be added in future versions:

- Webcam-based online examination monitoring.
- Better user interface and responsive design.
- Email notifications for examination bookings.
- More detailed examination reports.
- Additional security and validation.

---

**Academic Examination Management and Results Portal — Making examination management easier for students, examiners and administrators.**