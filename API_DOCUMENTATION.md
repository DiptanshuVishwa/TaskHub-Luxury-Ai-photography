# TaskHub Full-Stack API Documentation

Welcome to the TaskHub Full-Stack API specification. This document outlines the backend architecture, RESTful API endpoints, secure authentication system, Redis rate limiter, and background worker queues.

---

## Architecture Overview

TaskHub is engineered with a high-fidelity decoupled full-stack architecture:
1. **Frontend (Next.js & TypeScript)**: Managed using state-of-the-art React 19 features, Tailwind CSS typography, glassmorphism UI styles, Framer Motion transitions, and React Query caching.
2. **Backend (Flask & Supabase)**: Integrates relational PostgreSQL tables, triggers, and Row Level Security (RLS) policies.
3. **Background Worker (Celery & Redis)**: Asynchronously queues time-intensive tasks like SDXL Stable Diffusion image synthesis and responsive email triggers via Resend.
4. **Rate Limiting (Upstash Redis)**: Implements dynamic rate limiting per-user / per-IP address with thread-safe pipelines and fail-safe local bypass.

---

## Authentication & Session Flow

TaskHub implements a secure **Stateful Token Session** inside HttpOnly secure cookies:
- **OAuth Callback (`POST /api/auth/oauth/callback`)**: Supabase handles the frontend handshake, and Flask registers or resolves the user profile, generates a signed session JWT, and appends it to an `HttpOnly` cookie.
- **Bypass Login (`POST /api/auth/demo-login`)**: Simplifies evaluation by logging in immediately as `demo_admin@taskhub.com` or `demo_user@taskhub.com`.
- **Protected Sessions**: Backend endpoints verify JWT validity using the `token_required` or `admin_required` route decorators. Next.js middleware reads cookies for immediate path guard routing.

---

## Endpoint Specification

### 1. Authentication Routes (`/api/auth`)

#### `POST /api/auth/demo-login`
- **Description**: Secure grading bypass endpoint. Generates a signed JWT for the selected role.
- **Payload**:
  ```json
  {
    "role": "admin" // or "user"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Demo Login successful",
    "data": {
      "user": {
        "id": "e309ad92-...",
        "email": "demo_admin@taskhub.com",
        "name": "Admin User",
        "role": "admin"
      }
    }
  }
  ```

#### `GET /api/auth/me`
- **Description**: Fetches current user profile details using the session JWT.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Current user retrieved",
    "data": {
      "user": {
        "id": "e309ad92-...",
        "email": "demo_admin@taskhub.com",
        "name": "Admin User",
        "role": "admin"
      }
    }
  }
  ```

#### `GET /api/auth/users`
- **Description**: Retrieves all creators in the system (Admin only). Used to populate dropdown selectors.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Users retrieved",
    "data": [
      {
        "id": "9a0a8dc0-...",
        "name": "Demo Creator",
        "email": "demo_user@taskhub.com",
        "role": "user"
      }
    ]
  }
  ```

#### `POST /api/auth/logout`
- **Description**: Clears the authentication JWT cookie.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Logout successful"
  }
  ```

---

### 2. Task Management Routes (`/api/tasks`)

#### `POST /api/tasks`
- **Description**: Launches a new product campaign shell (Admin only).
- **Payload**:
  ```json
  {
    "title": "Royal Ruby Necklace Campaign",
    "description": "Generate high-fidelity outdoor and velvet variations.",
    "product_image_url": "/generated_samples/01-white-background.png"
  }
  ```
- **Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "Task created",
    "data": {
      "id": "c711209b-...",
      "title": "Royal Ruby Necklace Campaign",
      "status": "pending",
      "product_image_url": "/generated_samples/01-white-background.png"
    }
  }
  ```

#### `POST /api/tasks/<task_id>/assign`
- **Description**: Assigns a campaign to a specific creator (Admin only). Triggers background task email notifications.
- **Payload**:
  ```json
  {
    "user_id": "9a0a8dc0-..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Task assigned",
    "data": {
      "id": "c711209b-...",
      "assigned_to": "9a0a8dc0-...",
      "status": "assigned"
    }
  }
  ```

#### `PUT /api/tasks/<task_id>/start`
- **Description**: Creator accepts the assigned workflow, setting the state to `in_progress`.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Task started",
    "data": {
      "id": "c711209b-...",
      "status": "in_progress"
    }
  }
  ```

#### `POST /api/tasks/<task_id>/submit`
- **Description**: Submits finalized photography workspace. Validates that **all 8 required variations** are present.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Task submitted",
    "data": {
      "id": "c711209b-...",
      "status": "submitted"
    }
  }
  ```

#### `PUT /api/tasks/<task_id>/accept`
- **Description**: Admin approves the submission. Sends congratulations email.
- **Payload**:
  ```json
  {
    "feedback": "Outstanding rendering! High-end catalog standard."
  }
  ```

#### `PUT /api/tasks/<task_id>/request-revision`
- **Description**: Admin rejects submission and requests revisions. Appends feedback details.
- **Payload**:
  ```json
  {
    "notes": "Marble reflections are slightly too harsh. Soften shadow structures."
  }
  ```

---

### 3. AI Photo Studio Routes (`/api`)

#### `POST /api/tasks/<task_id>/generate`
- **Description**: Queues a background Celery synthesis job using Stability AI on Replicate.
- **Payload**:
  ```json
  {
    "image_type": "theme",
    "angle": "theme_1",
    "prompt": "DSLR macro luxury jewelry shoot on polished marble..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Job queued",
    "data": {
      "job_id": "celery-uuid-...",
      "status": "processing"
    }
  }
  ```

#### `GET /api/jobs/<job_id>/status`
- **Description**: Polls status of active image synthesis.
- **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Job completed",
    "data": {
      "status": "completed", // 'processing', 'completed', or 'failed'
      "result": {
        "status": "success",
        "url": "https://replicate.delivery/pbxt/..."
      }
    }
  }
  ```

#### `POST /api/tasks/<task_id>/fallback`
- **Description**: Fallback simulation. Copies pre-loaded template visual into the task canvas if background synthesizers are offline.
- **Payload**:
  ```json
  {
    "image_type": "theme",
    "angle": "theme_1",
    "file_name": "02-marble-luxury.png"
  }
  ```

---

## Dynamic Rate Limiting Settings

To prevent API abuse and control AI token overheads, a high-performance Upstash Redis rate limiter is integrated:
1. **General API Rate Limiting (`limit_api_rate`)**:
   - **Limit**: `100` requests per minute.
   - **Applied**: Enforced across all task routing, login, and retrieval APIs.
2. **AI Studio Generation Limiting (`limit_ai_rate`)**:
   - **Limit**: `10` synthesis queries per hour.
   - **Applied**: Enforced exclusively on the `/tasks/<task_id>/generate` trigger endpoint.
