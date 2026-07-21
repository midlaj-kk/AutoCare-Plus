# AutoCare Pro
## System Design, Architecture & Implementation Guide
### Car Service Center Management App — Backend Engineering Blueprint

**Stack:** Flutter (frontend) · Python + Django REST Framework (backend) · PostgreSQL / NeonDB (database)
**Deployment target:** $0/month, using free-tier cloud services
**Document version:** 1.0 — June 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack Justification](#3-technology-stack-justification)
4. [Database Design (ERD + Schema)](#4-database-design-erd--schema)
5. [Django Project Structure](#5-django-project-structure)
6. [Authentication & RBAC Design](#6-authentication--rbac-design)
7. [API Design (Full Endpoint Reference)](#7-api-design-full-endpoint-reference)
8. [Business Logic & State Machines](#8-business-logic--state-machines)
9. [Validation & Error Handling Standards](#9-validation--error-handling-standards)
10. [Zero-Cost Deployment Architecture](#10-zero-cost-deployment-architecture)
11. [Step-by-Step Deployment Guide](#11-step-by-step-deployment-guide)
12. [Flutter Integration Guide](#12-flutter-integration-guide)
13. [Development Roadmap (Phased Implementation Plan)](#13-development-roadmap-phased-implementation-plan)
14. [Security Checklist](#14-security-checklist)
15. [Scaling Beyond Free Tier](#15-scaling-beyond-free-tier)
16. [Appendix: Environment Variables & Config Files](#16-appendix-environment-variables--config-files)

---

## 1. Project Overview

**AutoCare Pro** is a multi-role car service center management system. A Flutter mobile app is used by four kinds of staff — Admin, Service Advisor, Mechanic, Cashier — to move a vehicle through its entire service lifecycle: intake, job creation, mechanic assignment, repair work, parts consumption, quality check, billing, payment, and delivery, with full service history retained for future visits.

This document is the **backend engineering blueprint**: it defines the system architecture, database schema, API contracts, role permissions, business rules, and a complete path to a live, **zero-cost** production deployment.

### 1.1 Core Design Principles

| Principle | Why it matters here |
|---|---|
| **Single source of truth** | The Service Job is the central object every other module (work, parts, QC, bill, payment, delivery) attaches to. |
| **Status-driven workflow** | The vehicle's journey is modeled as a finite state machine on `ServiceJob.status`. No module mutates another module's data directly — they react to status transitions. |
| **Soft delete everywhere** | Real-world businesses can't lose financial/audit history. Nothing with historical references is ever hard-deleted — see [Section 8.5](#85-soft-delete--inactive-status-engine). |
| **Stock integrity** | Spare parts stock changes must be atomic and reversible (deleting a "parts used" entry must restore stock). |
| **Role isolation at the query level**, not just the UI level | A Mechanic's API calls are filtered server-side to their own assigned jobs — never trust the Flutter client to hide data correctly. |
| **Free-tier-first infrastructure** | Every architectural choice in Section 10 is made to fit inside free-tier limits of Render + NeonDB without locking you out of a serious production app later. |

### 1.2 Actors & Their One-Line Job

- **Admin** — owns everything: users, masters (customers/vehicles/parts/mechanics), reports, full CRUD.
- **Service Advisor** — front desk: registers customers/vehicles, opens service jobs, assigns mechanics.
- **Mechanic** — workshop floor: sees only their assigned vehicles, logs work and parts used.
- **Cashier** — back office: bills, payments, invoices, hands the vehicle back to the customer.

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│   Flutter App (Android / iOS / Web)                              │
│   - Role-based UI (Admin / Advisor / Mechanic / Cashier)          │
│   - Secure token storage (flutter_secure_storage)                │
│   - Dio/Retrofit HTTP client with JWT interceptor                 │
└───────────────────────────┬────────────────────────────────────-─┘
                            │ HTTPS (JSON over REST)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER (Render)                   │
│   Django + Django REST Framework, served by Gunicorn             │
│                                                                    │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│   │   Auth     │  │   Users &  │  │  Customers │  │  Vehicles  │ │
│   │  (JWT)     │  │  Mechanics │  │            │  │            │ │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│   │   Spare    │  │  Service   │  │  Service   │  │  Quality   │ │
│   │   Parts    │  │   Jobs     │  │   Work     │  │   Check    │ │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│   │  Billing   │  │  Payments  │  │  Delivery  │  │  Reports / │ │
│   │            │  │            │  │            │  │  Dashboard │ │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘ │
│                                                                    │
│   Middleware: JWT Auth · RBAC Permission Classes · Exception      │
│   Handler · Request Logging · CORS                                │
└───────────────────────────┬───────────────────────────────────────┘
                            │ psycopg2 / SSL connection
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       DATA LAYER (NeonDB)                        │
│   PostgreSQL (Serverless, autoscaling, scale-to-zero)             │
│   - Connection pooling via PgBouncer (Neon built-in)              │
└──────────────────────────────────────────────────────────────────┘

   Supporting (optional, still $0):
   ┌────────────────┐   ┌────────────────────┐   ┌──────────────┐
   │ Cloudinary      │   │ UptimeRobot /       │   │ GitHub        │
   │ (vehicle/QC      │   │ cron-job.org         │   │ Actions       │
   │ photos, if added)│   │ (keep-alive pings)    │   │ (CI/CD)       │
   └────────────────┘   └────────────────────┘   └──────────────┘
```

### 2.2 Request Lifecycle (example: Mechanic marks work complete)

```
Flutter App                Django/DRF                      PostgreSQL
    │                           │                                │
    │  PATCH /api/service-work/ │                                │
    │  {id}/  {status:"completed"}                                │
    │  Header: Authorization: Bearer <JWT>                        │
    ├──────────────────────────►│                                │
    │                           │ 1. JWTAuthentication middleware │
    │                           │    decodes token → request.user│
    │                           │ 2. IsMechanic permission class  │
    │                           │    checks request.user.role     │
    │                           │ 3. Queryset filtered to jobs     │
    │                           │    assigned to this mechanic    │
    │                           │ 4. Serializer validates payload  │
    │                           │ 5. Business rule: if this was    │
    │                           │    last pending work → check     │
    │                           │    if job ready for QC           │
    │                           ├───────────────────────────────► │
    │                           │     UPDATE service_work SET...   │
    │                           │ ◄─────────────────────────────── │
    │  200 OK + updated object  │                                │
    │◄──────────────────────────┤                                │
```

### 2.3 Layered Application Architecture (inside Django)

AutoCare Pro uses a **4-layer separation** inside each Django app, so business logic never leaks into views and is unit-testable in isolation:

```
View/APIview  →  Serializer  →  Service Layer (business logic)  →  Model/QuerySet
   (HTTP)         (validation)      (rules, transactions)              (DB)
```

- **Views/APIview**: only handle HTTP concerns — parsing requests, calling the service layer, returning responses.
- **Serializers**: field-level validation (data shape, types, required fields).
- **Service layer** (`services.py` per app): cross-model business rules — e.g. "reduce stock when parts are used," "cascade status when QC is approved." This is where all the rules from Sections 13–24 of your requirement doc live in code.
- **Models**: schema, relationships, and simple model-level validators only.

This matters specifically for AutoCare Pro because almost every module in your spec ("if X then status becomes Y," "don't delete, deactivate instead") is a cross-model rule — exactly what the service layer is for.

---

## 3. Technology Stack Justification

| Layer | Choice | Why |
|---|---|---|
| Backend framework | **Django 5 + DRF** | Batteries-included (admin panel, ORM, auth) drastically cuts solo-dev build time; DRF's serializers/viewsets map cleanly to your CRUD-heavy spec. |
| Auth | **`djangorestframework-simplejwt`** | Standard JWT library for DRF — access/refresh tokens, blacklist support for logout, drop-in `IsAuthenticated`-style permissions. |
| Database | **PostgreSQL via NeonDB** | Free, serverless, real production-grade Postgres (not SQLite) from day one — avoids a painful SQLite→Postgres migration later. Branching feature is genuinely useful for testing migrations safely. |
| ORM | Django ORM | Native, no extra dependency, perfect fit with Django. |
| API docs | **drf-spectacular** | Auto-generates OpenAPI 3 schema + Swagger UI directly from your viewsets/serializers — meets your "API Documentation" requirement with near-zero manual work. |
| Hosting | **Render (free web service)** | Native Python/Django buildpack support, free TLS, auto-deploy from GitHub, no credit card needed for the free instance type. |
| Media storage (optional) | **Cloudinary free tier** | If you later add vehicle/QC photos — Render's free disk is ephemeral (wiped on redeploy), so you cannot store uploaded files on Render itself. |
| CI/CD | **GitHub Actions (free for public + generous free minutes for private repos)** | Run tests + auto-deploy on push to `main`. |
| Mobile HTTP client | **Dio** (Flutter) | Interceptor support for attaching/refreshing JWTs automatically — cleaner than the raw `http` package for this use case. |

> **A note on "Option 1 vs Option 3" from your original doc:** You listed Node/Express/Mongo as the "recommended" stack for easy Flutter integration. That recommendation doesn't actually hold once you account for your own requirements — your spec is heavily **relational** (customers → vehicles → service jobs → work → parts → bills → payments, with strict referential and status rules). PostgreSQL with foreign keys and DB-level constraints is a much more natural fit than MongoDB's document model for this exact data shape, and Django's ORM + admin panel will save you significant backend dev time as a Flutter-only developer. This document proceeds with **Django + DRF + PostgreSQL** as specified in your message.

---

## 4. Database Design (ERD + Schema)

### 4.1 Entity Relationship Diagram (text form)

```
User (1) ──────────────< (M) ServiceJob [assigned_mechanic_id]
  │                            │
  │                            │
  │  (1)                       │ (1)
  │                            ▼
  │                       ┌──────────┐
  │                       │ Vehicle  │──< (M) ServiceJob
  │                       └────┬─────┘
  │                            │ (M)
  │                            ▼
  │                       ┌──────────┐
  │                       │ Customer │
  │                       └──────────┘
  │
  └──< StockMovement (created_by)

ServiceJob (1) ──< (M) ServiceWork
ServiceJob (1) ──< (M) PartUsed >── (M) SparePart
ServiceJob (1) ──< (0..1) QualityCheck
ServiceJob (1) ──< (0..1) Bill ──< (M) Payment
ServiceJob (1) ──< (0..1) Delivery

SparePart (1) ──< (M) StockMovement
SparePart (1) ──< (M) PartUsed
```

### 4.2 Table-by-Table Schema

> Every table includes `created_at`, `updated_at` (auto-managed). PKs are `id BIGSERIAL` unless noted. All money fields use `DECIMAL(10,2)` — **never** `FLOAT`, to avoid rounding errors in billing.

#### `users`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(150) | NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| phone | VARCHAR(15) | NOT NULL |
| password | VARCHAR(255) | NOT NULL (hashed) |
| role | VARCHAR(20) | NOT NULL, CHECK IN ('admin','service_advisor','mechanic','cashier') |
| specialization | VARCHAR(100) | NULL (mechanics only) |
| status | VARCHAR(10) | DEFAULT 'active', CHECK IN ('active','inactive') |
| created_at, updated_at | TIMESTAMP | auto |

#### `customers`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(150) | NOT NULL |
| phone | VARCHAR(15) | NOT NULL, INDEX |
| email | VARCHAR(255) | NULL |
| address | TEXT | NULL |
| status | VARCHAR(10) | DEFAULT 'active', CHECK IN ('active','inactive') |
| created_at, updated_at | TIMESTAMP | auto |

#### `vehicles`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| customer_id | BIGINT | FK → customers.id, NOT NULL |
| vehicle_number | VARCHAR(20) | UNIQUE, NOT NULL, INDEX |
| brand | VARCHAR(50) | NOT NULL |
| model | VARCHAR(50) | NOT NULL |
| year | SMALLINT | NULL |
| kilometers | INTEGER | DEFAULT 0 |
| status | VARCHAR(10) | DEFAULT 'active', CHECK IN ('active','inactive') |
| created_at, updated_at | TIMESTAMP | auto |

#### `spare_parts`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| name | VARCHAR(150) | NOT NULL |
| part_number | VARCHAR(50) | UNIQUE, NOT NULL |
| stock_quantity | DECIMAL(10,2) | DEFAULT 0, CHECK >= 0 |
| unit | VARCHAR(20) | NOT NULL (e.g. litre, piece, kg) |
| purchase_price | DECIMAL(10,2) | NOT NULL |
| selling_price | DECIMAL(10,2) | NOT NULL |
| minimum_stock | DECIMAL(10,2) | DEFAULT 0 |
| status | VARCHAR(10) | DEFAULT 'active', CHECK IN ('active','inactive') |
| created_at, updated_at | TIMESTAMP | auto |

#### `stock_movements` *(new table — needed to satisfy "View Stock History")*
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| spare_part_id | BIGINT | FK → spare_parts.id |
| movement_type | VARCHAR(10) | CHECK IN ('in','out') |
| quantity | DECIMAL(10,2) | NOT NULL |
| reference_type | VARCHAR(20) | e.g. 'purchase', 'service_job', 'adjustment' |
| reference_id | BIGINT | NULL — e.g. the service_job_id if type='service_job' |
| created_by | BIGINT | FK → users.id |
| created_at | TIMESTAMP | auto |

#### `service_jobs`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| job_number | VARCHAR(20) | UNIQUE, auto-generated (e.g. `SJ-2026-00001`) |
| vehicle_id | BIGINT | FK → vehicles.id, NOT NULL |
| complaint | TEXT | NOT NULL |
| service_type | VARCHAR(50) | NOT NULL |
| assigned_mechanic_id | BIGINT | FK → users.id, NULL (assigned later) |
| created_by | BIGINT | FK → users.id (the advisor) |
| status | VARCHAR(20) | DEFAULT 'waiting' — see [state machine](#81-service-job-state-machine) |
| odometer_reading | INTEGER | NULL |
| created_at, updated_at | TIMESTAMP | auto |

#### `service_works`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| service_job_id | BIGINT | FK → service_jobs.id, NOT NULL |
| work_name | VARCHAR(150) | NOT NULL |
| description | TEXT | NULL |
| status | VARCHAR(15) | DEFAULT 'pending', CHECK IN ('pending','in_progress','completed') |
| labour_charge | DECIMAL(10,2) | DEFAULT 0 |
| created_by | BIGINT | FK → users.id (mechanic) |
| created_at, updated_at | TIMESTAMP | auto |

#### `parts_used`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| service_job_id | BIGINT | FK → service_jobs.id, NOT NULL |
| part_id | BIGINT | FK → spare_parts.id, NOT NULL |
| quantity | DECIMAL(10,2) | NOT NULL, CHECK > 0 |
| price | DECIMAL(10,2) | NOT NULL — snapshot of selling_price at time of use |
| added_by | BIGINT | FK → users.id |
| created_at, updated_at | TIMESTAMP | auto |

> **Why snapshot `price`?** If you later change a spare part's `selling_price`, old bills must NOT change retroactively. Always copy price-at-time-of-transaction into the transactional row.

#### `quality_checks`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| service_job_id | BIGINT | FK → service_jobs.id, UNIQUE, NOT NULL |
| brake_check | VARCHAR(15) | CHECK IN ('passed','failed','na') |
| engine_check | VARCHAR(15) | CHECK IN ('passed','failed','na') |
| oil_leakage_check | VARCHAR(15) | CHECK IN ('no_issue','issue_found','na') |
| ac_check | VARCHAR(15) | CHECK IN ('passed','failed','na') |
| tyre_check | VARCHAR(15) | CHECK IN ('passed','failed','na') |
| test_drive | VARCHAR(15) | CHECK IN ('passed','failed','na') |
| overall_status | VARCHAR(20) | CHECK IN ('approved','rework_required') |
| remarks | TEXT | NULL |
| checked_by | BIGINT | FK → users.id |
| created_at, updated_at | TIMESTAMP | auto |

#### `bills`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| invoice_number | VARCHAR(20) | UNIQUE, auto-generated (e.g. `INV-2026-00001`) |
| service_job_id | BIGINT | FK → service_jobs.id, UNIQUE, NOT NULL |
| labour_charge | DECIMAL(10,2) | NOT NULL |
| parts_charge | DECIMAL(10,2) | NOT NULL |
| tax | DECIMAL(10,2) | DEFAULT 0 |
| discount | DECIMAL(10,2) | DEFAULT 0 |
| total_amount | DECIMAL(10,2) | NOT NULL |
| payment_status | VARCHAR(10) | DEFAULT 'pending', CHECK IN ('pending','paid','partial') |
| created_by | BIGINT | FK → users.id (cashier) |
| created_at, updated_at | TIMESTAMP | auto |

#### `payments`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| bill_id | BIGINT | FK → bills.id, NOT NULL |
| payment_method | VARCHAR(20) | CHECK IN ('cash','upi','card','bank_transfer') |
| paid_amount | DECIMAL(10,2) | NOT NULL, CHECK > 0 |
| payment_date | DATE | NOT NULL |
| received_by | BIGINT | FK → users.id |
| created_at | TIMESTAMP | auto |

> A bill can have **multiple** payment rows (to support `partial` status — e.g. ₹2000 today, ₹3484 next week). `bills.payment_status` is recalculated from `SUM(payments.paid_amount)` vs `bills.total_amount` every time a payment is added.

#### `deliveries`
| Column | Type | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| service_job_id | BIGINT | FK → service_jobs.id, UNIQUE, NOT NULL |
| delivered_by | BIGINT | FK → users.id |
| delivery_date | TIMESTAMP | NOT NULL |
| customer_received | BOOLEAN | DEFAULT false |
| remarks | TEXT | NULL |
| created_at | TIMESTAMP | auto |

### 4.3 Key Design Decisions Explained

1. **`job_number` and `invoice_number` are human-readable sequential codes**, generated server-side (e.g. via a `Sequence` model or Postgres sequence + format string), separate from the internal `id` PK. Mechanics, cashiers and customers reference `SJ-2026-00001` / `INV-2026-00001`, not raw DB IDs.
2. **One-to-one tables (`quality_checks`, `bills`, `deliveries`) use a UNIQUE FK** to `service_jobs.id` rather than a shared PK, keeping Django's default model style intact while enforcing "one QC / one bill / one delivery per job" at the DB level.
3. **No hard FK `ON DELETE CASCADE` anywhere that touches money or history.** Every relevant FK uses `ON DELETE PROTECT` (Django: `on_delete=models.PROTECT`) so the DB itself refuses to let you delete a customer/vehicle/part that has dependent rows — backing up the "soft delete" business rule with a hard database guarantee, not just application code.
4. **`stock_movements` is an addition beyond your original spec** — your doc asked for "View Stock History" but didn't define its schema. Without a movements ledger, you cannot show a history of additions/reductions, only the current `stock_quantity`. This table is the audit trail.

---

## 5. Django Project Structure

A clean, modular folder layout — one Django **app** per business domain, mirroring the tables in Section 4. This satisfies your "Clean Folder Structure" requirement directly.

```
autocare_backend/
├── manage.py
├── requirements.txt
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env
├── .env.example
├── .gitignore
├── render.yaml
├── Procfile
├── runtime.txt
│
├── config/                              # Project configuration
│   ├── __init__.py
│   │
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                       # Common settings for all environments
│   │   ├── dev.py                        # Local development settings
│   │   └── prod.py                       # Production / Render settings
│   │
│   ├── urls.py                           # Main URL router
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                                 # All business modules stay here
│   ├── __init__.py
│   │
│   ├── accounts/                         # User, login, JWT, roles
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Custom User model
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── services.py
│   │   ├── selectors.py                  # Read/query logic
│   │   ├── tests.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── customers/                        # Customer details
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── vehicles/                         # Customer vehicles
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── mechanics/                        # Mechanic-specific APIs
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── inventory/                        # Spare parts and stock
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # SparePart, StockMovement
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py                   # Add stock, reduce stock
│   │   ├── selectors.py                  # Low stock queries
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── service_jobs/                     # Main service workflow
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # ServiceJob
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── services.py                   # Job status transitions
│   │   ├── selectors.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── service_work/                     # Work done by mechanic
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # ServiceWork
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── parts_used/                       # Parts consumed for a service job
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # PartUsed
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py                   # Calls inventory stock reduction
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── quality_check/                    # Final QC
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # QualityCheck
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── billing/                          # Bill generation
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Bill
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py                   # Calculate total bill
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── payments/                         # Payment records
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Payment
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── delivery/                         # Vehicle delivery details
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                     # Delivery
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── service_history/                  # Read-only service history
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── selectors.py
│   │
│   ├── dashboard/                        # Dashboard summary APIs
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── selectors.py
│   │
│   └── reports/                          # Sales, stock, mechanic reports
│       ├── __init__.py
│       ├── apps.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── services.py
│       └── selectors.py
│
├── core/                                 # Shared code used by all apps
│   ├── __init__.py
│   ├── models.py                         # TimeStampedModel abstract model
│   ├── permissions.py                    # IsAdmin, IsMechanic, IsCashier
│   ├── exceptions.py                     # Custom DRF exception handler
│   ├── pagination.py                     # StandardResultsPagination
│   ├── responses.py                      # Success/error response helpers
│   ├── constants.py                      # Global constants
│   ├── validators.py                     # Shared validators
│   └── utils.py                          # Helper functions
│
├── tests/                                # Project-level integration tests
│   ├── __init__.py
│   ├── factories.py
│   ├── test_auth.py
│   ├── test_permissions.py
│   ├── test_service_job_flow.py
│   └── test_stock_integrity.py
│
├── static/
├── media/
│
└── docs/
    ├── api_documentation.md
    ├── database_schema.md
    ├── deployment_guide.md
    └── project_flow.md
```

**Why this structure works well for a solo/Flutter-background developer:**
- Each folder maps 1:1 to a section of your original requirement doc — when you re-read Section 14 ("Billing Module") you go straight to `billing/`.
- `services.py` files are where you put the "if X then Y" rules. Views stay tiny and dumb on purpose.
- `core/permissions.py` centralizes the 4-role logic once, instead of repeating role checks in every view.

---

## 6. Authentication & RBAC Design

### 6.1 Custom User Model

Django's default `User` model has no `role` or `phone` field, and swapping the user model **must** be done before the first migration. Define a custom model immediately:

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SERVICE_ADVISOR = "service_advisor", "Service Advisor"
        MECHANIC = "mechanic", "Mechanic"
        CASHIER = "cashier", "Cashier"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=20, choices=Role.choices)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # keep username for Django admin compatibility
```

```python
# config/settings/base.py
AUTH_USER_MODEL = "accounts.User"
```

### 6.2 JWT Authentication Flow

```
┌─────────┐   POST /api/auth/login/   ┌──────────────┐
│ Flutter │ ─────────────────────────►│ TokenObtain   │
│  App    │   {email, password}       │ PairView      │
│         │◄───────────────────────── │ (simplejwt)   │
└─────────┘  {access, refresh, user}  └──────────────┘
     │
     │  Store access (short-lived, 15-30 min)
     │  Store refresh (long-lived, 7 days) in flutter_secure_storage
     │
     │  Every API call:
     │  Authorization: Bearer <access_token>
     │
     │  On 401 (access expired):
     │  POST /api/auth/refresh/ {refresh} → new access token
     │  (Dio interceptor handles this automatically — Section 12)
     │
     │  Logout:
     │  POST /api/auth/logout/ {refresh} → blacklists the refresh token
     ▼
```

**Settings:**

```python
# config/settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}
```

Add `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` so logout actually invalidates tokens server-side (without it, a "logged out" refresh token still works until it expires).

### 6.3 Role-Based Permission Classes

```python
# core/permissions.py
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"

class IsServiceAdvisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin", "service_advisor"
        )

class IsMechanic(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "mechanic"

class IsCashier(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "admin", "cashier"
        )

class IsAdminOrReadOnly(BasePermission):
    """Service Advisor can read+create, only Admin can edit/delete."""
    def has_permission(self, request, view):
        if request.method in ("GET", "POST"):
            return request.user.role in ("admin", "service_advisor")
        return request.user.role == "admin"
```

Apply per-viewset, e.g.:

```python
# service_jobs/views.py
class ServiceJobViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceJobSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdmin()]
        if self.action in ("create", "assign_mechanic"):
            return [IsServiceAdvisor()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = ServiceJob.objects.select_related("vehicle", "assigned_mechanic")
        if user.role == "mechanic":
            return qs.filter(assigned_mechanic=user)        # ← row-level isolation
        return qs
```

> **This `get_queryset` override is the single most important security pattern in the whole backend.** A Mechanic must never be able to fetch another mechanic's job by simply guessing an ID in the URL (`GET /api/service-jobs/47/`). Filtering at the queryset level — not just hiding the button in Flutter — closes that hole.

### 6.4 Permission Matrix (authoritative reference)

| Module | Admin | Service Advisor | Mechanic | Cashier |
|---|:---:|:---:|:---:|:---:|
| Users | CRUD | – | – | – |
| Customers | CRUD | Create, Read, Update | Read (own jobs' customer) | Read |
| Vehicles | CRUD | Create, Read, Update | Read (own jobs' vehicle) | Read |
| Mechanics | CRUD | Read | Read (self) | – |
| Spare Parts | CRUD | Read | Read | Read |
| Stock | Update | – | – | – |
| Service Jobs | CRUD, Assign | Create, Read, Update, Assign | Read (own), Update status | Read |
| Service Work | Read | Read | CRUD (own jobs) | Read |
| Parts Used | Read | Read | CRUD (own jobs) | Read |
| Quality Check | Read | Read | – | Read |
| QC: who performs it | Admin or a designated QC role* | – | – | – |
| Bills | Read | Read | – | Create, Read, Update |
| Payments | Read | – | – | CRUD |
| Delivery | Read | – | – | CRUD |
| Reports | Full | – | – | – |
| Dashboard | Full | Limited (own-shift counts) | Limited (own jobs) | Limited (today's billing) |

*\* Your original spec doesn't name who performs Quality Check. Section 8.2 proposes Admin or Service Advisor by default, with a configurable `QC_PERFORMER_ROLES` setting — flag if you want a dedicated QC role instead.*

---

## 7. API Design (Full Endpoint Reference)

**Conventions used throughout:**
- Base URL: `/api/v1/`
- All list endpoints support `?page=`, `?page_size=`, `?search=`, `?ordering=`, and module-specific `?status=` filters.
- All responses follow the standard envelope in [Section 9.1](#91-standard-response-envelope).
- 🔒 marks the minimum role required (Admin always implicitly included unless marked Admin-only).

### 7.1 Authentication

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/auth/login/` | Login, returns access+refresh+user | Public |
| POST | `/api/v1/auth/refresh/` | Refresh access token | Authenticated |
| POST | `/api/v1/auth/logout/` | Blacklist refresh token | Authenticated |
| POST | `/api/v1/auth/change-password/` | Change own password | Authenticated |
| POST | `/api/v1/auth/forgot-password/` | Send reset OTP/link (optional) | Public |
| POST | `/api/v1/auth/reset-password/` | Reset via OTP/token (optional) | Public |
| GET | `/api/v1/auth/me/` | Get current logged-in user profile | Authenticated |

### 7.2 User Management

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/users/` | Add user | Admin |
| GET | `/api/v1/users/` | List users (filter by `?role=`, `?status=`) | Admin |
| GET | `/api/v1/users/{id}/` | Get single user | Admin |
| PUT/PATCH | `/api/v1/users/{id}/` | Update user | Admin |
| DELETE | `/api/v1/users/{id}/` | Delete (soft, see Section 8.5) | Admin |
| PATCH | `/api/v1/users/{id}/role/` | Change user role | Admin |
| PATCH | `/api/v1/users/{id}/activate/` | Activate | Admin |
| PATCH | `/api/v1/users/{id}/deactivate/` | Deactivate | Admin |
| POST | `/api/v1/users/{id}/reset-password/` | Admin resets a user's password | Admin |

### 7.3 Customers

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/customers/` | Add customer | Advisor+ |
| GET | `/api/v1/customers/` | List (`?search=` matches name/phone) | Advisor+ |
| GET | `/api/v1/customers/{id}/` | Get single customer | Advisor+ |
| PUT/PATCH | `/api/v1/customers/{id}/` | Update customer | Advisor+ |
| DELETE | `/api/v1/customers/{id}/` | Delete (soft) | Admin |
| GET | `/api/v1/customers/?search={name}` | Search by name | Advisor+ |
| GET | `/api/v1/customers/?phone={phone}` | Search by phone | Advisor+ |
| GET | `/api/v1/customers/{id}/vehicles/` | Get customer's vehicles | Advisor+ |
| GET | `/api/v1/customers/{id}/service-history/` | Get full service history | Advisor+ |

### 7.4 Vehicles

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/vehicles/` | Add vehicle | Advisor+ |
| GET | `/api/v1/vehicles/` | List vehicles | Advisor+ |
| GET | `/api/v1/vehicles/{id}/` | Get single vehicle | Advisor+ |
| PUT/PATCH | `/api/v1/vehicles/{id}/` | Update vehicle | Advisor+ |
| DELETE | `/api/v1/vehicles/{id}/` | Delete (soft) | Admin |
| GET | `/api/v1/vehicles/?search={vehicle_number}` | Search by number | Advisor+ |
| GET | `/api/v1/vehicles/?customer_id={id}` | Vehicles by customer | Advisor+ |
| GET | `/api/v1/vehicles/{id}/service-history/` | Full service history for this vehicle | Advisor+ |

### 7.5 Mechanics (built on the `users` table, `role=mechanic`)

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/mechanics/` | Add mechanic (creates a User) | Admin |
| GET | `/api/v1/mechanics/` | List all mechanics | Admin/Advisor |
| PUT/PATCH | `/api/v1/mechanics/{id}/` | Edit mechanic | Admin |
| DELETE | `/api/v1/mechanics/{id}/` | Delete (with reassignment guard, 8.5) | Admin |
| PATCH | `/api/v1/mechanics/{id}/activate/` | Activate | Admin |
| PATCH | `/api/v1/mechanics/{id}/deactivate/` | Deactivate | Admin |
| GET | `/api/v1/mechanics/{id}/assigned-vehicles/` | Vehicles currently assigned | Admin/Advisor/Self |
| GET | `/api/v1/mechanics/{id}/productivity/` | Jobs completed, avg time, etc. | Admin |

### 7.6 Spare Parts & Inventory

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/spare-parts/` | Add spare part | Admin |
| GET | `/api/v1/spare-parts/` | List (`?search=`, `?status=`) | All authenticated |
| GET | `/api/v1/spare-parts/{id}/` | Get single part | All authenticated |
| PUT/PATCH | `/api/v1/spare-parts/{id}/` | Edit part | Admin |
| DELETE | `/api/v1/spare-parts/{id}/` | Delete (soft) | Admin |
| POST | `/api/v1/spare-parts/{id}/add-stock/` | Add new stock (purchase) | Admin |
| POST | `/api/v1/spare-parts/{id}/reduce-stock/` | Manual stock reduction/adjustment | Admin |
| GET | `/api/v1/spare-parts/{id}/stock-history/` | Movement ledger for this part | Admin |
| GET | `/api/v1/spare-parts/low-stock/` | All parts at/below minimum_stock | Admin |

### 7.7 Service Jobs

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/service-jobs/` | Create job | Advisor+ |
| GET | `/api/v1/service-jobs/` | List (`?status=`, `?mechanic_id=`) | Role-filtered (6.3) |
| GET | `/api/v1/service-jobs/{id}/` | Get single job (full nested detail) | Role-filtered |
| PUT/PATCH | `/api/v1/service-jobs/{id}/` | Update job | Advisor+ |
| DELETE | `/api/v1/service-jobs/{id}/` | Cancel (never hard-delete, see 8.5) | Admin |
| PATCH | `/api/v1/service-jobs/{id}/assign-mechanic/` | Assign mechanic | Advisor+ |
| PATCH | `/api/v1/service-jobs/{id}/change-mechanic/` | Re-assign | Advisor+ |
| PATCH | `/api/v1/service-jobs/{id}/status/` | Manual status update (validated transitions) | Role-dependent |
| GET | `/api/v1/service-jobs/?mechanic_id={id}` | Jobs by mechanic | Admin/Advisor |
| GET | `/api/v1/service-jobs/?status={status}` | Jobs by status | Role-filtered |
| GET | `/api/v1/service-jobs/?vehicle_number={no}` | Search by vehicle number | Advisor+ |

### 7.8 Service Work

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/service-jobs/{job_id}/works/` | Add service work | Mechanic (own job) |
| GET | `/api/v1/service-jobs/{job_id}/works/` | List works for a job | Role-filtered |
| PUT/PATCH | `/api/v1/works/{id}/` | Update work | Mechanic (own job) |
| DELETE | `/api/v1/works/{id}/` | Delete work | Mechanic (own job)/Admin |
| PATCH | `/api/v1/works/{id}/status/` | Update work status | Mechanic (own job) |

### 7.9 Parts Used

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/service-jobs/{job_id}/parts-used/` | Add used part (auto stock reduce) | Mechanic (own job) |
| GET | `/api/v1/service-jobs/{job_id}/parts-used/` | List parts used for a job | Role-filtered |
| PUT/PATCH | `/api/v1/parts-used/{id}/` | Update quantity (adjusts stock delta) | Mechanic (own job)/Admin |
| DELETE | `/api/v1/parts-used/{id}/` | Delete (auto stock restore) | Mechanic (own job)/Admin |

### 7.10 Quality Check

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/service-jobs/{job_id}/quality-check/` | Add QC record | Admin/Advisor |
| GET | `/api/v1/service-jobs/{job_id}/quality-check/` | Get QC for a job | Role-filtered |
| PUT/PATCH | `/api/v1/quality-checks/{id}/` | Update QC | Admin/Advisor |
| PATCH | `/api/v1/quality-checks/{id}/approve/` | Approve → job becomes `ready_for_bill` | Admin/Advisor |
| PATCH | `/api/v1/quality-checks/{id}/send-for-rework/` | Reject → job becomes `rework_required` | Admin/Advisor |

### 7.11 Billing

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/service-jobs/{job_id}/bill/` | Create bill (only if QC approved) | Cashier |
| GET | `/api/v1/bills/` | List all bills (`?payment_status=`) | Cashier/Admin |
| GET | `/api/v1/bills/{id}/` | Get single bill | Cashier/Admin |
| GET | `/api/v1/service-jobs/{job_id}/bill/` | Get bill by job | Cashier/Admin |
| PUT/PATCH | `/api/v1/bills/{id}/` | Update bill (before payment only) | Cashier |
| GET | `/api/v1/bills/{id}/invoice/` | Generate/download invoice (PDF) | Cashier/Admin |

### 7.12 Payments

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| POST | `/api/v1/bills/{bill_id}/payments/` | Add payment | Cashier |
| GET | `/api/v1/bills/{bill_id}/payments/` | Get payments for a bill | Cashier/Admin |
| PUT/PATCH | `/api/v1/payments/{id}/` | Update payment (corrections) | Cashier/Admin |
| GET | `/api/v1/payments/pending/` | All bills with pending/partial status | Cashier/Admin |
| GET | `/api/v1/payments/` | Full payment history (`?from=`, `?to=`) | Cashier/Admin |

### 7.13 Delivery

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| PATCH | `/api/v1/service-jobs/{job_id}/ready-for-delivery/` | Mark ready (auto on full payment, 8.4) | System/Cashier |
| GET | `/api/v1/delivery/ready/` | List vehicles ready for delivery | Cashier |
| POST | `/api/v1/service-jobs/{job_id}/delivery/` | Complete delivery | Cashier |
| GET | `/api/v1/delivery/delivered/` | List delivered vehicles (`?date=`) | Cashier/Admin |

### 7.14 Service History

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| GET | `/api/v1/vehicles/{id}/history/` | History by vehicle ID | Advisor+ |
| GET | `/api/v1/vehicles/history/?vehicle_number={no}` | History by vehicle number | Advisor+ |
| GET | `/api/v1/customers/{id}/history/` | Full customer service history | Advisor+ |

### 7.15 Dashboard

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary/` | All dashboard metrics from Section 4/22 of spec | Role-scoped |

### 7.16 Reports

| Method | Endpoint | Description | 🔒 |
|---|---|---|---|
| GET | `/api/v1/reports/daily-revenue/?date=` | Daily revenue report | Admin |
| GET | `/api/v1/reports/monthly-revenue/?month=&year=` | Monthly revenue report | Admin |
| GET | `/api/v1/reports/completed-services/?from=&to=` | Completed services report | Admin |
| GET | `/api/v1/reports/pending-services/` | Pending services report | Admin |
| GET | `/api/v1/reports/mechanic-productivity/?from=&to=` | Mechanic productivity report | Admin |
| GET | `/api/v1/reports/spare-parts-usage/?from=&to=` | Most used spare parts | Admin |
| GET | `/api/v1/reports/low-stock/` | Low stock parts report | Admin |
| GET | `/api/v1/reports/vehicle-problems/` | Most common vehicle problems | Admin |
| GET | `/api/v1/reports/vehicle-service/{vehicle_id}/` | Single-vehicle service report | Admin |
| GET | `/api/v1/reports/pending-payments/` | Pending payment report | Admin |

### 7.17 API Documentation

`drf-spectacular` auto-generates this — once installed, you get:
- `GET /api/schema/` → raw OpenAPI 3.0 JSON
- `GET /api/docs/` → interactive Swagger UI
- Exportable directly to Postman: Postman can **import an OpenAPI URL** directly (File → Import → Link → paste `https://yourapp.onrender.com/api/schema/`), which auto-generates your full Postman Collection — satisfying the "Postman Collection" requirement without writing one by hand.

---

## 8. Business Logic & State Machines

### 8.1 Service Job State Machine

This is the backbone of the entire app. Every other module either **causes** a transition or **reads** the current state.

```
                    ┌─────────┐
                    │ waiting │  (created by Service Advisor)
                    └────┬────┘
                         │ assign_mechanic()
                         ▼
                   ┌────────────┐
            ┌──────│ in_progress│
            │      └─────┬──────┘
            │            │ mechanic needs a part not in stock
            │            ▼
            │   ┌──────────────────┐
            │   │ waiting_for_parts │──(stock restocked)──► back to in_progress
            │   └──────────────────┘
            │            │
            │            │ all service_work rows = 'completed'
            │            ▼
            │      ┌────────────┐
            │      │ qc_pending │
            │      └─────┬──────┘
            │            │ QC submitted
            │     ┌──────┴───────┐
            │     ▼              ▼
            │ ┌─────────┐  ┌──────────────────┐
            └─│ rework_  │  │  ready_for_bill   │
              │ required │  └─────────┬─────────┘
              └────┬─────┘            │ bill created
                   │                  ▼
        (mechanic redoes work)  ┌──────────────┐
                   │            │ (bill exists, │
                   └───────────►│  status stays │
                                │ ready_for_bill │
                                │ until payment) │
                                └───────┬────────┘
                                        │ full payment received
                                        ▼
                               ┌──────────────────┐
                               │ ready_for_delivery │
                               └─────────┬──────────┘
                                         │ delivery completed
                                         ▼
                                   ┌───────────┐
                                   │ delivered │  (terminal)
                                   └───────────┘

   Any state ──(advisor/admin cancels, no bill yet)──► cancelled (terminal)
```

**Implementation pattern — guard every transition in the service layer, never in the serializer:**

```python
# service_jobs/services.py
ALLOWED_TRANSITIONS = {
    "waiting": {"in_progress", "cancelled"},
    "in_progress": {"waiting_for_parts", "qc_pending", "cancelled"},
    "waiting_for_parts": {"in_progress", "cancelled"},
    "qc_pending": {"ready_for_bill", "rework_required"},
    "rework_required": {"in_progress"},
    "ready_for_bill": {"ready_for_delivery", "cancelled"},  # cancel only if unpaid
    "ready_for_delivery": {"delivered"},
    "delivered": set(),       # terminal
    "cancelled": set(),       # terminal
}

class InvalidTransitionError(Exception):
    pass

def transition_job_status(job, new_status, actor):
    if new_status not in ALLOWED_TRANSITIONS.get(job.status, set()):
        raise InvalidTransitionError(
            f"Cannot move job from '{job.status}' to '{new_status}'."
        )
    if new_status == "cancelled" and hasattr(job, "bill"):
        raise InvalidTransitionError("Cannot cancel a job that already has a bill.")
    job.status = new_status
    job.save(update_fields=["status", "updated_at"])
    # audit log entry here if you add one later
    return job
```

This single function is called from every place that changes a job's status — `assign_mechanic`, QC approval, payment completion, delivery completion — so the rule lives in **exactly one place**.

### 8.2 Quality Check → Job Status Cascade

```python
# quality_check/services.py
def submit_quality_check(job, qc_data, actor):
    qc = QualityCheck.objects.create(service_job=job, checked_by=actor, **qc_data)
    if qc.overall_status == "approved":
        transition_job_status(job, "ready_for_bill", actor)
    else:
        transition_job_status(job, "rework_required", actor)
    return qc
```

### 8.3 Parts Used → Stock Cascade (the trickiest rule in the whole spec)

Your spec says: *"When a part is added as used, stock should automatically decrease"* and *"Restore stock if used part is deleted."* This must be **atomic** — if the stock update fails, the parts-used record must not be saved either, or your stock count silently drifts from reality.

```python
# inventory/services.py
from django.db import transaction
from django.core.exceptions import ValidationError

class InsufficientStockError(Exception):
    pass

@transaction.atomic
def consume_part(service_job, spare_part_id, quantity, actor):
    part = SparePart.objects.select_for_update().get(id=spare_part_id)  # row lock
    if part.stock_quantity < quantity:
        raise InsufficientStockError(
            f"Only {part.stock_quantity} {part.unit} of {part.name} available."
        )
    part.stock_quantity -= quantity
    part.save(update_fields=["stock_quantity"])

    StockMovement.objects.create(
        spare_part=part, movement_type="out", quantity=quantity,
        reference_type="service_job", reference_id=service_job.id, created_by=actor,
    )
    return PartUsed.objects.create(
        service_job=service_job, part=part, quantity=quantity,
        price=part.selling_price, added_by=actor,        # price snapshot
    )

@transaction.atomic
def restore_part(part_used, actor):
    part = SparePart.objects.select_for_update().get(id=part_used.part_id)
    part.stock_quantity += part_used.quantity
    part.save(update_fields=["stock_quantity"])
    StockMovement.objects.create(
        spare_part=part, movement_type="in", quantity=part_used.quantity,
        reference_type="adjustment", reference_id=part_used.service_job_id,
        created_by=actor,
    )
    part_used.delete()
```

`select_for_update()` is essential here: it locks the `spare_parts` row for the duration of the transaction so two mechanics can't simultaneously "use" the last 2 units of a part and both succeed, leaving stock at -2. This is a real race condition in any multi-mechanic shop, not a theoretical one.

### 8.4 Payment → Bill → Job Cascade

```python
# payments/services.py
@transaction.atomic
def record_payment(bill, amount, method, payment_date, actor):
    Payment.objects.create(
        bill=bill, payment_method=method, paid_amount=amount,
        payment_date=payment_date, received_by=actor,
    )
    total_paid = bill.payments.aggregate(s=Sum("paid_amount"))["s"] or 0

    if total_paid >= bill.total_amount:
        bill.payment_status = "paid"
        bill.save(update_fields=["payment_status"])
        transition_job_status(bill.service_job, "ready_for_delivery", actor)
    elif total_paid > 0:
        bill.payment_status = "partial"
        bill.save(update_fields=["payment_status"])
    return bill
```

### 8.5 Soft Delete / Inactive Status Engine

Rather than hand-writing the same "check for dependent records" logic five times (Section 24 of your spec), implement it once as a reusable mixin:

```python
# core/services.py
class HasActiveDependentsError(Exception):
    def __init__(self, model_name, count):
        self.model_name = model_name
        self.count = count
        super().__init__(f"{model_name} has {count} dependent record(s); deactivating instead of deleting.")

def safe_deactivate_or_block(instance, dependent_querysets: dict):
    """
    dependent_querysets: {"vehicles": Vehicle.objects.filter(customer=instance), ...}
    If ANY queryset is non-empty, instance.status = 'inactive' instead of delete.
    Returns ("deleted"|"deactivated", instance)
    """
    for name, qs in dependent_querysets.items():
        if qs.exists():
            instance.status = "inactive"
            instance.save(update_fields=["status"])
            return "deactivated", instance
    instance.delete()
    return "deleted", instance
```

Used like this in each app's `services.py`:

```python
# customers/services.py
def delete_customer(customer):
    return safe_deactivate_or_block(customer, {
        "vehicles": Vehicle.objects.filter(customer=customer),
        "service_jobs": ServiceJob.objects.filter(vehicle__customer=customer),
    })

# mechanics: special case — must reassign BEFORE deactivating, not just block
def delete_mechanic(mechanic):
    active_jobs = ServiceJob.objects.filter(
        assigned_mechanic=mechanic,
        status__in=["waiting", "in_progress", "waiting_for_parts", "rework_required"],
    )
    if active_jobs.exists():
        raise HasActiveDependentsError("ServiceJob", active_jobs.count())
        # API layer returns 409 Conflict with the list of job_numbers,
        # forcing the Admin to reassign them first via the UI.
    mechanic.status = "inactive"
    mechanic.save(update_fields=["status"])
```

### 8.6 Auto-Generated Sequential Codes (`job_number`, `invoice_number`)

```python
# core/services.py
from django.db import transaction

def generate_sequential_code(prefix, model, field_name="job_number"):
    """Generates e.g. SJ-2026-00001. Uses select_for_update on a Sequence
    row per (prefix, year) to stay race-condition-safe under concurrent requests."""
    from django.utils import timezone
    year = timezone.now().year
    with transaction.atomic():
        seq, _ = SequenceCounter.objects.select_for_update().get_or_create(
            prefix=prefix, year=year, defaults={"last_value": 0}
        )
        seq.last_value += 1
        seq.save(update_fields=["last_value"])
        return f"{prefix}-{year}-{seq.last_value:05d}"
```

A tiny `SequenceCounter(prefix, year, last_value)` model backs this — far safer under concurrent requests than `Model.objects.count() + 1`, which has an obvious race condition the moment two cashiers create bills at the same second.

---

## 9. Validation & Error Handling Standards

### 9.1 Standard Response Envelope

Every endpoint — success or failure — returns the same shape, so the Flutter app can parse responses with one generic model class instead of one per endpoint:

```json
// Success
{
  "success": true,
  "message": "Service job created successfully",
  "data": { "id": 1, "job_number": "SJ-2026-00001", "...": "..." }
}

// Success (list, paginated)
{
  "success": true,
  "message": "Service jobs fetched successfully",
  "data": {
    "results": [ /* ... */ ],
    "count": 134,
    "next": "https://yourapp.onrender.com/api/v1/service-jobs/?page=3",
    "previous": "https://yourapp.onrender.com/api/v1/service-jobs/?page=1"
  }
}

// Validation error (400)
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "vehicle_id": ["This field is required."],
    "complaint": ["This field may not be blank."]
  }
}

// Business rule error (409 Conflict)
{
  "success": false,
  "message": "Cannot cancel a job that already has a bill.",
  "errors": {}
}

// Auth error (401)
{ "success": false, "message": "Authentication credentials were not provided.", "errors": {} }

// Permission error (403)
{ "success": false, "message": "You do not have permission to perform this action.", "errors": {} }

// Not found (404)
{ "success": false, "message": "Service job not found.", "errors": {} }
```

### 9.2 Custom Exception Handler

```python
# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "success": False,
            "message": _extract_message(exc, response),
            "errors": response.data if isinstance(response.data, dict) else {},
        }
        return response

    # Unhandled exceptions (custom business exceptions land here)
    from service_jobs.services import InvalidTransitionError
    from inventory.services import InsufficientStockError
    from core.services import HasActiveDependentsError

    if isinstance(exc, InvalidTransitionError):
        return Response({"success": False, "message": str(exc), "errors": {}}, status=409)
    if isinstance(exc, InsufficientStockError):
        return Response({"success": False, "message": str(exc), "errors": {}}, status=409)
    if isinstance(exc, HasActiveDependentsError):
        return Response({"success": False, "message": str(exc), "errors": {}}, status=409)

    return Response(
        {"success": False, "message": "An unexpected error occurred.", "errors": {}},
        status=500,
    )
```

### 9.3 Validation Rules Reference

| Field type | Rule |
|---|---|
| `email` | Valid email format, unique where required (users, optionally customers) |
| `phone` | Exactly matches `^\+?[0-9]{10,15}$`; normalize before saving (strip spaces/dashes) |
| `vehicle_number` | Uppercase + normalize spacing before saving (`kl11ab1234` → `KL 11 AB 1234`); enforce uniqueness |
| Money fields | `>= 0`; reject more than 2 decimal places at serializer level |
| `quantity` (parts used) | `> 0`; must not exceed available stock (checked in service layer, not just serializer) |
| Status fields | Always validated against the explicit `choices=` list — DRF rejects unknown values automatically |
| Foreign keys (`vehicle_id`, `part_id`, etc.) | Must reference an **active** record; DRF's `PrimaryKeyRelatedField` with a `queryset` filtered to `status='active'` handles this for free |
| Dates | `payment_date`/`delivery_date` cannot be in the future |

### 9.4 Pagination, Search, Filter, Sort — One Reusable Pattern

```python
# core/pagination.py
from rest_framework.pagination import PageNumberPagination

class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
```

```python
# Example viewset using django-filter + DRF SearchFilter/OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

class ServiceJobViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "assigned_mechanic"]
    search_fields = ["job_number", "vehicle__vehicle_number", "complaint"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]
```

This one pattern, applied consistently, satisfies "Pagination / Search / Filter / Sort" across **every** list endpoint in Section 7 without bespoke code per module.

---

## 10. Zero-Cost Deployment Architecture

> **Verified June 2026.** Free tiers change without notice — re-check provider docs before you commit, but as of this writing this stack is genuinely $0/month for a project at AutoCare Pro's scale.

### 10.1 Recommended Free Stack

| Component | Service | Free tier limits | Notes |
|---|---|---|---|
| **Backend hosting** | **Render** (Web Service, Free instance) | 512 MB RAM, 0.1 CPU, sleeps after 15 min idle, ~750 free instance-hours/workspace/month | No credit card needed for the free instance type. Cold start ~30-60s after sleep. |
| **Database** | **NeonDB** (Free plan) | 0.5 GB storage, 100 compute-hours/month, up to 2 CU autoscale, scale-to-zero | This is the better choice over Render's own free Postgres, which **expires 30 days after creation** and is deleted after a 14-day grace period — not viable for a real project. Neon's free Postgres has no such expiry. |
| **Media/file storage** (optional — vehicle photos, QC photos) | **Cloudinary** Free tier | ~25 GB storage/bandwidth combined credit | Required if you store images: Render's filesystem is **ephemeral** — any file saved to local disk is wiped on every redeploy/restart. Never store uploaded media on Render's disk. |
| **Keep-alive (optional)** | **cron-job.org** or **UptimeRobot** free plan | Free scheduled pings | Pings your `/health/` endpoint every 10-14 min to reduce (not eliminate) cold-start sleep. Use sparingly — see caveat below. |
| **CI/CD** | **GitHub Actions** | Free minutes for public repos; free tier minutes for private | Runs tests on every push, auto-deploys to Render via webhook on merge to `main`. |
| **API docs hosting** | Served by Django itself (`drf-spectacular`) | n/a | No separate hosting needed. |
| **Domain** | Render's `*.onrender.com` subdomain | Free | Custom domain also free on Render if you already own one. |

### 10.2 Architecture Diagram — Free Tier Deployment

```
┌────────────────────┐
│   Flutter App       │
│ (built APK / IPA /   │
│  or Flutter Web)     │
└──────────┬──────────┘
           │ HTTPS
           ▼
┌─────────────────────────────────┐        ┌──────────────────────┐
│  Render Free Web Service         │        │   cron-job.org        │
│  autocare-backend.onrender.com   │◄───────┤  GET /health/ every    │
│                                   │  ping  │  10-14 min (optional)  │
│  Gunicorn + Django + DRF         │        └──────────────────────┘
│  - Sleeps after 15 min idle      │
│  - Wakes on next request (~30-   │
│    60s cold start)                │
└───────────────┬───────────────────┘
                │ SSL connection (psycopg2 / dj-database-url)
                ▼
┌─────────────────────────────────┐
│   NeonDB Free Postgres            │
│   - Scale-to-zero compute         │
│   - 0.5 GB storage / 100 CU-hr    │
│   - PgBouncer connection pooling  │
│     built in (use pooled conn     │
│     string in production)          │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│   Cloudinary (optional)           │
│   - Vehicle / QC photos            │
│   - Free 25GB storage+bandwidth   │
└─────────────────────────────────┘

       Build/Deploy pipeline:
┌────────────┐   push to main   ┌──────────────────┐   webhook    ┌─────────┐
│  GitHub    │ ───────────────► │  GitHub Actions    │ ───────────► │ Render  │
│  Repo      │   (tests run)    │  (lint, pytest)    │  auto-deploy │         │
└────────────┘                  └──────────────────┘              └─────────┘
```

### 10.3 The Honest Trade-offs of Free Hosting

Be upfront with yourself about what "$0/month" actually costs you in user experience, so you can decide if it's acceptable for your stage:

1. **Cold starts.** After 15 minutes of no traffic, Render's free instance sleeps. The next request takes 30-60 seconds to wake it. For a service-center staff app used in bursts throughout the day, this means the first action after a lull (e.g. opening the app first thing in the morning) is slow.
   - *Mitigation:* a keep-alive ping every 10-14 minutes. **Caveat:** Render explicitly reserves the right to suspend free services that receive "uncommonly high" automated traffic, so don't ping more often than ~every 10 minutes, and understand this is a mitigation, not a guarantee — it can still sleep over genuinely idle stretches (e.g. overnight) and during any provider-side throttling.
   - *Better mitigation for staff-facing apps:* show a "Connecting…" splash/loading state in Flutter on app launch so a cold start doesn't look like the app is broken.

2. **NeonDB's 0.5 GB storage ceiling.** For a single service center, 0.5 GB stores **years** of customers/vehicles/jobs/bills as plain relational rows (this is text and numbers, not media). It becomes a constraint only if you add bulk activity logs, exported reports, or photo BLOBs into the same database — which is exactly why media goes to Cloudinary instead.

3. **Render's RAM (512 MB) and CPU (0.1 vCPU) are genuinely small.** Heavy reporting queries (e.g. "Most Used Spare Parts Report" across years of data) should use database-side aggregation (`.aggregate()`, `.annotate()`) rather than pulling rows into Python and summing in the app layer — this matters more on a constrained free instance than it would on a paid one.

4. **No SLA, no guaranteed uptime.** This stack is appropriate for an MVP, a pilot at one branch, a portfolio/demo, or pre-revenue validation. It is **not** appropriate once the service center actually depends on this app to run daily operations and downtime has a real cost — see [Section 15](#15-scaling-beyond-free-tier) for the upgrade path at that point.

5. **NeonDB cold starts too.** Neon's compute also scales to zero on the free plan; a request after idle time triggers Neon's own brief wake-up, compounding with Render's cold start. In practice this means the *very first* request after a long idle period can be noticeably slow (Render waking + Neon waking), while subsequent requests are fast.

### 10.4 `render.yaml` (Infrastructure as Code)

Render Blueprints let you define your entire service in one committed file, so deployment is reproducible and not a pile of manual dashboard clicks:

```yaml
# render.yaml — place at repo root
services:
  - type: web
    name: autocare-backend
    runtime: python
    plan: free
    buildCommand: "pip install -r requirements.txt && python manage.py collectstatic --noinput"
    startCommand: "gunicorn config.wsgi:application --bind 0.0.0.0:$PORT"
    envVars:
      - key: DJANGO_SETTINGS_MODULE
        value: config.settings.production
      - key: DATABASE_URL
        sync: false        # set manually in Render dashboard (from Neon)
      - key: SECRET_KEY
        generateValue: true
      - key: PYTHON_VERSION
        value: 3.12.4
      - key: WEB_CONCURRENCY
        value: 2
      - key: ALLOWED_HOSTS
        value: ".onrender.com"
```

---

## 11. Step-by-Step Deployment Guide

### Step 1 — Local Project Setup

```bash
mkdir autocare_backend && cd autocare_backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install django djangorestframework djangorestframework-simplejwt \
            psycopg2-binary python-decouple django-cors-headers \
            django-filter drf-spectacular dj-database-url gunicorn whitenoise

django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp customers
python manage.py startapp vehicles
python manage.py startapp inventory
python manage.py startapp service_jobs
python manage.py startapp service_work
python manage.py startapp parts_used
python manage.py startapp quality_check
python manage.py startapp billing
python manage.py startapp payments
python manage.py startapp delivery
python manage.py startapp dashboard
python manage.py startapp reports
python manage.py startapp core

pip freeze > requirements.txt
```

### Step 2 — Create a NeonDB Project

1. Sign up at neon.com (no credit card required for the Free plan).
2. Create a new project — pick a region close to your users (e.g. Asia-Pacific/Singapore if your service center is in India, for lower latency).
3. Neon gives you a connection string immediately:
   ```
   postgresql://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require
   ```
4. **Use the pooled connection string** (Neon provides both a direct and a pooled/PgBouncer URL — look for `-pooler` in the host). Django opens/closes connections per-request under Gunicorn workers; the pooled endpoint handles this far better than the direct one and avoids hitting Neon's connection limits.
5. Save this connection string — you'll set it as `DATABASE_URL` in both your local `.env` and Render's environment variables.

### Step 3 — Configure Settings for Environment Switching

```python
# config/settings/base.py
import dj_database_url
from decouple import config

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(",")

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "rest_framework_simplejwt", "rest_framework_simplejwt.token_blacklist",
    "corsheaders", "django_filters", "drf_spectacular",
    "core", "accounts", "customers", "vehicles", "inventory",
    "service_jobs", "service_work", "parts_used", "quality_check",
    "billing", "payments", "delivery", "dashboard", "reports",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serves static files on Render
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
```

```python
# config/settings/production.py
from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="").split(",")
```

```bash
# .env (local — never commit this file)
SECRET_KEY=your-local-dev-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:pass@your-neon-pooled-host.neon.tech/autocare?sslmode=require
ALLOWED_HOSTS=127.0.0.1,localhost
```

### Step 4 — Run Initial Migrations Locally Against Neon

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Visit http://127.0.0.1:8000/admin/ to confirm DB connectivity
```

### Step 5 — Push to GitHub

```bash
git init
echo "venv/
.env
__pycache__/
*.pyc
staticfiles/
db.sqlite3" > .gitignore
git add .
git commit -m "Initial AutoCare Pro backend setup"
git remote add origin https://github.com/<your-username>/autocare-backend.git
git push -u origin main
```

### Step 6 — Deploy to Render

**Option A — Render Blueprint (recommended, uses the `render.yaml` from 10.4):**
1. Render dashboard → "New" → "Blueprint" → connect your GitHub repo.
2. Render reads `render.yaml` and provisions the web service automatically.
3. Go to the service's **Environment** tab and manually add:
   - `DATABASE_URL` = your Neon **pooled** connection string
   - `CORS_ALLOWED_ORIGINS` = your Flutter web origin if applicable
4. Click "Deploy."

**Option B — Manual setup (if you skip the Blueprint):**
1. Render dashboard → "New" → "Web Service" → connect repo.
2. Runtime: Python 3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
3. Instance type: **Free**.
4. Add the same environment variables as above, plus `SECRET_KEY` (generate one) and `ALLOWED_HOSTS=.onrender.com`.
5. Deploy.

### Step 7 — Run Migrations on Render

Render's free web service doesn't give you a persistent shell by default, so run the first production migration via Render's **Shell** tab (available even on free instances for one-off commands) or by temporarily adding a Render **Job**:

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 8 — Verify

```bash
curl https://autocare-backend.onrender.com/api/v1/auth/login/ \
  -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@gmail.com","password":"yourpassword"}'
```

You should get back `access`, `refresh`, and `user`. Visit `https://autocare-backend.onrender.com/api/docs/` to confirm Swagger UI is live.

### Step 9 — (Optional) Add a Keep-Alive Job

```python
# core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})
```

```python
# config/urls.py
path("health/", health_check),
```

Then register `https://autocare-backend.onrender.com/health/` on cron-job.org with a 10-14 minute interval.

### Step 10 — CI/CD with GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Test and Deploy
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python manage.py test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          SECRET_KEY: ci-test-key
          DEBUG: "True"
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Render Deploy
        run: curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
```

Render gives you a unique **Deploy Hook URL** per service (Settings → Deploy Hook) — store it as a GitHub Actions secret (`RENDER_DEPLOY_HOOK_URL`). This way every push to `main` runs your test suite, and only deploys if tests pass.

---

## 12. Flutter Integration Guide

### 12.1 Recommended Packages

```yaml
# pubspec.yaml
dependencies:
  dio: ^5.4.0                      # HTTP client with interceptors
  flutter_secure_storage: ^9.0.0   # store JWT tokens securely
  flutter_riverpod: ^2.5.0         # or provider/bloc — state management
  freezed: ^2.5.0                  # immutable models + JSON
  json_annotation: ^4.9.0
  go_router: ^14.0.0               # role-based route guarding
```

### 12.2 Dio Client with Auto Token Refresh

```dart
// lib/core/api_client.dart
class ApiClient {
  final Dio dio;
  final FlutterSecureStorage storage = const FlutterSecureStorage();

  ApiClient() : dio = Dio(BaseOptions(
          baseUrl: "https://autocare-backend.onrender.com/api/v1",
          connectTimeout: const Duration(seconds: 45), // generous: free-tier cold starts
        )) {
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storage.read(key: "access_token");
        if (token != null) options.headers["Authorization"] = "Bearer $token";
        handler.next(options);
      },
      onError: (DioException e, handler) async {
        if (e.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            final retryReq = await dio.fetch(e.requestOptions);
            return handler.resolve(retryReq);
          }
          // refresh also failed → force logout, navigate to login screen
        }
        handler.next(e);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    final refresh = await storage.read(key: "refresh_token");
    if (refresh == null) return false;
    try {
      final res = await dio.post("/auth/refresh/", data: {"refresh": refresh});
      await storage.write(key: "access_token", value: res.data["access"]);
      return true;
    } catch (_) {
      return false;
    }
  }
}
```

> Note the **45-second connect timeout** — this is not arbitrary. It directly accounts for Render free-tier cold starts (Section 10.3). A default 10-15s Dio timeout will cause spurious "request failed" errors on the very first request after the backend has gone to sleep.

### 12.3 Role-Based Navigation Guard (go_router)

```dart
final router = GoRouter(
  redirect: (context, state) {
    final role = ref.read(authProvider).role;  // from decoded JWT or /auth/me/
    if (state.fullPath!.startsWith("/admin") && role != "admin") return "/unauthorized";
    if (state.fullPath!.startsWith("/mechanic") && role != "mechanic") return "/unauthorized";
    // etc.
    return null;
  },
  routes: [ /* ... */ ],
);
```

> Treat this as a **UX convenience**, not a security boundary — the real enforcement is the `get_queryset()` role filtering on the backend (Section 6.3). Flutter-side guards just stop a legitimate user from seeing screens irrelevant to their role; they cannot be relied on to stop a malicious actor, since a modified client could call the API directly.

### 12.4 Standard Response Model (matches Section 9.1)

```dart
@freezed
class ApiResponse<T> with _$ApiResponse<T> {
  const factory ApiResponse({
    required bool success,
    required String message,
    T? data,
    Map<String, dynamic>? errors,
  }) = _ApiResponse<T>;
}
```

Because every endpoint in this backend returns the same envelope shape, you write **one** generic parser and reuse it for all 90+ endpoints in Section 7 — this is the direct payoff of standardizing the response format on the backend.

### 12.5 Suggested Flutter Folder Structure (mirrors backend modules)

```
lib/
├── core/ (api_client, storage, theme, router)
├── models/ (one file per backend entity — Customer, Vehicle, ServiceJob...)
├── features/
│   ├── auth/
│   ├── admin/ (dashboard, users, reports)
│   ├── advisor/ (customers, vehicles, job_creation)
│   ├── mechanic/ (assigned_jobs, service_work, parts_used)
│   └── cashier/ (billing, payments, delivery)
└── shared/ (widgets reused across roles)
```

---

## 13. Development Roadmap (Phased Implementation Plan)

Recommended build order — each phase produces something testable end-to-end before moving on, rather than building all models first and discovering integration problems at the end.

### Phase 0 — Foundations (Week 1)
- Project scaffold, settings split (dev/prod), NeonDB connected, deployed "Hello World" to Render.
- Custom User model + JWT auth (login/refresh/logout) working end-to-end, tested with Postman/curl.
- Standard response envelope + exception handler in place from day one — retrofitting this later touches every view.

### Phase 1 — Master Data (Week 2)
- Customers, Vehicles, Spare Parts, Mechanics (Users with role=mechanic) — full CRUD with soft-delete rules.
- Search/filter/pagination pattern established here, reused everywhere after.

### Phase 2 — Core Workflow Skeleton (Weeks 3-4)
- Service Job CRUD + the state machine (Section 8.1) with **only** `waiting ↔ in_progress ↔ cancelled` transitions at first.
- Assign/change mechanic.
- Get this single slice deployed and testable from a minimal Flutter screen before adding more states — confirms the whole pipeline (Flutter → Render → Neon) works under real network conditions, including cold starts.

### Phase 3 — Work, Parts, Stock (Week 5)
- Service Work CRUD, Parts Used CRUD with the atomic stock-consumption service (Section 8.3).
- Stock movement ledger, low-stock endpoint.
- This is the highest-risk phase for race conditions — write the concurrent-access test (`test_stock_integrity.py`) here, not later.

### Phase 4 — Quality Check → Billing → Payment → Delivery (Weeks 6-7)
- Wire up the remaining state transitions in order: QC cascade (8.2) → Billing → Payment cascade (8.4) → Delivery.
- By the end of this phase, a vehicle can travel the **entire** lifecycle from intake to delivery through the API.

### Phase 5 — History, Dashboard, Reports (Week 8)
- Service history aggregation endpoints.
- Dashboard summary (use `.aggregate()` queries, not Python loops — see 10.3 point 3).
- All 9 reports.

### Phase 6 — Hardening (Week 9)
- API documentation review (drf-spectacular output, Postman import test).
- Full permission matrix test pass (Section 6.4) — write one test per cell that matters (e.g. "mechanic cannot delete customer").
- Load-test the stock consumption endpoint specifically for race conditions.
- Security checklist (Section 14).

### Phase 7 — Flutter Integration & UAT (Weeks 10-12)
- Connect each Flutter role module to its corresponding backend slice, in the same order as Phases 1-5.
- User acceptance testing with actual service-center staff if possible — this is where you'll discover gaps your spec didn't anticipate (e.g. "what if a mechanic needs to add a part used at 11pm and the manager isn't around to approve it" — a real operational question your current spec doesn't address).

> **This is a solo/small-team estimate assuming familiarity with Django after the learning curve.** If Django is new to you (your message says you know Flutter, not backend), budget meaningfully more time for Phase 0-1 — Django's request/response cycle, ORM, and DRF serializers are the concepts to get comfortable with first, since everything in Phases 2+ builds on them.

---

## 14. Security Checklist

Run through this before considering the backend "production ready," even for an MVP:

- [ ] `DEBUG = False` in production settings — confirm via `config.settings.production`, never edit `base.py` directly for a quick test.
- [ ] `SECRET_KEY` is unique, random, and stored only in Render's environment variables — never committed, never reused from a tutorial.
- [ ] `ALLOWED_HOSTS` is an explicit list, not `["*"]`.
- [ ] All passwords stored via Django's built-in PBKDF2 hasher (default) — never store or log plaintext passwords, including in `createsuperuser` scripts left in version control.
- [ ] JWT access token lifetime is short (≤30 min); refresh token blacklisting is enabled (Section 6.2) so logout is real, not just client-side token deletion.
- [ ] Every viewset's `get_queryset()` is checked for role-based row filtering — re-read Section 6.3's warning; this is the most common real-world vulnerability in role-based apps.
- [ ] CORS is locked to your actual Flutter web origin(s) in production, not `CORS_ALLOW_ALL_ORIGINS = True`.
- [ ] Rate limiting on `/auth/login/` (DRF throttling classes) to slow down brute-force attempts.
- [ ] All money calculations server-side only — never trust a `total_amount` sent from the Flutter client; always recompute `labour_charge + parts_charge + tax - discount` in the service layer.
- [ ] SQL injection: you're using the Django ORM throughout, which parameterizes queries automatically — avoid `.raw()` or `.extra()` with string-interpolated user input; if you must use raw SQL, use parameterized placeholders.
- [ ] Postgres connection string (with credentials) never appears in logs, error messages, or Sentry/monitoring breadcrumbs.
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT = True`) — Render provides free TLS automatically, just don't disable the redirect.
- [ ] Admin Django panel (`/admin/`) — either restrict access (IP allowlist, or disable in production if unused) or at minimum ensure superuser passwords are strong; this panel has full DB access by design.
- [ ] Backups: Neon's free plan offers limited point-in-time restore (6-hour window) — for anything beyond a hobby/demo stage, schedule your own periodic `pg_dump` export until you upgrade to a paid plan with longer retention.

---

## 15. Scaling Beyond Free Tier

A clear trigger list for when to start paying for infrastructure — useful so you're deciding based on evidence, not guessing:

| Signal | What it means | What to upgrade |
|---|---|---|
| Staff complain about the app being slow "first thing in the morning" or after lunch breaks | Cold starts are now a daily friction point, not a rare annoyance | Render **Starter** plan (~$7/month) — removes free-tier sleep entirely |
| `stock_quantity` or row counts approaching Neon's 0.5 GB | You're a genuinely active multi-bay shop now | Neon **Launch** plan — usage-based, often $1-3/month at this scale, no storage ceiling |
| Multiple service centers / branches | Single-tenant design (this doc) needs a `branch_id` on most tables, or fully separate deployments per branch | Architecture change — plan this *before* it's urgent, retrofitting multi-tenancy later is expensive |
| You need guaranteed uptime (revenue depends on the app being up) | Free tier explicitly has no SLA | Paid Render plan + Neon paid plan + consider a status page/monitoring (e.g. Better Stack) |
| Concurrent mechanics regularly hitting the same spare part simultaneously | The `select_for_update()` locking in Section 8.3 starts to create queuing delays under load | Move to Neon's higher CU autoscale tier, and profile whether locking granularity needs to change |
| You want native push notifications (e.g. "your vehicle is ready") | Out of scope for this doc's spec | Add Firebase Cloud Messaging (has its own generous free tier, separate from this stack) |

**Realistic cost at "one real, busy service center" scale:** Render Starter ($7/mo) + Neon Launch (often $5-15/mo depending on usage) ≈ **$15-25/month** — a small, predictable jump up from $0, not a cliff.

---

## 16. Appendix: Environment Variables & Config Files

### 16.1 `.env.example` (commit this, not `.env`)

```bash
SECRET_KEY=
DEBUG=False
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
ALLOWED_HOSTS=autocare-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://your-flutter-web-domain.com
```

### 16.2 `requirements.txt` (core set)

```
Django>=5.0,<5.1
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
psycopg2-binary>=2.9
python-decouple>=3.8
django-cors-headers>=4.3
django-filter>=24.2
drf-spectacular>=0.27
dj-database-url>=2.2
gunicorn>=22.0
whitenoise>=6.6
```

### 16.3 `Procfile` (backup, in case `render.yaml` start command isn't used)

```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

### 16.4 `runtime.txt`

```
python-3.12.4
```

---

## Closing Notes

This document maps every module in your original requirement doc to a concrete table, endpoint, permission rule, and state transition — nothing in your 27-section spec was dropped, and two gaps were filled in explicitly (the `stock_movements` audit table in Section 4, and the QC-performer-role ambiguity flagged in Section 6.4).

The single most important section to internalize before writing code is **Section 8** — the state machine and its cascading rules are what separates "a CRUD app with some buttons" from a system that actually enforces how a car moves through a real service center. Everything else in this document exists to support that core correctly and cheaply.







