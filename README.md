# Coaching Portal Backend

Backend API for a **Coaching Portal** platform designed for Indian tutors teaching students from **Class 8 to 12**.

This project is built using **FastAPI**, **PostgreSQL**, and **SQLAlchemy** with a scalable backend architecture.

---

## Project Overview

The Coaching Portal helps manage online/offline coaching institutes with role-based access for different users.

### User Roles

- Tutor
- Teacher
- Parent
- Student

The system is designed to support coaching management features like:

- Authentication & Authorization
- Role Based Sidebar
- Student Management
- Attendance Management
- Assignment Management
- Parent Dashboard
- Profile Management
- Study Material Upload
- Notifications

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy ORM
- JWT Authentication
- Alembic Migration
- Pydantic Validation

### Database

- PostgreSQL

### Tools

- Postman
- Git & GitHub

---

## Project Architecture

The project follows clean backend architecture.



### Router Layer

Handles:

- API endpoints
- Request/Response
- Dependency Injection

### Service Layer

Handles:

- Business Logic
- Workflow Processing
- Data Transformation

### CRUD Layer

Handles:

- Database Queries
- Insert / Update / Delete / Select

### Schema Layer

Handles:

- Request Validation
- Response Formatting

---

## Features Completed

### Authentication Module

- User Registration
- Login API
- JWT Access Token
- Refresh Token API
- Logout API
- Forgot Password API
- OTP Verification
- Reset Password API

### Authorization Module

Role-based access control implemented for:

- Tutor
- Teacher
- Parent
- Student

### Sidebar Module (In Progress)

Dynamic sidebar system with:

- Role Based Menu Access
- Parent → Child Menu Structure
- Multiple Submenu Support

---

## Database Design

### Users Table

Stores:

- Full Name
- Username
- Email
- Password
- Role ID
- OTP Verification
- Profile Image
- Last Login

### Role Table

Stores system roles.

Example:

- Tutor
- Teacher
- Parent
- Student

### Menu Table

Stores sidebar menu structure.

Example:

- Dashboard
- Student Management
- Assignment
- Attendance

Supports nested menus using:

- parent_id

### Role Menu Table

Maps roles to menus.

Example:

Tutor → Dashboard  
Teacher → Attendance  
Student → Assignment

---

## Authentication Flow



---

## API Modules

### Auth APIs

- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- POST /auth/forgot-password
- POST /auth/verify-otp
- POST /auth/reset-password

### Sidebar APIs

- GET /sidebar/

---

## Future Modules

- Attendance Module
- Assignment Module
- Student Dashboard
- Parent Dashboard
- Teacher Dashboard
- Study Material Upload
- Live Class Scheduling
- Notification System

---

## Developer

Rahul Kashyap

Backend Developer | Python | FastAPI | PostgreSQL | React | Next.js



