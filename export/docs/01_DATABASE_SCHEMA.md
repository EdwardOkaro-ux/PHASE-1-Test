# AfroFreight Database Schema Documentation
## Multi-Tenant Logistics SaaS Platform

**Version:** 1.0  
**Date:** February 14, 2026  
**Database:** MongoDB  
**Total Collections:** 16

---

## Table of Contents
1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Core Tables](#core-tables)
3. [Shipment Tables](#shipment-tables)
4. [Trip Tables](#trip-tables)
5. [Financial Tables](#financial-tables)
6. [Fleet Tables](#fleet-tables)
7. [Authentication Tables](#authentication-tables)
8. [Sample Data Structures](#sample-data-structures)

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AFROFREIGHT DATABASE SCHEMA                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   TENANTS    │
                              │──────────────│
                              │ id (PK)      │
                              │ subdomain    │
                              │ company_name │
                              └──────┬───────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │    USERS     │          │   CLIENTS    │          │   VEHICLES   │
    │──────────────│          │──────────────│          │──────────────│
    │ id (PK)      │          │ id (PK)      │          │ id (PK)      │
    │ tenant_id(FK)│          │ tenant_id(FK)│          │ tenant_id(FK)│
    │ email        │          │ name         │          │ registration │
    │ role         │          │ credit_limit │          │ status       │
    └──────┬───────┘          └──────┬───────┘          └──────┬───────┘
           │                         │                         │
           │                         │                         ▼
           │                         │                  ┌──────────────────┐
           │                         │                  │VEHICLE_COMPLIANCE│
           │                         │                  │──────────────────│
           │                         │                  │ id (PK)          │
           │                         │                  │ vehicle_id (FK)  │
           │                         │                  │ item_type        │
           │                         │                  │ expiry_date      │
           │                         │                  └──────────────────┘
           │                         │
           │              ┌──────────┴──────────┐
           │              │                     │
           │              ▼                     ▼
           │       ┌──────────────┐      ┌──────────────┐
           │       │ CLIENT_RATES │      │  SHIPMENTS   │◄────────────────┐
           │       │──────────────│      │──────────────│                 │
           │       │ id (PK)      │      │ id (PK)      │                 │
           │       │ client_id(FK)│      │ tenant_id(FK)│                 │
           │       │ rate_type    │      │ client_id(FK)│                 │
           │       │ rate_value   │      │ trip_id (FK) │                 │
           │       └──────────────┘      │ status       │                 │
           │                             └──────┬───────┘                 │
           │                                    │                         │
           │                                    ▼                         │
           │                            ┌────────────────┐                │
           │                            │SHIPMENT_PIECES │                │
           │                            │────────────────│                │
           │                            │ id (PK)        │                │
           │                            │ shipment_id(FK)│                │
           │                            │ barcode        │                │
           │                            │ weight         │                │
           │                            │ loaded_at      │                │
           │                            └────────────────┘                │
           │                                                              │
           │    ┌──────────────┐                                          │
           │    │    TRIPS     │──────────────────────────────────────────┘
           │    │──────────────│
           │    │ id (PK)      │
           │    │ tenant_id(FK)│
           │    │ trip_number  │◄──────────┐
           │    │ vehicle_id   │           │
           │    │ driver_id    │           │
           │    │ status       │           │
           │    └──────┬───────┘           │
           │           │                   │
           │           ▼                   │
           │    ┌──────────────┐           │
           │    │TRIP_EXPENSES │           │
           │    │──────────────│           │
           │    │ id (PK)      │           │
           │    │ trip_id (FK) │           │
           │    │ category     │           │
           │    │ amount       │           │
           │    └──────────────┘           │
           │                               │
           │    ┌──────────────┐           │
           │    │   INVOICES   │───────────┘
           │    │──────────────│
           │    │ id (PK)      │
           │    │ tenant_id(FK)│
           │    │ client_id(FK)│
           │    │ trip_id (FK) │
           │    │ invoice_num  │
           │    │ status       │
           │    └──────┬───────┘
           │           │
           │           ├────────────────────┐
           │           ▼                    ▼
           │    ┌──────────────────┐ ┌──────────────┐
           │    │INVOICE_LINE_ITEMS│ │   PAYMENTS   │
           │    │──────────────────│ │──────────────│
           │    │ id (PK)          │ │ id (PK)      │
           │    │ invoice_id (FK)  │ │ tenant_id(FK)│
           │    │ shipment_id (FK) │ │ client_id(FK)│
           │    │ description      │ │ invoice_id   │
           │    │ amount           │ │ amount       │
           │    └──────────────────┘ └──────────────┘
           │
           │    ┌──────────────┐      ┌──────────────────┐
           │    │   DRIVERS    │──────│DRIVER_COMPLIANCE │
           │    │──────────────│      │──────────────────│
           │    │ id (PK)      │      │ id (PK)          │
           │    │ tenant_id(FK)│      │ driver_id (FK)   │
           │    │ name         │      │ item_type        │
           │    │ phone        │      │ expiry_date      │
           │    │ status       │      └──────────────────┘
           │    └──────────────┘
           │
           ▼
    ┌──────────────────┐
    │  USER_SESSIONS   │
    │──────────────────│
    │ user_id (FK)     │
    │ session_token    │
    │ expires_at       │
    └──────────────────┘
```

---

## Core Tables

### 1. tenants
Primary table for multi-tenant isolation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique tenant identifier |
| subdomain | string | UNIQUE, NOT NULL | Tenant's subdomain (e.g., "acme") |
| company_name | string | NOT NULL | Display name |
| logo_url | string | NULLABLE | Company logo URL |
| primary_color | string | DEFAULT "#27AE60" | Brand color |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `subdomain` (unique)

---

### 2. users
User accounts within tenants.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique user identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| name | string | NOT NULL | Full name |
| email | string (EmailStr) | NOT NULL | Email address |
| role | enum | NOT NULL | owner, manager, warehouse, finance, driver |
| phone | string | NULLABLE | Phone number |
| status | enum | DEFAULT "active" | active, invited, suspended |
| last_login | datetime | NULLABLE | Last login timestamp |
| picture | string | NULLABLE | Profile picture URL (from OAuth) |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `tenant_id`
- `email` (unique per tenant)

---

### 3. clients
Customer/shipper accounts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique client identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| name | string | NOT NULL | Client company name |
| phone | string | NULLABLE | Phone number |
| email | string | NULLABLE | Email address |
| whatsapp | string | NULLABLE | WhatsApp number |
| credit_limit | float | DEFAULT 0.0 | Credit limit amount |
| payment_terms_days | int | DEFAULT 30 | Payment terms in days |
| default_currency | string | DEFAULT "ZAR" | Currency code |
| status | enum | DEFAULT "active" | active, inactive |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `tenant_id`
- `name`

---

### 4. client_rates
Custom pricing per client.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique rate identifier |
| client_id | string | FOREIGN KEY → clients.id | Parent client |
| rate_type | enum | NOT NULL | per_kg, per_cbm, flat_rate, custom |
| rate_value | float | NOT NULL | Rate amount |
| effective_from | string | NULLABLE | Start date (YYYY-MM-DD) |
| notes | string | NULLABLE | Additional notes |
| created_by | string | FOREIGN KEY → users.id | User who created |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `client_id`

---

## Shipment Tables

### 5. shipments
Main shipment records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique shipment identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| client_id | string | FOREIGN KEY → clients.id | Shipper/customer |
| trip_id | string | FOREIGN KEY → trips.id, NULLABLE | Assigned trip |
| description | string | NOT NULL | Cargo description |
| destination | string | NOT NULL | Delivery destination |
| total_pieces | int | DEFAULT 1 | Number of pieces |
| total_weight | float | NOT NULL | Total weight (kg) |
| total_cbm | float | NULLABLE | Total volume (m³) |
| status | enum | DEFAULT "warehouse" | warehouse, staged, loaded, in_transit, delivered |
| created_by | string | FOREIGN KEY → users.id | User who created |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `tenant_id`
- `client_id`
- `trip_id`
- `status`

---

### 6. shipment_pieces
Individual pieces within shipments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique piece identifier |
| shipment_id | string | FOREIGN KEY → shipments.id | Parent shipment |
| piece_number | int | NOT NULL | Sequence number (1, 2, 3...) |
| barcode | string | UNIQUE | Scannable barcode |
| weight | float | NOT NULL | Piece weight (kg) |
| length_cm | float | NULLABLE | Length dimension |
| width_cm | float | NULLABLE | Width dimension |
| height_cm | float | NULLABLE | Height dimension |
| photo_url | string | NULLABLE | Photo of the piece |
| loaded_at | datetime | NULLABLE | When loaded onto vehicle |

**Barcode Format:**
- Unassigned: `TEMP-{random}-{piece_number}`
- Assigned to trip: `{trip_number}-{shipment_seq:03d}-{piece_number}`

**Indexes:**
- `shipment_id`
- `barcode` (unique)

---

## Trip Tables

### 7. trips
Delivery trips/routes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique trip identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| trip_number | string | UNIQUE per tenant | Trip reference (e.g., "S27") |
| route | array[string] | DEFAULT [] | Ordered stops list |
| departure_date | string | NOT NULL | Departure date (YYYY-MM-DD) |
| vehicle_id | string | FOREIGN KEY → vehicles.id, NULLABLE | Assigned vehicle |
| driver_id | string | FOREIGN KEY → drivers.id, NULLABLE | Assigned driver |
| notes | string | NULLABLE | Additional notes |
| status | enum | DEFAULT "planning" | planning, loading, in_transit, delivered, closed |
| locked_at | datetime | NULLABLE | When trip was locked |
| created_by | string | FOREIGN KEY → users.id | User who created |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Business Rules:**
- `trip_number` must be unique within tenant
- Once status = "closed", trip is locked (no modifications)
- `locked_at` is set when status changes to "closed"

**Indexes:**
- `tenant_id`
- `trip_number` (unique per tenant)
- `status`

---

### 8. trip_expenses
Expenses incurred during trips.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique expense identifier |
| trip_id | string | FOREIGN KEY → trips.id | Parent trip |
| category | enum | NOT NULL | fuel, tolls, border_fees, repairs, food, accommodation, other |
| amount | float | NOT NULL | Expense amount |
| currency | string | DEFAULT "ZAR" | Currency code |
| expense_date | string | NOT NULL | Date of expense (YYYY-MM-DD) |
| description | string | NULLABLE | Expense description |
| receipt_url | string | NULLABLE | Receipt image URL |
| created_by | string | FOREIGN KEY → users.id | User who recorded |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `trip_id`

---

## Financial Tables

### 9. invoices
Customer invoices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique invoice identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| invoice_number | string | UNIQUE per tenant | Auto-generated (INV-YYYY-NNN) |
| client_id | string | FOREIGN KEY → clients.id | Billed customer |
| trip_id | string | FOREIGN KEY → trips.id, NULLABLE | Related trip |
| subtotal | float | NOT NULL | Sum of line items |
| adjustments | float | DEFAULT 0 | Discounts/additions |
| total | float | COMPUTED | subtotal + adjustments |
| currency | string | DEFAULT "ZAR" | Currency code |
| status | enum | DEFAULT "draft" | draft, sent, paid, overdue |
| due_date | string | COMPUTED | Based on client payment_terms_days |
| sent_at | datetime | NULLABLE | When invoice was sent |
| sent_by | string | FOREIGN KEY → users.id, NULLABLE | User who sent |
| paid_at | datetime | NULLABLE | When marked paid |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Auto-Generation Rules:**
- `invoice_number`: INV-{YYYY}-{NNN} where NNN is sequential per year
- `due_date`: created_at + client.payment_terms_days

**Indexes:**
- `tenant_id`
- `invoice_number` (unique per tenant)
- `client_id`
- `status`

---

### 10. invoice_line_items
Individual items on invoices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique line item identifier |
| invoice_id | string | FOREIGN KEY → invoices.id | Parent invoice |
| shipment_id | string | FOREIGN KEY → shipments.id, NULLABLE | Related shipment |
| description | string | NOT NULL | Line item description |
| quantity | int | DEFAULT 1 | Quantity |
| weight | float | NULLABLE | Weight if applicable |
| rate | float | NOT NULL | Unit rate |
| amount | float | COMPUTED | quantity × rate (or weight × rate) |

**Indexes:**
- `invoice_id`

---

### 11. payments
Payment records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique payment identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| client_id | string | FOREIGN KEY → clients.id | Paying customer |
| invoice_id | string | FOREIGN KEY → invoices.id, NULLABLE | Related invoice |
| amount | float | NOT NULL | Payment amount |
| payment_date | string | NOT NULL | Date of payment (YYYY-MM-DD) |
| payment_method | enum | NOT NULL | cash, bank_transfer, mobile_money, other |
| reference | string | NULLABLE | Payment reference number |
| notes | string | NULLABLE | Additional notes |
| created_by | string | FOREIGN KEY → users.id | User who recorded |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Business Rules:**
- When payment covers full invoice amount, invoice.status → "paid"

**Indexes:**
- `tenant_id`
- `client_id`
- `invoice_id`

---

## Fleet Tables

### 12. vehicles
Fleet vehicles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique vehicle identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| name | string | NOT NULL | Vehicle name/description |
| registration_number | string | NOT NULL | License plate |
| vin | string | NULLABLE | Vehicle Identification Number |
| make | string | NULLABLE | Manufacturer (e.g., MAN) |
| model | string | NULLABLE | Model name |
| year | int | NULLABLE | Manufacturing year |
| max_weight_kg | float | NULLABLE | Max cargo weight (kg) |
| max_volume_cbm | float | NULLABLE | Max cargo volume (m³) |
| status | enum | DEFAULT "available" | available, in_transit, repair, inactive |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `tenant_id`
- `registration_number`
- `status`

---

### 13. vehicle_compliance
Vehicle compliance/document tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique compliance identifier |
| vehicle_id | string | FOREIGN KEY → vehicles.id | Parent vehicle |
| item_type | enum | NOT NULL | license_disk, insurance, roadworthy, service, custom |
| item_label | string | NULLABLE | Custom label (for "custom" type) |
| expiry_date | string | NOT NULL | Expiration date (YYYY-MM-DD) |
| reminder_days_before | int | DEFAULT 30 | Days before expiry to remind |
| notify_channels | array[string] | DEFAULT ["bell"] | Notification channels |
| provider | string | NULLABLE | Insurance/service provider |
| policy_number | string | NULLABLE | Policy or reference number |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `vehicle_id`
- `expiry_date`

---

### 14. drivers
Driver records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique driver identifier |
| tenant_id | string | FOREIGN KEY → tenants.id | Parent tenant |
| name | string | NOT NULL | Driver's full name |
| phone | string | NOT NULL | Phone number |
| email | string | NULLABLE | Email address |
| id_passport_number | string | NULLABLE | ID or passport number |
| nationality | string | NULLABLE | Country of nationality |
| status | enum | DEFAULT "available" | available, on_trip, on_leave, inactive |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `tenant_id`
- `phone`
- `status`

---

### 15. driver_compliance
Driver compliance/document tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | string (UUID) | PRIMARY KEY | Unique compliance identifier |
| driver_id | string | FOREIGN KEY → drivers.id | Parent driver |
| item_type | enum | NOT NULL | license, work_permit, medical, prdp, custom |
| item_label | string | NULLABLE | Custom label (for "custom" type) |
| expiry_date | string | NOT NULL | Expiration date (YYYY-MM-DD) |
| reminder_days_before | int | DEFAULT 30 | Days before expiry to remind |
| notify_channels | array[string] | DEFAULT ["bell"] | Notification channels |
| license_number | string | NULLABLE | License number |
| issuing_country | string | NULLABLE | Country that issued document |
| created_at | datetime | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `driver_id`
- `expiry_date`

---

## Authentication Tables

### 16. user_sessions
Active user sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | string | FOREIGN KEY → users.id | Session owner |
| session_token | string | UNIQUE | Session identifier |
| expires_at | datetime | NOT NULL | Session expiration (7 days default) |

**Indexes:**
- `session_token` (unique)
- `expires_at` (TTL index for auto-cleanup)

---

## Sample Data Structures

### Tenant Example
```json
{
  "id": "tenant-abc123",
  "subdomain": "acmefreight",
  "company_name": "Acme Freight Services",
  "logo_url": "https://example.com/logo.png",
  "primary_color": "#27AE60",
  "created_at": "2026-02-14T00:00:00Z"
}
```

### Shipment with Pieces Example
```json
{
  "shipment": {
    "id": "c0e023d0-8abb-40fc-9afc-e063b479afa7",
    "tenant_id": "tenant-abc123",
    "client_id": "client-linda",
    "trip_id": "trip-s27",
    "description": "Wine (Sedgwicks Old Brown)",
    "destination": "Kenya",
    "total_pieces": 4,
    "total_weight": 74.0,
    "status": "staged",
    "created_by": "user-123",
    "created_at": "2026-02-13T23:55:10Z"
  },
  "pieces": [
    {"id": "piece-1", "shipment_id": "...", "piece_number": 1, "barcode": "S27-001-1", "weight": 18.5, "loaded_at": "2026-02-14T00:05:31Z"},
    {"id": "piece-2", "shipment_id": "...", "piece_number": 2, "barcode": "S27-001-2", "weight": 18.5, "loaded_at": null},
    {"id": "piece-3", "shipment_id": "...", "piece_number": 3, "barcode": "S27-001-3", "weight": 18.5, "loaded_at": null},
    {"id": "piece-4", "shipment_id": "...", "piece_number": 4, "barcode": "S27-001-4", "weight": 18.5, "loaded_at": null}
  ]
}
```

### Trip with Expenses Example
```json
{
  "trip": {
    "id": "4869a266-8326-4b12-8398-2c58dbe847df",
    "tenant_id": "tenant-abc123",
    "trip_number": "S27",
    "route": ["Johannesburg", "Nairobi"],
    "departure_date": "2026-02-15",
    "vehicle_id": null,
    "driver_id": null,
    "status": "planning",
    "locked_at": null,
    "created_by": "user-123",
    "created_at": "2026-02-13T23:55:10Z"
  },
  "expenses": [
    {"id": "exp-1", "trip_id": "...", "category": "fuel", "amount": 5000.00, "currency": "ZAR", "expense_date": "2026-02-15"},
    {"id": "exp-2", "trip_id": "...", "category": "tolls", "amount": 850.00, "currency": "ZAR", "expense_date": "2026-02-15"}
  ]
}
```

### Invoice Example
```json
{
  "id": "inv-abc123",
  "tenant_id": "tenant-abc123",
  "invoice_number": "INV-2026-001",
  "client_id": "client-linda",
  "trip_id": "trip-s27",
  "subtotal": 5000.00,
  "adjustments": -500.00,
  "total": 4500.00,
  "currency": "ZAR",
  "status": "sent",
  "due_date": "2026-03-15",
  "sent_at": "2026-02-14T10:00:00Z",
  "sent_by": "user-123",
  "paid_at": null,
  "created_at": "2026-02-14T09:00:00Z"
}
```

---

## Enums Reference

### User Roles
- `owner` - Full access
- `manager` - Operational management
- `warehouse` - Warehouse operations
- `finance` - Financial access
- `driver` - Driver-specific access

### Shipment Status
- `warehouse` - In warehouse
- `staged` - Assigned to trip, ready for loading
- `loaded` - All pieces loaded
- `in_transit` - On the road
- `delivered` - Delivered to destination

### Trip Status
- `planning` - Trip being planned
- `loading` - Loading in progress
- `in_transit` - On the road
- `delivered` - Arrived at destination
- `closed` - Trip closed (locked)

### Invoice Status
- `draft` - Being prepared
- `sent` - Sent to customer
- `paid` - Fully paid
- `overdue` - Past due date

### Payment Methods
- `cash`
- `bank_transfer`
- `mobile_money`
- `other`

### Vehicle Status
- `available` - Ready for assignment
- `in_transit` - On a trip
- `repair` - Under maintenance
- `inactive` - Not in use

### Driver Status
- `available` - Ready for assignment
- `on_trip` - Currently on a trip
- `on_leave` - On leave
- `inactive` - Not active

---

*Document generated: February 14, 2026*
