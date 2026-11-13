from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Student Management API")
student_router = APIRouter()


# 1. Pydantic Model
class Student(BaseModel):
    id: int
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(gt=0, le=100)
    course: str
    email: str


# 2. Response Model
class StudentResponse(BaseModel):
    id: int
    name: str
    age: int
    course: str
    email: str


# 3. Update Model
class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    course: Optional[str] = None
    email: Optional[str] = None


# 4. In-memory student records
students = [
    {
        "id": 1,
        "name": "Rahul",
        "age": 22,
        "course": "Python",
        "email": "rahul@gmail.com"
    },
    {
        "id": 2,
        "name": "Aman",
        "age": 23,
        "course": "Data Science",
        "email": "aman@gmail.com"
    },
    {
        "id": 3,
        "name": "Priya",
        "age": 21,
        "course": "Python",
        "email": "priya@gmail.com"
    }
]


# 5. Home endpoint
@student_router.get("/")
def home():
    return {"message": "Welcome to Student Management API"}


# 6. Add Student (POST)
@student_router.post("/students", response_model=StudentResponse,
                     status_code=201)
def add_student(student: Student):

    for s in students:
        if s["id"] == student.id:
            raise HTTPException(
                status_code=400,
                detail="Student ID already exists"
            )

    students.append(student.model_dump())

    return student


# 7. Retrieve All Students with Pagination and Filtering
@student_router.get("/students", response_model=list[StudentResponse])
def get_students(
    name: Optional[str] = None,
    course: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, gt=0, le=100)
):

    result = students

    if name:
        result = [
            s for s in result
            if name.lower() in s["name"].lower()
        ]

    if course:
        result = [
            s for s in result
            if course.lower() in s["course"].lower()
        ]

    return result[skip:skip + limit]


# 8. Retrieve Student by ID (Path Parameter)
@student_router.get("/students/{student_id}",
                    response_model=StudentResponse)
def get_student(student_id: int):

    for student in students:
        if student["id"] == student_id:
            return student

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )


# 9. Update Student (PUT)
@student_router.put("/students/{student_id}",
                    response_model=StudentResponse)
def update_student(student_id: int, updated_data: Student):

    for index, student in enumerate(students):

        if student["id"] == student_id:

            if updated_data.id != student_id:
                raise HTTPException(
                    status_code=400,
                    detail="Student ID cannot be changed"
                )

            students[index] = updated_data.model_dump()

            return students[index]

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )


# 10. Delete Student (DELETE)
@student_router.delete("/students/{student_id}")
def delete_student(student_id: int):

    for index, student in enumerate(students):

        if student["id"] == student_id:
            deleted_student = students.pop(index)

            return {
                "message": "Student deleted successfully",
                "student": deleted_student
            }

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )


from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import Depends
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)

from pwdlib import PasswordHash
from pydantic import BaseModel, Field, field_validator


# 1. Password hashing
password_hash = PasswordHash.recommended()


# 2. JWT Configuration
SECRET_KEY = "REPLACE_WITH_YOUR_GENERATED_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# 3. OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# 4. In-memory user database
users_db = {}


# 5. Registration Request Model
class UserRegister(BaseModel):

    username: str = Field(min_length=3, max_length=30)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if len(value) < 8:
            raise ValueError("Password must have at least 8 characters")

        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain an uppercase letter")

        if not any(c.islower() for c in value):
            raise ValueError("Password must contain a lowercase letter")

        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain a digit")

        if not any(not c.isalnum() for c in value):
            raise ValueError("Password must contain a special character")

        return value


# 6. User Response Model
class UserResponse(BaseModel):
    username: str


# 7. Token Response Model
class Token(BaseModel):
    access_token: str
    token_type: str


# 8. Registration Endpoint
@app.post("/register", response_model=UserResponse,
          status_code=201)
def register_user(user: UserRegister):

    if user.username in users_db:
        raise HTTPException(
            status_code=409,
            detail="Username already registered"
        )

    hashed_password = password_hash.hash(user.password)

    users_db[user.username] = {
        "username": user.username,
        "hashed_password": hashed_password
    }

    return {"username": user.username}


# 9. Generate JWT Token
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    token = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# 10. Login Endpoint
@app.post("/login", response_model=Token)
def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):

    user = users_db.get(form_data.username)

    if not user or not password_hash.verify(
        form_data.password,
        user["hashed_password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        data={"sub": user["username"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# 11. Verify JWT Token
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception

    user = users_db.get(username)

    if user is None:
        raise credentials_exception

    return {"username": user["username"]}


# 12. Protected Endpoint
@app.get("/users/me", response_model=UserResponse)
def get_my_profile(
    current_user: Annotated[dict, Depends(get_current_user)]
):

    return current_user

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Annotated
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
import jwt


app = FastAPI(title="Student and Employee Management API with RBAC")
app.include_router(student_router)


# ==========================================
# 1. CONFIGURATION
# ==========================================

SECRET_KEY = "REPLACE_WITH_YOUR_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ==========================================
# 2. IN-MEMORY DATABASE
# ==========================================

users_db = {}
employees_db = {}


# Demo Admin Account
users_db["admin"] = {
    "username": "admin",
    "hashed_password": password_hash.hash("Admin123@"),
    "role": "admin"
}


# ==========================================
# 3. PYDANTIC MODELS
# ==========================================

# Registration Model
class UserRegister(BaseModel):

    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8)

    @classmethod
    def validate_password(cls, value):
        import re

        if not re.search(r"[A-Z]", value):
            raise ValueError("Uppercase letter required")

        if not re.search(r"[a-z]", value):
            raise ValueError("Lowercase letter required")

        if not re.search(r"[0-9]", value):
            raise ValueError("Number required")

        if not re.search(r"[^a-zA-Z0-9]", value):
            raise ValueError("Special character required")

        return value

    from pydantic import field_validator

    _password_validator = field_validator("password")(
        validate_password
    )


# User Response
class UserResponse(BaseModel):
    username: str
    role: str


# Token Response
class Token(BaseModel):
    access_token: str
    token_type: str


# Employee Create Model
class EmployeeCreate(BaseModel):

    employee_id: int = Field(gt=0)
    username: str = Field(min_length=3)
    name: str = Field(min_length=2, max_length=50)
    department: str = Field(min_length=2)
    salary: float = Field(gt=0)
    email: EmailStr


# Employee Update Model
class EmployeeUpdate(BaseModel):

    name: Optional[str] = Field(default=None, min_length=2)
    department: Optional[str] = Field(default=None, min_length=2)
    salary: Optional[float] = Field(default=None, gt=0)
    email: Optional[EmailStr] = None


# Employee Response Model
class EmployeeResponse(BaseModel):

    employee_id: int
    username: str
    name: str
    department: str
    salary: float
    email: EmailStr


# ==========================================
# 4. USER REGISTRATION
# ==========================================

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=201
)
def register_user(user: UserRegister):

    if user.username in users_db:
        raise HTTPException(
            status_code=409,
            detail="Username already exists"
        )

    hashed_password = password_hash.hash(user.password)

    users_db[user.username] = {
        "username": user.username,
        "hashed_password": hashed_password,
        "role": "employee"
    }

    return {
        "username": user.username,
        "role": "employee"
    }


# ==========================================
# 5. JWT TOKEN GENERATION
# ==========================================

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    token = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# ==========================================
# 6. LOGIN ENDPOINT
# ==========================================

@app.post("/login", response_model=Token)
def login_user(
    form_data: Annotated[
        OAuth2PasswordRequestForm, Depends()
    ]
):

    user = users_db.get(form_data.username)

    if not user or not password_hash.verify(
        form_data.password,
        user["hashed_password"]
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(
        {"sub": user["username"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ==========================================
# 7. GET CURRENT USER
# ==========================================

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except jwt.InvalidTokenError:
        raise credentials_exception

    user = users_db.get(username)

    if user is None:
        raise credentials_exception

    return user


# ==========================================
# 8. ADMIN ROLE VERIFICATION
# ==========================================

def get_current_admin(
    current_user: Annotated[
        dict, Depends(get_current_user)
    ]
):

    if current_user["role"] != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user


# ==========================================
# 9. VIEW OWN PROFILE
# ==========================================

@app.get("/users/me", response_model=UserResponse)
def get_my_profile(
    current_user: Annotated[
        dict, Depends(get_current_user)
    ]
):

    return {
        "username": current_user["username"],
        "role": current_user["role"]
    }


# ==========================================
# 10. CREATE EMPLOYEE - ADMIN ONLY
# ==========================================

@app.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=201
)
def create_employee(
    employee: EmployeeCreate,
    admin: Annotated[
        dict, Depends(get_current_admin)
    ]
):

    if employee.employee_id in employees_db:
        raise HTTPException(
            status_code=409,
            detail="Employee already exists"
        )

    user = users_db.get(employee.username)

    if user is None or user["role"] != "employee":
        raise HTTPException(
            status_code=404,
            detail="Employee user account not found"
        )

    for existing in employees_db.values():
        if existing["username"] == employee.username:
            raise HTTPException(
                status_code=409,
                detail="Employee profile already exists"
            )

    employees_db[employee.employee_id] = employee.model_dump()

    return employees_db[employee.employee_id]


# ==========================================
# 11. VIEW ALL EMPLOYEES - ADMIN ONLY
# ==========================================

@app.get(
    "/employees",
    response_model=list[EmployeeResponse]
)
def get_all_employees(
    admin: Annotated[
        dict, Depends(get_current_admin)
    ]
):

    return list(employees_db.values())


# ==========================================
# 12. VIEW OWN EMPLOYEE PROFILE
# ==========================================

@app.get(
    "/employees/me",
    response_model=EmployeeResponse
)
def get_my_employee_profile(
    current_user: Annotated[
        dict, Depends(get_current_user)
    ]
):

    for employee in employees_db.values():

        if employee["username"] == current_user["username"]:
            return employee

    raise HTTPException(
        status_code=404,
        detail="Employee profile not found"
    )


# ==========================================
# 13. VIEW EMPLOYEE BY ID - ADMIN ONLY
# ==========================================

@app.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse
)
def get_employee(
    employee_id: int,
    admin: Annotated[
        dict, Depends(get_current_admin)
    ]
):

    if employee_id not in employees_db:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return employees_db[employee_id]


# ==========================================
# 14. UPDATE EMPLOYEE - ADMIN ONLY
# ==========================================

@app.put(
    "/employees/{employee_id}",
    response_model=EmployeeResponse
)
def update_employee(
    employee_id: int,
    updated_data: EmployeeUpdate,
    admin: Annotated[
        dict, Depends(get_current_admin)
    ]
):

    if employee_id not in employees_db:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    update_data = updated_data.model_dump(
        exclude_unset=True
    )

    employees_db[employee_id].update(update_data)

    return employees_db[employee_id]


# ==========================================
# 15. DELETE EMPLOYEE - ADMIN ONLY
# ==========================================

@app.delete("/employees/{employee_id}")
def delete_employee(
    employee_id: int,
    admin: Annotated[
        dict, Depends(get_current_admin)
    ]
):

    if employee_id not in employees_db:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    del employees_db[employee_id]

    return {
        "message": "Employee deleted successfully"
    }


from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import time

app = FastAPI(title="File Upload and Processing API")

# 1. Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = [".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".json"]
# 2. In-memory storage
files_db = {}
tasks_db = {}


# 3. Background document processing
def process_document(task_id: str, file_id: str):

    try:
        tasks_db[task_id]["status"] = "PROCESSING"

        time.sleep(3)  # Simulate processing

        metadata = files_db[file_id]
        file_path = UPLOAD_DIR / metadata["stored_filename"]

        if not file_path.exists():
            raise FileNotFoundError("Uploaded file not found")

        tasks_db[task_id]["status"] = "COMPLETED"
        tasks_db[task_id]["message"] = "Document processed successfully"

    except Exception:
        tasks_db[task_id]["status"] = "FAILED"
        tasks_db[task_id]["message"] = "Document processing failed"


# 4. Upload endpoint (Q22-Q24, Q26-Q27)
@app.post("/upload", status_code=202)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Validate extension (Q23)
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file extension")

    # Generate unique IDs (Q27)
    file_id = str(uuid4())
    task_id = str(uuid4())

    # Generate safe filename (Q24)
    safe_filename = f"{file_id}{extension}"
    file_path = UPLOAD_DIR / safe_filename

    file_size = 0

    try:
        # Save file in chunks and enforce size limit
        with open(file_path, "wb") as buffer:

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File size exceeds 5 MB"
                    )

                buffer.write(chunk)

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file not allowed"
            )

    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise

    finally:
        await file.close()

    # Store file metadata (Q25)
    files_db[file_id] = {
        "file_id": file_id,
        "original_filename": file.filename,
        "stored_filename": safe_filename,
        "file_size": file_size,
        "extension": extension,
        "uploaded_at": datetime.now().isoformat()
    }

    # Create task status (Q28)
    tasks_db[task_id] = {
        "task_id": task_id,
        "file_id": file_id,
        "status": "PENDING",
        "message": "Task accepted"
    }

    # Run background task (Q26)
    background_tasks.add_task(
        process_document,
        task_id,
        file_id
    )

    return {
        "message": "File uploaded successfully",
        "file_id": file_id,
        "task_id": task_id,
        "status": "PENDING"
    }


# 5. List all uploaded files (Q25)
@app.get("/files")
def get_all_files():

    return list(files_db.values())


# 6. Get individual file metadata (Q25)
@app.get("/files/{file_id}")
def get_file_metadata(file_id: str):

    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")

    return files_db[file_id]


# 7. Download uploaded file
@app.get("/download/{file_id}")
def download_file(file_id: str):

    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")

    metadata = files_db[file_id]
    file_path = UPLOAD_DIR / metadata["stored_filename"]

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file not found")

    return FileResponse(
        path=file_path,
        filename=metadata["original_filename"]
    )


# 8. Check background task status (Q28-Q29)
@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):

    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    return tasks_db[task_id]


# 9. Home endpoint
@app.get("/")
def home():

    return {
        "message": "File Upload API is running"
    }
