# CarePoint Health — Healthcare Management System

A college-project prototype based on the supplied Healthcare Management System report. Built with Python Flask, SQLite, HTML, CSS and JavaScript.

## Features
- Patient self-registration and login
- Separate patient, doctor and administrator dashboards
- Patient appointment requests with basic doctor/time conflict checking
- Appointment status updates by the assigned doctor or administrator
- Medical report entry by doctor/admin and patient-specific report viewing
- Profile updates
- Password hashing and role-protected routes
- SQLite database initialized automatically

## Requirements
- Python 3.10 or newer
- VS Code (recommended)
- Internet connection only if you want Google Fonts to load

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `Healthcare-Management-System` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:
   ```powershell
   py -m venv venv
   ```
5. Activate it:
   ```powershell
   .\\venv\\Scripts\\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt and run:
   ```cmd
   venv\\Scripts\\activate.bat
   ```
6. Install packages:
   ```powershell
   pip install -r requirements.txt
   ```
7. Start the website:
   ```powershell
   python app.py
   ```
8. Open `http://127.0.0.1:5000` in your browser.

The SQLite database `healthcare.db` is created automatically on first run.

## Demo accounts
- Admin: `admin@healthcare.local` / `Admin@123`
- Doctor: `rahul@healthcare.local` / `Doctor@123`
- Doctor: `priya@healthcare.local` / `Doctor@123`
- Doctor: `amit@healthcare.local` / `Doctor@123`
- Patient: register a new account from the website.

Change demo passwords and the Flask secret key before any internet deployment.

## Deploying
This app can be deployed to a Python hosting service that supports Flask and persistent storage. Set:
- Build/install command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `SECRET_KEY` to a long random secret
- Environment variable: `DATABASE_PATH` to a persistent disk path if the host provides one.

**Important SQLite hosting note:** many free hosting services use temporary filesystems. If the host sleeps, restarts or redeploys, a SQLite database stored on the temporary filesystem may be erased. Use a persistent disk or migrate to a managed PostgreSQL database for reliable hosted data. Confirm the provider's current persistent-storage and pricing rules before deployment.

## Academic prototype safety
This is an educational demonstration, not a production hospital information system. Use only dummy/sample data. Do not enter real patient details, diagnoses, prescriptions, reports or other sensitive health information. Before real-world use, the system needs professional security review, HTTPS, stronger operational controls, audit logging, backups, privacy/legal review and a production database. It does not provide medical advice.

## Current scope / limitations
- Payment, pharmacy, laboratory integration, email/SMS alerts and video consultation are not implemented.
- Doctor availability is represented by a simple appointment-slot conflict check, not a full shift/calendar system.
- Admin can manage appointment status and create reports; a complete user/doctor CRUD management screen is future work.
