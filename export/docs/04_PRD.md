# AfroFreight Logistics SaaS Platform - PRD

## Original Problem Statement
Build a multi-tenant logistics SaaS platform for African freight companies with:
- Multi-tenant architecture with subdomain-based isolation
- Core database tables: tenants, users, clients, client_rates, shipments, shipment_pieces, trips
- User roles: owner, manager, warehouse, finance, driver
- Barcode generation: [trip_number]-[shipment_seq]-[piece_number] or TEMP-[random]
- All queries auto-filtered by tenant_id

## User Personas
1. **Business Owner** - Full access to all features, settings, and team management
2. **Operations Manager** - Manages shipments, trips, and clients
3. **Warehouse Staff** - Uses barcode scanner to track pieces
4. **Finance Team** - Views client rates and payment terms
5. **Drivers** - Access trip details and delivery information

## Core Requirements (Static)
- Multi-tenant data isolation
- Emergent Google OAuth authentication
- Role-based access control
- Dark/light theme toggle
- Mobile-friendly barcode scanner
- Shipment tracking with piece-level granularity
- Trip management with shipment assignment
- Client management with custom rates

## What's Been Implemented (Feb 2026)
### Backend
- ✅ FastAPI with MongoDB
- ✅ All 11 database collections with proper indexes
- ✅ Emergent Google OAuth integration
- ✅ Session management with 7-day expiry
- ✅ Multi-tenant middleware (auto tenant_id filtering)
- ✅ CRUD APIs for: tenants, users, clients, client_rates, shipments, shipment_pieces, trips, trip_expenses
- ✅ Dashboard statistics endpoint
- ✅ Barcode scanning and piece loading APIs
- ✅ Assign shipment to trip with barcode regeneration
- ✅ **Enhanced Trip Model**: route (JSON array), vehicle_id, locked_at timestamp
- ✅ **Trip Expenses**: category enum (fuel/tolls/border_fees/repairs/food/accommodation/other), amount, currency
- ✅ **Trip Locking**: closed trips prevent shipment changes, only owner can modify locked trip expenses
- ✅ **Trip number uniqueness** validation per tenant
- ✅ **Invoices**: auto-generated invoice_number (INV-YYYY-NNN), status (draft/sent/paid/overdue), auto due_date calculation
- ✅ **Invoice Line Items**: quantity/weight × rate = amount, auto subtotal recalculation
- ✅ **Payments**: payment_method enum (cash/bank_transfer/mobile_money/other), auto-mark invoice as paid
- ✅ **Financial Summary**: totals by status, total outstanding, total received
- ✅ **Fleet Management**: vehicles (name, registration, VIN, make, model, year, capacity), drivers (name, phone, ID/passport)
- ✅ **Vehicle Compliance**: license_disk, insurance, roadworthy, service, custom items with expiry tracking
- ✅ **Driver Compliance**: license, work_permit, medical, prdp, custom items with expiry tracking
- ✅ **Compliance Reminders**: aggregation endpoint grouping items by urgency (overdue, due_this_week, due_this_month, upcoming)

### Frontend
- ✅ Landing page with Google OAuth
- ✅ Protected routes with session verification
- ✅ Dashboard with stats, status breakdown, recent shipments
- ✅ Clients page (CRUD, rates management)
- ✅ Shipments page (CRUD, piece management, barcode generation)
- ✅ **Enhanced Trips page** with route stops, expenses tracking, shipment assignment/unassignment
- ✅ Scanner page (camera simulation + manual entry)
- ✅ **Finance page** with invoices, line items, payments, summary cards
- ✅ Team page (user management, roles)
- ✅ Settings page (company branding, colors)
- ✅ Responsive sidebar navigation
- ✅ Theme toggle (light/dark)
- ✅ Toast notifications (sonner)
- ✅ **Fleet page** with tabs for Vehicles, Drivers, and Reminders
- ✅ Vehicle CRUD with compliance items management
- ✅ Driver CRUD with compliance items management
- ✅ Compliance reminders with urgency color-coding (red=overdue, orange=this week)
- ✅ Fleet navigation link in sidebar

## Prioritized Backlog

### P0 (Critical) - Done
- [x] Multi-tenant architecture
- [x] User authentication
- [x] Core CRUD operations
- [x] Barcode system

### P1 (High Priority) - Deferred
- [ ] WhatsApp notifications for shipment updates
- [ ] Actual camera barcode scanning (using device camera API)
- [ ] Invoice generation for shipments
- [ ] Driver mobile app view
- [ ] Bulk shipment import (CSV)

### P2 (Medium Priority)
- [ ] Real-time tracking with GPS
- [ ] Customer portal for shipment tracking
- [ ] Financial reports and analytics
- [ ] Automated rate calculations
- [ ] Document attachments (POD, invoices)

### P3 (Nice to Have)
- [ ] AI-powered insights
- [ ] Route optimization
- [ ] Integration with payment gateways
- [ ] Email notifications
- [ ] Multi-language support

## Technical Architecture
```
Frontend (React)
├── Contexts: ThemeContext, AuthContext
├── Components: Layout, ProtectedRoute, AuthCallback
├── Pages: Landing, Dashboard, Clients, Shipments, Trips, Scanner, Finance, Fleet, Team, Settings
└── UI: Shadcn components, Tailwind CSS

Backend (FastAPI)
├── Auth: Emergent Google OAuth, Session management
├── Models: Tenant, User, Client, ClientRate, Shipment, ShipmentPiece, Trip, Invoice, Payment, Vehicle, Driver
├── Middleware: CORS, Auth dependency
└── Database: MongoDB with Motor async driver

Database Collections:
- tenants (subdomain, company_name, branding)
- users (tenant_id, email, role, status)
- clients (tenant_id, name, rates, payment_terms)
- client_rates (client_id, rate_type, rate_value)
- shipments (tenant_id, client_id, trip_id, status)
- shipment_pieces (shipment_id, barcode, loaded_at)
- trips (tenant_id, trip_number (unique), route[], departure_date, vehicle_id, driver_id, locked_at)
- trip_expenses (trip_id, category, amount, currency, expense_date)
- invoices (tenant_id, invoice_number (unique), client_id, trip_id, status, subtotal, adjustments, total, due_date)
- invoice_line_items (invoice_id, shipment_id, description, quantity, weight, rate, amount)
- payments (tenant_id, client_id, invoice_id, amount, payment_date, payment_method, reference)
- vehicles (tenant_id, name, registration_number, vin, make, model, year, max_weight_kg, max_volume_cbm, status)
- vehicle_compliance (vehicle_id, item_type, item_label, expiry_date, reminder_days_before, provider, policy_number)
- drivers (tenant_id, name, phone, email, id_passport_number, nationality, status)
- driver_compliance (driver_id, item_type, item_label, expiry_date, reminder_days_before, license_number, issuing_country)
- user_sessions (user_id, session_token, expires_at)
```

## Next Tasks
1. Implement WhatsApp notifications using Twilio
2. Add actual camera barcode scanning using QuaggaJS or similar
3. Build driver-specific mobile view
4. Add bulk CSV import for shipments
5. Link vehicles/drivers to trips (assign vehicle and driver when creating trips)
6. Add document attachments (POD, compliance certificates)
7. Automated compliance expiry email reminders
