# AutoCare Plus — Frontend Integration Guide

**Stack:** Flutter (frontend) · Django REST Framework (backend) · PostgreSQL (database)  
**Base URL (dev):** `http://localhost:8000`  
**Base URL (prod):** `https://autocare-backend-iz74.onrender.com`  
**API Prefix:** `/api/v1/`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Complete API Reference](#3-complete-api-reference)
4. [Workflows](#4-workflows)
5. [Database Flow](#5-database-flow)
6. [Error Handling & Response Format](#6-error-handling--response-format)
7. [Pagination & Filtering](#7-pagination--filtering)
8. [Integration Checklist](#8-integration-checklist)

---

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter App                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │  Admin   │ │ Service  │ │ Mechanic │ │ Cashier  │            │
│  │   UI      │ │ Advisor  │ │   UI     │ │   UI     │            │
│  │          │ │   UI     │ │          │ │          │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
│       └────────────┴────────────┴────────────┘                   │
│                           │                                      │
│                    HTTP API Calls                                │
│              (JWT Bearer Token in Header)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    Django REST Framework                          │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │ Middleware  │  │  URL Router│  │    Permission Classes    │   │
│  │ (CORS, Auth)│  │  (ViewSets)│  │  (IsAdmin, IsMechanic…) │   │
│  └────────────┘  └─────┬──────┘  └──────────────────────────┘   │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐  │
│  │                   Serializers                               │  │
│  │  (Request validation + Response formatting)                 │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐  │
│  │                   Services                                  │  │
│  │  (Business logic: state machine, stock atomic ops, etc.)   │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐  │
│  │                   Models (ORM)                              │  │
│  │  (Django models mapping to DB tables)                      │  │
│  └─────────────────────┬──────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                     PostgreSQL Database                          │
│                                                                  │
│  customers ──┐                                                  │
│              ├── vehicles ── service_jobs ──┐                   │
│  users ──────┘                              ├── service_work    │
│                                             ├── parts_used      │
│  spare_parts ── stock_movements             ├── quality_check   │
│                               bill ────────┤                   │
│                                           payment ── delivery   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Role-Based Access

| Role | Label | Responsibilities |
|------|-------|-----------------|
| `admin` | Admin | Full CRUD: users, mechanics, inventory, reports, dashboard, quality checks |
| `service_advisor` | Service Advisor | CRUD: customers, vehicles, service jobs; assign/change mechanics |
| `mechanic` | Mechanic | Manage own assigned jobs: service work, parts used (read-only on others) |
| `cashier` | Cashier | Billing, payments, delivery |

### 1.3 Token Management

| Detail | Value |
|--------|-------|
| Access token lifetime | **30 minutes** |
| Refresh token lifetime | **7 days** |
| Token storage (Flutter) | `flutter_secure_storage` |
| Auto-refresh | Intercept 401, call `/auth/refresh/`, retry original request |

---

## 2. Authentication & Authorization

### 2.1 Login Flow

```
Flutter                          Backend
  │                                │
  │  POST /api/v1/auth/login/      │
  │  { email, password }           │
  │ ─────────────────────────────> │
  │                                │  Validate credentials
  │                                │  Generate JWT pair
  │  { access, refresh }           │
  │ <───────────────────────────── │
  │                                │
  │  Store tokens securely         │
  │  Decode JWT to get role/name   │
  │                                │
  │  GET /api/v1/auth/me/          │
  │  Authorization: Bearer <token> │
  │ ─────────────────────────────> │
  │  { id, email, name, role... }  │
  │ <───────────────────────────── │
```

### 2.2 All Auth Endpoints

#### POST `/api/v1/auth/login/`
```json
// Request
{
  "email": "admin@autocare.com",
  "password": "admin123"
}

// Response 200
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}

// Response 401
{
  "detail": "No active account found with the given credentials"
}
```

#### POST `/api/v1/auth/refresh/`
```json
// Request
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}

// Response 200
{
  "access": "eyJ0eXAiOiJKV1Qi..."
}
```

#### POST `/api/v1/auth/logout/`
```json
// Request
{
  "refresh": "eyJ0eXAiOiJKV1Qi..."
}

// Response 200
{
  "detail": "Successfully logged out"
}
```

#### GET `/api/v1/auth/me/`
```json
// Response 200
{
  "id": 1,
  "email": "admin@autocare.com",
  "name": "Admin User",
  "phone": "9876543210",
  "role": "admin",
  "specialization": null,
  "status": "active",
  "is_active": true
}
```

### 2.3 All Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

---

## 3. Complete API Reference

### 3.1 Users (Admin only)

#### GET/POST `/api/v1/users/`
```json
// POST Request
{
  "email": "mechanic1@autocare.com",
  "name": "Rajesh Kumar",
  "phone": "9876543211",
  "role": "mechanic",
  "specialization": "Engine & Transmission",
  "password": "password123"
}

// POST Response 201
{
  "id": 5,
  "email": "mechanic1@autocare.com",
  "name": "Rajesh Kumar",
  "phone": "9876543211",
  "role": "mechanic",
  "specialization": "Engine & Transmission",
  "status": "active"
}

// GET Response 200 (paginated)
{
  "count": 8,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "email": "admin@autocare.com",
      "name": "Admin User",
      "phone": "9876543210",
      "role": "admin",
      "specialization": null,
      "status": "active",
      "is_active": true
    }
  ]
}
```

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/v1/users/` | List users |
| POST | `/api/v1/users/` | Create user |
| GET | `/api/v1/users/{id}/` | Retrieve user |
| PUT | `/api/v1/users/{id}/` | Update user |
| PATCH | `/api/v1/users/{id}/` | Partial update |
| DELETE | `/api/v1/users/{id}/` | Delete user |
| PATCH | `/api/v1/users/{id}/activate/` | Activate user |
| PATCH | `/api/v1/users/{id}/deactivate/` | Deactivate user |

---

### 3.2 Customers

#### GET/POST `/api/v1/customers/`
```json
// POST Request
{
  "name": "Amit Sharma",
  "phone": "9876543201",
  "email": "amit@example.com",
  "address": "123, MG Road, Bangalore"
}

// POST Response 201
{
  "id": 1,
  "name": "Amit Sharma",
  "phone": "9876543201",
  "email": "amit@example.com",
  "address": "123, MG Road, Bangalore",
  "status": "active",
  "created_at": "2026-07-08T10:30:00.000Z",
  "updated_at": "2026-07-08T10:30:00.000Z"
}

// GET Response 200 (paginated, searchable)
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [{ ... }]
}
```

Query params: `?search=amit&ordering=-created_at`

#### GET `/api/v1/customers/{id}/vehicles/`
Returns the customer's vehicles array.

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/customers/` | Service Advisor |
| POST | `/api/v1/customers/` | Service Advisor |
| GET/PUT/PATCH | `/api/v1/customers/{id}/` | Service Advisor |
| DELETE | `/api/v1/customers/{id}/` | Admin (soft-delete) |
| GET | `/api/v1/customers/{id}/vehicles/` | Service Advisor |

---

### 3.3 Vehicles

```json
// POST Request
{
  "customer": 1,
  "vehicle_number": "KA-01-AB-1234",
  "brand": "Maruti Suzuki",
  "model": "Swift VXi",
  "year": 2022,
  "kilometers": 15000
}

// POST Response 201
{
  "id": 1,
  "customer": 1,
  "vehicle_number": "KA-01-AB-1234",
  "brand": "Maruti Suzuki",
  "model": "Swift VXi",
  "year": 2022,
  "kilometers": 15000,
  "status": "active",
  "created_at": "2026-07-08T10:30:00.000Z",
  "updated_at": "2026-07-08T10:30:00.000Z"
}
```

Query params: `?customer=1&search=swift`

| Method | URL | Permission |
|--------|-----|-----------|
| GET/POST | `/api/v1/vehicles/` | Service Advisor |
| GET/PUT/PATCH | `/api/v1/vehicles/{id}/` | Service Advisor |
| DELETE | `/api/v1/vehicles/{id}/` | Admin (soft-delete) |

---

### 3.4 Mechanics

```json
// POST Request
{
  "email": "mechanic2@autocare.com",
  "name": "Suresh Reddy",
  "phone": "9876543212",
  "role": "mechanic",
  "specialization": "AC & Electrical",
  "password": "password123"
}

// GET Response
{
  "id": 6,
  "email": "mechanic2@autocare.com",
  "name": "Suresh Reddy",
  "phone": "9876543212",
  "role": "mechanic",
  "specialization": "AC & Electrical",
  "status": "active",
  "is_active": true
}
```

| Method | URL | Action |
|--------|-----|--------|
| GET | `/api/v1/mechanics/{id}/assigned_vehicles/` | Get mechanic's assigned jobs |
| PATCH | `/api/v1/mechanics/{id}/activate/` | Activate mechanic |
| PATCH | `/api/v1/mechanics/{id}/deactivate/` | Deactivate (blocked if active jobs → 409) |

All other CRUD operations mirror Users section pattern.

---

### 3.5 Spare Parts / Inventory

#### GET/POST `/api/v1/spare-parts/`
```json
// POST Request
{
  "name": "Engine Oil 5W30",
  "part_number": "OIL-5W30-1L",
  "stock_quantity": 50,
  "unit": "litre",
  "purchase_price": 350.00,
  "selling_price": 450.00,
  "minimum_stock": 10
}

// POST Response 201
{
  "id": 1,
  "name": "Engine Oil 5W30",
  "part_number": "OIL-5W30-1L",
  "stock_quantity": 50.00,
  "unit": "litre",
  "purchase_price": 350.00,
  "selling_price": 450.00,
  "minimum_stock": 10.00,
  "status": "active",
  "created_at": "2026-07-08T10:30:00.000Z",
  "updated_at": "2026-07-08T10:30:00.000Z"
}
```

Query params: `?search=oil&ordering=-stock_quantity`

#### POST `/api/v1/spare-parts/{id}/add_stock/`
```json
// Request
{
  "quantity": 20
}

// Response 200
{
  "id": 1,
  "name": "Engine Oil 5W30",
  "stock_quantity": 70.00,
  ...
}
```

#### POST `/api/v1/spare-parts/{id}/reduce_stock/`
```json
// Request
{
  "quantity": 5,
  "reason": "Damaged during delivery"
}
```

#### GET `/api/v1/spare-parts/low_stock/`
Returns parts where `stock_quantity <= minimum_stock`.

#### GET `/api/v1/spare-parts/{id}/stock_history/`
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "spare_part": 1,
      "movement_type": "in",
      "quantity": 50.00,
      "reference_type": "purchase",
      "reference_id": null,
      "created_by_name": "Admin User",
      "created_at": "2026-07-08T10:30:00.000Z"
    }
  ]
}
```

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/spare-parts/` | All authenticated |
| POST/PUT/PATCH/DELETE | `/api/v1/spare-parts/{id}/` | Admin |
| POST add_stock, reduce_stock | `/api/v1/spare-parts/{id}/.../` | Admin |
| GET low_stock, stock_history | `/api/v1/spare-parts/.../` | Admin |

---

### 3.6 Service Jobs (Core Entity)

#### POST `/api/v1/service-jobs/`
```json
// Request
{
  "vehicle": 1,
  "complaint": "Engine overheating, AC not cooling",
  "service_type": "General Service + AC Repair",
  "assigned_mechanic": 5,
  "odometer_reading": 15230
}

// Response 201
{
  "id": 1,
  "job_number": "SJ-2026-00001",
  "vehicle": 1,
  "vehicle_number": "KA-01-AB-1234",
  "customer_name": "Amit Sharma",
  "complaint": "Engine overheating, AC not cooling",
  "service_type": "General Service + AC Repair",
  "assigned_mechanic": 5,
  "mechanic_name": "Rajesh Kumar",
  "created_by": 1,
  "status": "in_progress",
  "odometer_reading": 15230,
  "created_at": "2026-07-08T10:30:00.000Z",
  "updated_at": "2026-07-08T10:30:00.000Z"
}
```

Note: `assigned_mechanic` is optional at creation. If provided, status auto-sets to `in_progress`. Otherwise defaults to `waiting`.

#### GET `/api/v1/service-jobs/` (list)
Query params: `?status=qc_pending&assigned_mechanic=5&search=KA-01`

Mechanics only see their own jobs. Admins/Advisors see all.

#### PATCH `/api/v1/service-jobs/{id}/status/`
```json
// Request
{
  "status": "qc_pending"
}
```

#### PATCH `/api/v1/service-jobs/{id}/assign_mechanic/`
```json
// Request
{
  "mechanic_id": 5
}
```

#### PATCH `/api/v1/service-jobs/{id}/change_mechanic/`
```json
// Request
{
  "mechanic_id": 6
}
```

| Method | URL | Permission |
|--------|-----|-----------|
| GET/POST | `/api/v1/service-jobs/` | All authenticated (create: Advisor) |
| GET/PUT/PATCH | `/api/v1/service-jobs/{id}/` | All authenticated |
| DELETE | `/api/v1/service-jobs/{id}/` | Admin |
| PATCH status | `/api/v1/service-jobs/{id}/status/` | Service Advisor |
| PATCH assign_mechanic | `/api/v1/service-jobs/{id}/assign_mechanic/` | Service Advisor |
| PATCH change_mechanic | `/api/v1/service-jobs/{id}/change_mechanic/` | Service Advisor |

---

### 3.7 Service Work

```json
// POST Request
{
  "service_job": 1,
  "work_name": "Oil Change",
  "description": "Drain old oil, replace filter, fill 5W30",
  "labour_charge": 300.00
}

// Response 201
{
  "id": 1,
  "service_job": 1,
  "work_name": "Oil Change",
  "description": "Drain old oil, replace filter, fill 5W30",
  "status": "pending",
  "labour_charge": 300.00,
  "created_by": 5,
  "created_at": "2026-07-08T11:00:00.000Z",
  "updated_at": "2026-07-08T11:00:00.000Z"
}
```

#### PATCH `/api/v1/works/{id}/status/`
```json
// Request
{
  "status": "completed"
}
```

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/works/` | All authenticated (mechanic: own jobs) |
| POST/PUT/PATCH/DELETE | `/api/v1/works/` | Mechanic + assigned to job |

---

### 3.8 Parts Used

```json
// POST Request
{
  "service_job": 1,
  "part_id": 1,
  "quantity": 4
}

// Response 201
{
  "id": 1,
  "service_job": 1,
  "part": 1,
  "part_name": "Engine Oil 5W30",
  "part_number": "OIL-5W30-1L",
  "quantity": 4.00,
  "price": 450.00,
  "added_by": 5,
  "created_at": "2026-07-08T11:05:00.000Z",
  "updated_at": "2026-07-08T11:05:00.000Z"
}
```

Note: `price` auto-fills from `spare_part.selling_price`. Stock is **atomically reduced** (`select_for_update`). Deleting a PartUsed entry **restores** stock.

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/parts-used/` | All authenticated |
| POST/DELETE | `/api/v1/parts-used/{id}/` | Mechanic + assigned to job |

---

### 3.9 Quality Check

```json
// POST Request
{
  "service_job": 1,
  "brake_check": "passed",
  "engine_check": "passed",
  "oil_leakage_check": "no_issue",
  "ac_check": "failed",
  "tyre_check": "passed",
  "test_drive": "passed",
  "overall_status": "rework_required",
  "remarks": "AC compressor needs replacement"
}

// Response 201
{
  "id": 1,
  "service_job": 1,
  "brake_check": "passed",
  "engine_check": "passed",
  "oil_leakage_check": "no_issue",
  "ac_check": "failed",
  "tyre_check": "passed",
  "test_drive": "passed",
  "overall_status": "rework_required",
  "remarks": "AC compressor needs replacement",
  "checked_by": 1,
  "created_at": "2026-07-08T11:30:00.000Z",
  "updated_at": "2026-07-08T11:30:00.000Z"
}
```

**Side effect:** `overall_status=approved` → job status becomes `ready_for_bill`.  
`overall_status=rework_required` → job status becomes `rework_required`.

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/quality-checks/` | All authenticated |
| POST/PUT/PATCH/DELETE | `/api/v1/quality-checks/{id}/` | Admin |

---

### 3.10 Billing

#### POST `/api/v1/bills/`
```json
// Request
{
  "service_job": 1,
  "labour_charge": 1200.00,
  "parts_charge": 1800.00,
  "tax": 150.00,
  "discount": 100.00
}

// Response 201
{
  "id": 1,
  "invoice_number": "INV-2026-00001",
  "service_job": 1,
  "job_number": "SJ-2026-00001",
  "labour_charge": 1200.00,
  "parts_charge": 1800.00,
  "tax": 150.00,
  "discount": 100.00,
  "total_amount": 3050.00,
  "payment_status": "pending",
  "created_by": 1,
  "created_at": "2026-07-08T12:00:00.000Z",
  "updated_at": "2026-07-08T12:00:00.000Z"
}
```

Note: If the job already has a bill, creation returns a validation error. Use PUT/PATCH to modify existing bill (only if not paid).

#### GET `/api/v1/bills/`
Query params: `?payment_status=pending`

| Method | URL | Permission |
|--------|-----|-----------|
| GET/POST | `/api/v1/bills/` | Cashier |
| GET/PUT/PATCH | `/api/v1/bills/{id}/` | Cashier |
| DELETE | `/api/v1/bills/{id}/` | Cashier |

---

### 3.11 Payments

```json
// POST Request
{
  "bill": 1,
  "payment_method": "upi",
  "paid_amount": 3050.00,
  "payment_date": "2026-07-08"
}

// Response 201
{
  "id": 1,
  "bill": 1,
  "payment_method": "upi",
  "paid_amount": 3050.00,
  "payment_date": "2026-07-08",
  "received_by": 1,
  "created_at": "2026-07-08T12:15:00.000Z"
}
```

**Side effect:** If total paid amount >= bill total → `bill.payment_status` becomes `paid`.  
If fully paid → job status auto-transitions to `ready_for_delivery`.

#### GET `/api/v1/payments/pending/`
Returns bills where `payment_status` is `pending` or `partial`, with customer/job details.

| Method | URL | Permission |
|--------|-----|-----------|
| GET/POST | `/api/v1/payments/` | Cashier |
| GET | `/api/v1/payments/{id}/` | Cashier |
| GET | `/api/v1/payments/pending/` | Cashier |

---

### 3.12 Delivery

```json
// POST Request
{
  "service_job": 1,
  "delivery_date": "2026-07-08T17:00:00.000Z",
  "customer_received": true,
  "remarks": "Customer satisfied"
}

// Response 201
{
  "id": 1,
  "service_job": 1,
  "delivered_by": 1,
  "delivery_date": "2026-07-08T17:00:00.000Z",
  "customer_received": true,
  "remarks": "Customer satisfied",
  "created_at": "2026-07-08T17:05:00.000Z"
}
```

**Side effect:** Job status → `delivered` (terminal state).

#### GET `/api/v1/delivery/ready/`
Jobs with `status=ready_for_delivery`.

#### GET `/api/v1/delivery/delivered/`
Query params: `?date=2026-07-08`.

| Method | URL | Permission |
|--------|-----|-----------|
| GET/POST | `/api/v1/delivery/` | Cashier |
| GET | `/api/v1/delivery/{id}/` | Cashier |
| GET | `/api/v1/delivery/ready/` | Cashier |
| GET | `/api/v1/delivery/delivered/` | Cashier |

---

### 3.13 Service History

#### GET `/api/v1/vehicles/{vehicle_id}/history/`
#### GET `/api/v1/vehicles/history/?vehicle_number=KA-01-AB-1234`
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "job_number": "SJ-2026-00001",
      "service_type": "General Service + AC Repair",
      "status": "delivered",
      "created_at": "2026-07-08T10:30:00.000Z",
      "mechanic_name": "Rajesh Kumar",
      "total_labour": 1200.00,
      "total_parts": 1800.00
    }
  ]
}
```

#### GET `/api/v1/customers/{customer_id}/history/`
Returns all service jobs for all vehicles owned by the customer.

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/vehicles/{id}/history/` | Service Advisor |
| GET | `/api/v1/vehicles/history/` | Service Advisor |
| GET | `/api/v1/customers/{id}/history/` | Service Advisor |

---

### 3.14 Dashboard

#### GET `/api/v1/dashboard/summary/`
```json
{
  "total_jobs_today": 12,
  "active_jobs": 8,
  "pending_qc": 3,
  "ready_for_delivery": 2,
  "revenue_today": 15250.00,
  "low_stock_items": 1
}
```

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/dashboard/summary/` | Admin |

---

### 3.15 Reports

#### GET `/api/v1/reports/daily-revenue/?date=2026-07-08`
```json
{
  "date": "2026-07-08",
  "total_revenue": 15250.00,
  "total_bills": 5
}
```

#### GET `/api/v1/reports/monthly-revenue/?month=7&year=2026`
```json
{
  "month": 7,
  "year": 2026,
  "total_revenue": 285000.00,
  "total_bills": 95
}
```

#### GET `/api/v1/reports/completed-services/?from=2026-07-01&to=2026-07-08`
```json
{
  "from_date": "2026-07-01",
  "to_date": "2026-07-08",
  "total_completed": 42
}
```

#### GET `/api/v1/reports/mechanic-productivity/?from=2026-07-01&to=2026-07-08`
```json
{
  "from_date": "2026-07-01",
  "to_date": "2026-07-08",
  "mechanics": [
    {
      "mechanic_id": 5,
      "mechanic_name": "Rajesh Kumar",
      "completed_jobs": 15
    },
    {
      "mechanic_id": 6,
      "mechanic_name": "Suresh Reddy",
      "completed_jobs": 12
    }
  ]
}
```

#### GET `/api/v1/reports/spare-parts-usage/?from=2026-07-01&to=2026-07-08`
```json
{
  "from_date": "2026-07-01",
  "to_date": "2026-07-08",
  "parts": [
    {
      "part_id": 1,
      "part_name": "Engine Oil 5W30",
      "part_number": "OIL-5W30-1L",
      "total_quantity_used": 12.00
    }
  ]
}
```

| Method | URL | Permission |
|--------|-----|-----------|
| GET | `/api/v1/reports/.../` | Admin |

---

### 3.16 Health & Docs (no auth for health)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/health/` | Returns `{"status": "ok"}` |
| GET | `/api/schema/` | OpenAPI 3.0 JSON schema |
| GET | `/api/docs/` | Swagger UI |

---

## 4. Workflows

### 4.1 Complete Service Lifecycle State Machine

```
                    ┌──────────────┐
                    │   waiting    │
                    └──────┬───────┘
                           │ assign_mechanic
                    ┌──────▼───────┐
              ┌────>│ in_progress  │<────┐
              │     └──┬───────┬───┘     │
              │        │       │         │
         rework   wait_for  request      │
         required  parts     QC          │
              │     │       │            │
              │ ┌───▼────┐  │            │
              │ │waiting_ │  │            │
              │ │for_parts│  │            │
              │ └───┬─────┘  │            │
              │     │ resume │            │
              │     └────────┘            │
              │     ┌──────▼────────┐     │
              └─────│  rework_required    │
                    └────────────────┘     │
                                           │
                    ┌──────────────┐        │
                    │  qc_pending  │        │
                    └──────┬───────┘        │
                           │ qc approved    │
                    ┌──────▼───────┐        │
                    │ready_for_bill│        │
                    └──────┬───────┘        │
                           │ payment done   │
                    ┌──────▼───────────┐    │
                    │ready_for_delivery│    │
                    └──────┬───────────┘    │
                           │ deliver        │
                    ┌──────▼───────┐        │
                    │  delivered   │ (terminal)
                    └──────────────┘

  waiting ───────────────────────────> cancelled (terminal)
  in_progress ───────────────────────> cancelled (terminal)
  waiting_for_parts ─────────────────> cancelled (terminal)
  ready_for_bill ────────────────────> cancelled (if no bill exists) (terminal)
```

### 4.2 Service Advisor Workflow

```
1. Walk-in customer arrives
2. Search/create customer → POST /api/v1/customers/
3. Register/create vehicle → POST /api/v1/vehicles/
4. Create service job → POST /api/v1/service-jobs/
   (optionally assign mechanic, or leave unassigned)
5. If mechanic not assigned: PATCH .../assign_mechanic/
6. Monitor job progress on dashboard
7. If needed: PATCH .../change_mechanic/ or PATCH .../status/
```

### 4.3 Mechanic Workflow

```
1. Login → view assigned jobs → GET /api/v1/service-jobs/
2. Select a job → GET /api/v1/service-jobs/{id}/
3. Add service work items → POST /api/v1/works/
4. Update work status as completed → PATCH /api/v1/works/{id}/status/
5. Add parts consumed → POST /api/v1/parts-used/
   (stock auto-reduces atomically)
6. When all work done:
   PATCH /api/v1/service-jobs/{id}/status/ → "qc_pending"
7. If rework required (QC failed):
   Fix issues, update work, then
   PATCH /api/v1/service-jobs/{id}/status/ → "in_progress"
   → repeat from step 3
```

### 4.4 Cashier Workflow

```
1. View jobs ready for billing (status=ready_for_bill):
   GET /api/v1/service-jobs/?status=ready_for_bill
2. Create bill → POST /api/v1/bills/
   (system auto-computes total_amount)
3. Receive payment → POST /api/v1/payments/
   (if fully paid: status → ready_for_delivery)
4. Complete delivery → POST /api/v1/delivery/
   (status → delivered, terminal)
```

### 4.5 Admin Workflow

```
1. View dashboard → GET /api/v1/dashboard/summary/
2. Manage users/mechanics → /api/v1/users/, /api/v1/mechanics/
3. Manage inventory → /api/v1/spare-parts/
4. Perform quality checks → POST /api/v1/quality-checks/
5. View reports → /api/v1/reports/*/
```

---

## 5. Database Flow

### 5.1 Entity Relationship (Simplified)

```
┌────────────┐       ┌──────────────┐
│  Customer  │1───*>│   Vehicle     │
└────────────┘       └──────┬───────┘
                            │
                            │1
                            │
                      ┌─────▼────────┐
                      │  ServiceJob  │──────>* ServiceWork
                      │  (core entity)│──────>* PartUsed
                      └──┬───────────┘       │
                         │1                  └──* SparePart
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼───┐ ┌───▼────┐
         │Quality │ │ Bill  │ │Delivery │
         │ Check  │ └───┬───┘ └────────┘
         └────────┘     │1
                        │
                   ┌────▼────┐
                   │ Payment │*
                   └─────────┘
```

### 5.2 Core Data Flow for a Service Job

```
Step 1: Create Service Job
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/service-jobs/
  → ServiceJob.job_number auto-generated (SJ-YYYY-XXXXX)
  → ServiceJob.status = "waiting" (or "in_progress" if mechanic assigned)
  → Vehicle found by FK, Customer accessed via vehicle.customer

Step 2: Assign Mechanic
─────────────────────────────────────────────────────────
  Flutter → PATCH /api/v1/service-jobs/{id}/assign_mechanic/
  → ServiceJob.assigned_mechanic = User (role=mechanic)
  → ServiceJob.status → "in_progress" (if was "waiting")

Step 3: Add Service Work
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/works/ (multiple times)
  → ServiceWork created, linked to ServiceJob via FK
  → labour_charge stored per work item

Step 4: Consume Parts
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/parts-used/
  → PartUsed created (price snapshot from SparePart.selling_price)
  → SparePart.stock_quantity -= quantity (atomic, select_for_update)
  → StockMovement created (type="out", reference_type="service_job")

Step 5: Request QC
─────────────────────────────────────────────────────────
  Flutter → PATCH /api/v1/service-jobs/{id}/status/
  → ServiceJob.status → "qc_pending"

Step 6: Quality Check
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/quality-checks/
  → QualityCheck created, linked to ServiceJob (OneToOne)
  → If approved: ServiceJob.status → "ready_for_bill"
  → If rejected: ServiceJob.status → "rework_required"

Step 7: Billing
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/bills/
  → Bill created, invoice_number auto-generated (INV-YYYY-XXXXX)
  → total_amount = labour_charge + parts_charge + tax - discount
  → labour from bill (not auto-summed from works)
  → parts from bill (not auto-summed from parts_used)
  → payment_status = "pending"

Step 8: Payment
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/payments/
  → Payment created, linked to Bill via FK
  → Bill.payment_status recalculated:
      total_paid >= bill.total → "paid"
      total_paid > 0 → "partial"
  → If "paid": ServiceJob.status → "ready_for_delivery"

Step 9: Delivery
─────────────────────────────────────────────────────────
  Flutter → POST /api/v1/delivery/
  → Delivery created, linked to ServiceJob via OneToOne
  → ServiceJob.status → "delivered" (terminal)
```

### 5.3 Stock Movement Journal

Every stock change generates a `StockMovement` record:

| Event | movement_type | reference_type | Effect on stock |
|-------|--------------|---------------|----------------|
| Purchase (add_stock) | `in` | `purchase` | +quantity |
| Adjustment (reduce_stock) | `out` | `adjustment` | -quantity |
| Part consumed on job | `out` | `service_job` | -quantity |
| PartUsed deleted | `in` | `service_job` | +quantity (restore) |

### 5.4 Sequential Code Generation

Both `job_number` (SJ-2026-00001) and `invoice_number` (INV-2026-00001) are generated using a thread-safe `SequenceCounter` model with `select_for_update()`:

```
Prefix: "SJ" or "INV"
Year: current year (2026)
Format: {PREFIX}-{YEAR}-{PADDED_SEQUENCE}
Example: SJ-2026-00042
```

---

## 6. Error Handling & Response Format

### 6.1 Success Response Format

All list endpoints return paginated responses:
```json
{
  "count": 42,
  "next": "http://.../?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### 6.2 Error Response Format

```json
// Validation Error (400)
{
  "field_name": ["This field is required."],
  "non_field_errors": ["..."]
}

// Authentication Error (401)
{
  "detail": "Given token not valid for any token type"
}

// Permission Error (403)
{
  "detail": "You do not have permission to perform this action."
}

// Not Found (404)
{
  "detail": "Not found."
}

// Business Logic / Conflict (409)
{
  "detail": "Cannot cancel a job that already has a bill."
}

// Validation Error (400)
{
  "detail": "Cannot move job from 'waiting' to 'delivered'."
}

// Stock Error (400)
{
  "detail": "Insufficient stock. Available: 2.00, Requested: 5.00"
}
```

### 6.3 Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | GET, PUT, PATCH success |
| 201 | Created | POST success |
| 204 | No Content | DELETE success |
| 400 | Bad Request | Validation error, invalid transition, insufficient stock |
| 401 | Unauthorized | Missing/invalid JWT |
| 403 | Forbidden | Wrong role for endpoint |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Business rule violation (e.g., deactivate mechanic with active jobs, cancel job with bill) |

---

## 7. Pagination & Filtering

### 7.1 Pagination

Default page size: **25**. Controlled by `?page=` and `?page_size=`:
```
GET /api/v1/customers/?page=2&page_size=10
```

### 7.2 Search

Available on list endpoints via `?search=`:
```
GET /api/v1/customers/?search=amit
GET /api/v1/vehicles/?search=KA-01
GET /api/v1/service-jobs/?search=Swift
```

Searches against: name, phone, email (customers) / vehicle_number, brand, model (vehicles) / job_number, complaint (jobs).

### 7.3 Ordering

```
GET /api/v1/customers/?ordering=name
GET /api/v1/customers/?ordering=-created_at
```

### 7.4 Filtering

```
GET /api/v1/service-jobs/?status=qc_pending
GET /api/v1/service-jobs/?assigned_mechanic=5
GET /api/v1/vehicles/?customer=1
GET /api/v1/bills/?payment_status=pending
GET /api/v1/delivery/delivered/?date=2026-07-08
GET /api/v1/spare-parts/low_stock/
```

---

## 8. Integration Checklist

### Phase 1: Auth & Setup
- [ ] Implement login screen → `POST /api/v1/auth/login/`
- [ ] Store tokens in `flutter_secure_storage`
- [ ] Decode JWT to extract `role` for navigation
- [ ] Add JWT interceptor (auto-refresh on 401)
- [ ] Build role-based navigation shell

### Phase 2: Customer & Vehicle Management
- [ ] Customer list with search → `GET /api/v1/customers/?search=`
- [ ] Customer create/edit → `POST/PUT /api/v1/customers/`
- [ ] Vehicle list by customer → `GET /api/v1/customers/{id}/vehicles/`
- [ ] Vehicle create/edit → `POST/PUT /api/v1/vehicles/`

### Phase 3: Service Job Lifecycle
- [ ] Create service job → `POST /api/v1/service-jobs/`
- [ ] List jobs (filtered by status) → `GET /api/v1/service-jobs/?status=`
- [ ] Job detail view → `GET /api/v1/service-jobs/{id}/`
- [ ] Assign/change mechanic → `PATCH .../assign_mechanic/`, `PATCH .../change_mechanic/`
- [ ] Update job status → `PATCH .../status/`

### Phase 4: Mechanic Module
- [ ] View assigned jobs (auto-filtered by backend)
- [ ] Add/edit/delete service work → CRUD `/api/v1/works/`
- [ ] Update work status → `PATCH /api/v1/works/{id}/status/`
- [ ] Add/delete parts used → `POST/DELETE /api/v1/parts-used/`
- [ ] Request QC → `PATCH /api/v1/service-jobs/{id}/status/`

### Phase 5: Admin Module
- [ ] QC submission → `POST /api/v1/quality-checks/`
- [ ] Inventory management → CRUD `/api/v1/spare-parts/`
- [ ] Add/reduce stock → `POST .../add_stock/`, `POST .../reduce_stock/`
- [ ] Low stock alerts → `GET /api/v1/spare-parts/low_stock/`
- [ ] User management → CRUD `/api/v1/users/`
- [ ] Mechanic management → CRUD `/api/v1/mechanics/`
- [ ] Dashboard summary → `GET /api/v1/dashboard/summary/`
- [ ] Reports → `GET /api/v1/reports/*/`

### Phase 6: Cashier Module
- [ ] View jobs ready for billing → `GET /api/v1/service-jobs/?status=ready_for_bill`
- [ ] Create/edit bill → `POST/PUT /api/v1/bills/`
- [ ] Record payment → `POST /api/v1/payments/`
- [ ] View pending payments → `GET /api/v1/payments/pending/`
- [ ] Complete delivery → `POST /api/v1/delivery/`
- [ ] View delivery ready/delivered → `GET /api/v1/delivery/ready/`, `GET /api/v1/delivery/delivered/`

### Phase 7: History & Polish
- [ ] Vehicle service history → `GET /api/v1/vehicles/{id}/history/`
- [ ] Customer service history → `GET /api/v1/customers/{id}/history/`
- [ ] Search by vehicle number → `GET /api/v1/vehicles/history/?vehicle_number=`
- [ ] Error handling throughout (toast/snackbar on 4xx/5xx)
- [ ] Pull-to-refresh on all list screens

---

## Quick Reference: Endpoint Summary Table

| # | Module | Endpoints | Primary Role |
|---|--------|-----------|-------------|
| 1 | Auth | `/auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/me/` | All |
| 2 | Users | `/users/` (CRUD + activate/deactivate) | Admin |
| 3 | Customers | `/customers/` (CRUD + vehicles sub-resource) | Advisor |
| 4 | Vehicles | `/vehicles/` (CRUD) | Advisor |
| 5 | Mechanics | `/mechanics/` (CRUD + activate/deactivate + assigned_vehicles) | Admin |
| 6 | Inventory | `/spare-parts/` (CRUD + add_stock, reduce_stock, low_stock, stock_history) | Admin |
| 7 | Service Jobs | `/service-jobs/` (CRUD + status, assign_mechanic, change_mechanic) | Advisor |
| 8 | Service Work | `/works/` (CRUD + status) | Mechanic |
| 9 | Parts Used | `/parts-used/` (CRUD) | Mechanic |
| 10 | Quality Check | `/quality-checks/` (CRUD) | Admin |
| 11 | Billing | `/bills/` (CRUD) | Cashier |
| 12 | Payments | `/payments/` (CRUD + pending) | Cashier |
| 13 | Delivery | `/delivery/` (CRUD + ready, delivered) | Cashier |
| 14 | History | `/vehicles/{id}/history/`, `/vehicles/history/`, `/customers/{id}/history/` | Advisor |
| 15 | Dashboard | `/dashboard/summary/` | Admin |
| 16 | Reports | `/reports/daily-revenue/`, `/reports/monthly-revenue/`, `/reports/completed-services/`, `/reports/mechanic-productivity/`, `/reports/spare-parts-usage/` | Admin |
| 17 | Health | `/health/` | No auth |
