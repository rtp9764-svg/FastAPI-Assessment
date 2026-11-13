# FastAPI Assessment

A FastAPI assessment project with student and employee examples and a file
upload/processing API.

> **Current entry point:** `main2.py` defines multiple FastAPI applications in
sequence. The final `app` assignment is the File Upload and Processing API,
which is the application served by the command below. Earlier student and
authentication examples in the file are not mounted in that application.

## Requirements

- Python 3.10 or newer
- pip

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/rtp9764-svg/FastAPI-Assessment.git
cd FastAPI-Assessment
```

Create and activate a virtual environment.

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the packages used by `main2.py`:

```bash
python -m pip install --upgrade pip
python -m pip install "fastapi" "uvicorn[standard]" "python-multipart" "PyJWT" "pwdlib[argon2]" "email-validator"
```

## Run the API

From the repository directory, start the development server:

```bash
python -m uvicorn main2:app --reload
```

The API is available at <http://127.0.0.1:8000>. Interactive API documentation
is available at <http://127.0.0.1:8000/docs>.

The upload API accepts files at `POST /upload` and provides endpoints to list
files, download a file, and check its processing status. Uploaded files are
written to the `uploads/` directory. File/task metadata is held in memory and
is cleared when the server restarts.

This is assessment/demo code; review it before using it in a production
environment.
