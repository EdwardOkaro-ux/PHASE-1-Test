# Servex Holdings Logistics SaaS Platform - PRD

## Original Problem Statement
Download SaaS project from GitHub (https://github.com/Philip92/SaaS-ERM-2) and set up email/password authentication.

## What's Been Implemented
- Multi-tenant logistics SaaS platform for African freight companies
- FastAPI backend with MongoDB
- React frontend with Tailwind CSS
- Email/Password Authentication (bcrypt + session tokens)
- Features: Shipments, Trips, Fleet, Invoices, Warehouse, Finance Hub, Team management

## Authentication System
- Email/Password login with bcrypt password hashing
- Session token-based authentication (7-day expiry)
- Default admin: admin@servex.com / Servex2026!

---

## Update: Feb 17, 2026 - Session 2

### Changes Made:
1. **Default Rate R36/kg**
   - Tenant settings now include default_rate_value (36.0) and default_rate_type (per_kg)
   - New clients auto-populate with tenant's default rate
   - All existing clients updated to R36/kg

2. **Scanner Page Removed**
   - Removed from navigation sidebar
   - Removed from all role permissions
   - Database permissions cleaned up

3. **CSV Import with Warehouse Selection**
   - Settings > Data > Import CSV now opens modal
   - Can select specific warehouse or alternate between all
   - Imported: 549 parcels to Johannesburg, 289 to Nairobi

4. **Notes & Mentions System**
   - New NotesPanel component (reusable across pages)
   - POST /api/notes - Create note with @mentions
   - GET /api/notes - List notes for entity
   - Automatic notification creation for mentioned users
   - Available for: warehouse, clients, finance, fleet, trips, loading

5. **Settings Persistence Fix**
   - Tenant schema updated to include all settings fields
   - Settings now persist when switching tabs

6. **Logo Flickering Fix**
   - Simplified logo rendering with CSS transitions
   - Added imageRendering: auto style

### Files Modified:
- `/app/backend/models/schemas.py` - Tenant & Client schemas with rate fields
- `/app/backend/routes/notes_routes.py` - NEW: Notes CRUD
- `/app/backend/routes/data_routes.py` - CSV import with warehouse_id param
- `/app/frontend/src/components/Layout.jsx` - Scanner removed
- `/app/frontend/src/components/NotesPanel.jsx` - NEW: Notes UI
- `/app/frontend/src/pages/Settings.jsx` - Import modal, scanner removed from permissions

---

## Update: Feb 17, 2026 - Session 1

### 1. Data Reset System
- POST /api/data/reset - Wipes all operational data (clients, trips, parcels, invoices, payments, expenses, notifications)
- Preserves: users, tenant settings, warehouses
- Owner-only access

### 2. Warehouse Management
- Full CRUD in Settings > Warehouses tab
- Fields: Name, Location, Contact Person, Phone, Status
- Default warehouses: Johannesburg Warehouse (South Africa), Nairobi Warehouse (Kenya)
- POST /api/warehouses/create-defaults endpoint

### 3. Multi-Currency System
- Settings > Currencies tab
- Base currency: ZAR (South African Rand)
- Preset exchange rates: KES (0.14), USD (18.5), GBP (23.2), EUR (20.1)
- Editable rates with real-time updates
- Add/Delete currencies (cannot delete base)

### 4. Recipient Details System
- "+ Add Recipient" button in Parcel Intake next to client selector
- Modal fields: Name, Phone, WhatsApp, Email, VAT Number, Shipping Address
- Recipients stored in recipients collection
- Auto-fills recipient field on save

### 5. Loading & Staging Page Rebuild
- Split-screen layout: Warehouse parcels (left) | Truck parcels (right)
- Trip dropdown (filters: planning, loading status)
- Warehouse dropdown filter
- Barcode scanner with Warehouse/Truck toggle
- Real-time counters: X in warehouse, Y on truck, Z total
- Mark Truck Loaded / Open Truck buttons

### 6. CSV Parcel Import
- Settings > Data tab > Import Parcels from CSV
- Auto-creates clients (case-insensitive matching)
- Alternates parcels between warehouses
- Skips rows with KG=0
- Calculates volumetric weight
- Creates barcode for each piece

### 7. Bug Fixes
- Trip dropdown now supports comma-separated status filter
- Fixed parcel intake NameError (missing imports)
- Fixed currency display empty array check

### Files Modified:
- `/app/backend/routes/data_routes.py` - New: Data reset, CSV import
- `/app/backend/routes/warehouse_routes.py` - Warehouse CRUD
- `/app/backend/routes/auth_routes.py` - Currency management
- `/app/backend/routes/recipient_routes.py` - New: Recipient CRUD
- `/app/backend/routes/trip_routes.py` - Comma-separated status filter
- `/app/frontend/src/pages/Settings.jsx` - New tabs: Warehouses, Currencies, Data
- `/app/frontend/src/pages/LoadingStaging.jsx` - Complete rebuild
- `/app/frontend/src/pages/ParcelIntake.jsx` - Add Recipient modal
- `/app/backend/models/schemas.py` - physical_address field

### Test Data:
- 549 parcels imported from CSV
- 51 clients auto-created
- 275 parcels in Johannesburg, 274 in Nairobi
- Total weight: 10,161.25 kg

## Previous Session (Feb 17, 2026)

### Settings, Team & Fleet Improvements (Latest)

**1. User Default Warehouse**
- Added "Default Warehouse" dropdown to Add/Edit User forms
- Fetches warehouses from GET /api/warehouses
- Saves as `default_warehouse` on user document
- Shown in Team table as new column

**2. Role-Based Page Visibility**
- New "Permissions" tab in Settings
- Grid showing roles (Owner, Manager, Warehouse, Finance, Driver) vs pages
- Owner can toggle which pages each role can access
- Saves to tenant settings (`role_permissions`)
- Layout.jsx filters nav items based on logged-in user's role

**3. Fleet Compliance Uploads**
- Added file upload field to compliance forms (PDF/images)
- Stores as base64: file_name, file_type, file_data
- Shows file icon next to compliance items with uploaded docs

**4. Compliance Reminders Sorted**
- New "All Compliance Items" view in Reminders tab
- Shows ALL vehicle + driver compliance in one list
- Sorted by expiry date ascending
- Color coding: Red = expired/within 30 days, Yellow = within 60 days, Green = more than 60 days

**Files Modified:**
- `/app/frontend/src/pages/Team.jsx` - Default warehouse dropdown
- `/app/frontend/src/pages/Settings.jsx` - Permissions tab with grid
- `/app/frontend/src/pages/Fleet.jsx` - File upload in compliance, reminders sorting
- `/app/frontend/src/components/Layout.jsx` - Role-based nav filtering
- `/app/backend/routes/auth_routes.py` - Permissions endpoints
- `/app/backend/routes/fleet_routes.py` - /compliance/all endpoint
- `/app/backend/models/schemas.py` - File fields on compliance models

### Trip Detail Improvements
1. Documents Tab for uploading trip documents
2. Invoice Review Workflow with Mark as Reviewed / Approve and Send
3. Team Mentions (@) on invoices creating notifications
4. Removed "Scan to Load" button
5. Parcel Tab: search bar, Total Amount column, totals row
6. Trip Actions Dropdown: Edit, Duplicate, Change Status, Download Summary, Close Trip, Delete Trip
7. Expenses Columns: Date, Category, Description, Supplier/Paid To, Amount, Receipt, Added By

### Clients Page Improvements
1. Renamed "Company Name" → "Client Name"
2. Removed Credit Limits
3. Added Financial Columns: Rate, Amount Owed, Total Spent
4. Sort Dropdown with 7 options
5. Trip Filter
6. Fixed Column Spacing

### Warehouse Page Improvements
1. Search by Client Name
2. Default Warehouse by User
3. Warehouse Name Header
4. Trip Filter Dropdown
5. Duplicate Detection

## Key API Endpoints
- `GET /api/tenant/permissions` - Get role-based page permissions
- `PUT /api/tenant/permissions` - Update permissions (owner only)
- `GET /api/compliance/all` - All compliance items sorted by expiry
- `POST /api/vehicles/{id}/compliance` - Add compliance with file upload
- `POST /api/drivers/{id}/compliance` - Add compliance with file upload
- `POST /api/trips/{trip_id}/documents` - Upload trip document
- `POST /api/invoices/{id}/mark-reviewed` - Mark invoice reviewed
- `POST /api/invoices/{id}/approve-and-send` - Approve invoice
- `GET /api/team-members` - List team for @mentions

## Default Credentials
- Email: admin@servex.com
- Password: Servex2026!

## Bug Fix - Parcel Intake (Feb 17, 2026)

### Issue
Critical bug where parcel intake was failing with "NameError: name 'create_audit_log' is not defined"

### Root Cause
Missing imports in `/app/backend/routes/shipment_routes.py`:
- `create_audit_log` was not imported from `models.schemas`
- `AuditAction` was not imported from `models.enums`

### Fix Applied
Updated line 11-12 of shipment_routes.py to include missing imports:
```python
from models.schemas import ..., create_audit_log
from models.enums import ShipmentStatus, AuditAction
```

### Verified Fixed
1. ✅ Save no longer shows false "failed" error
2. ✅ No duplicate parcels on retry
3. ✅ Multiple parcels save correctly
4. ✅ Photo upload works and displays in warehouse

## Testing Status
- All features tested: 100% pass rate (backend & frontend)
- Test files in `/app/backend/tests/`
- Test reports: `/app/test_reports/iteration_28.json` (latest)

## Deployment Status
- ✅ All frontend API calls use window.location.origin
- ✅ Backend .env configured
- ✅ Ready for deployment

---

## Update: Feb 19, 2026 - Bug Fixes & Schema Updates

### Critical Bug Fixes (All Resolved)
1. **Loading Page Wrong Parcels** - Fixed shipment routes to filter by trip_id and warehouse_id
2. **Invoice Number Display** - Shipments endpoint now enriches with invoice_number from invoice_line_items
3. **Client Rate Saving** - Working correctly, no issues found
4. **Invoice Line Items** - Working correctly, line items appear in invoice detail
5. **Invoice PDF Download** - Working correctly at GET /api/invoices/{id}/pdf
6. **Delete Invoice Drafts** - Added delete button in InvoiceEditor for draft invoices
7. **Trip Worksheet Export** - Fixed PDF generation at GET /api/finance/trip-worksheet/{trip_id}/pdf
8. **Warehouse Filtering** - Working correctly, "All Trips" shows all parcels in warehouse

### Schema Updates (All Implemented)
1. **Client Schema** - Added vat_number, billing_address fields to Client model and forms
2. **Parcel Numbering** - Added parcel_sequence, total_in_sequence fields to Shipment model
3. **Number Formatting** - Created /frontend/src/utils/formatting.js with utility functions
4. **Invoice Schema** - Added frozen client snapshot fields: client_name_snapshot, client_address_snapshot, client_vat_snapshot, client_phone_snapshot, client_email_snapshot

### Files Modified
- `/app/backend/routes/shipment_routes.py` - trip_id, warehouse_id filtering + invoice_number enrichment
- `/app/backend/routes/invoice_routes.py` - Client snapshot on creation, delete with adjustments cleanup, recalculate_invoice_totals helper
- `/app/backend/routes/finance_routes.py` - Trip worksheet PDF export endpoint
- `/app/backend/services/pdf_service.py` - Added missing imports
- `/app/backend/models/schemas.py` - Client, Shipment, Invoice model updates
- `/app/frontend/src/pages/LoadingStaging.jsx` - Invoice number display, strict trip filtering
- `/app/frontend/src/pages/Clients.jsx` - Form with vat_number, physical_address, billing_address
- `/app/frontend/src/pages/TripDetail.jsx` - Download worksheet handler
- `/app/frontend/src/components/InvoiceEditor.jsx` - Delete invoice function for drafts
- `/app/frontend/src/utils/formatting.js` - NEW: Number formatting utilities

### Testing
- ✅ All 11 backend tests pass
- ✅ All UI components verified working
- Test report: /app/test_reports/iteration_28.json

---

## Update: Feb 19, 2026 - Enhanced Invoice Workflow

### Features Implemented

**1. Add Parcels Directly to Invoices (Parcel Intake)**
- Toggle: "Add to Invoice" checkbox in Parcel Intake page
- Invoice selector with search by number or client name
- "Create New Invoice" option if none found
- Parcels automatically linked to invoice via invoice_id field
- Preview badge: "Will add parcels to INV-2026-0003"

**2. Smart Parcel Selection (Prevent Double-Invoicing)**
- New endpoint: GET /api/invoices/trip-parcels/{trip_id}
- Returns parcels with is_invoiced flag and invoice_number
- Already-invoiced parcels shown grayed out with invoice badge
- "Reassign to This Invoice" button for moving parcels
- Warning dialog before reassignment

**3. Payment Terms Per Invoice**
- Added payment_terms field to Invoice schema
- Options: full_on_receipt, 50_50, 30_70, net_30, custom
- Custom terms stored in payment_terms_custom field
- Terms displayed on invoice PDF with calculated amounts
- For 50/50: Shows "Due on receipt: R X" and "Due on delivery: R X"

**4. Enhanced Invoice Editor (80% Screen Width)**
- Expanded layout: 1/6 for list, 5/6 for editor
- Enhanced columns: Parcel#, Client, Recipient, Description, Dimensions, Qty, Weight, Rate, Amount
- Dimensions formatted to 3 decimals (L×W×H)
- Weight formatted to 4 decimals
- Checkboxes for batch line item selection
- "Adjust Rate for Selected" button
- Reverse Calculator: Enter target total, calculate required rate

**5. Invoice PDF Enhanced**
- Includes client snapshot: name, VAT, address, phone, email
- Recipient details section (Ship To) if different from client
- Payment terms with calculated payment schedule
- Dimensions column in line items table
- Item count and total quantity summary

### New API Endpoints
- GET /api/invoices/search - Search invoices by q, client_id, status
- GET /api/invoices/trip-parcels/{trip_id} - Parcels with invoice info
- POST /api/invoices/{id}/reassign-parcels - Move parcels between invoices

### Schema Updates
- Shipment: Added invoice_id, recipient_phone, recipient_vat, shipping_address, length_cm, width_cm, height_cm
- Invoice: Added payment_terms, payment_terms_custom
- InvoiceLineItemInput: Added parcel_label, client_name, recipient_name, dimensions

### Files Modified
- `/app/backend/routes/invoice_routes.py` - New endpoints, enhanced line items
- `/app/backend/services/pdf_service.py` - Complete rewrite with client/recipient details
- `/app/backend/models/schemas.py` - Shipment, Invoice, InvoiceLineItemInput updates
- `/app/frontend/src/pages/ParcelIntake.jsx` - Invoice assignment toggle and selector
- `/app/frontend/src/components/InvoiceEditor.jsx` - 80% width, enhanced columns, batch ops, reverse calc

### Testing
- ✅ All 20 backend tests pass
- ✅ All UI features verified working
- Test report: /app/test_reports/iteration_29.json
- Bug fixed: Route order issue with /invoices/search endpoint

---

## Update: Feb 19, 2026 - Session 5 - Warehouse & Loading/Unloading Features

### Completed Features

**1. Warehouse Page Client Filter**
- Added client dropdown filter to warehouse page header
- Filters parcels by selected client

**2. Parcel Verification System**
- Added "Verified" checkbox column to warehouse table
- Backend: PUT /api/shipments/{id}/verify endpoint
- Schema: Added verified, verified_by, verified_at fields to Shipment model
- Allows second-person verification of parcel details

**3. Parcel Sequence Display**
- Warehouse table now shows "X of Y" under parcel number
- Uses parcel_sequence and total_in_sequence fields

**4. Collection Workflow**
- "Mark Collected" button added to warehouse floating action bar
- Backend: PUT /api/warehouse/parcels/bulk-collect endpoint
- Only works for parcels with status "arrived"
- Updates status to "collected" with collected_by and collected_at

**5. Loading/Unloading Page Rebuilt**
- Mode toggle: Loading vs Unloading tabs
- Loading mode: Shows staged→loaded workflow
- Unloading mode: Shows in_transit→arrived workflow
- Manual move checkboxes in both tables
- "Load Selected" / "Return Selected" buttons
- "Mark Arrived" / "Return to Transit" buttons
- Summary cards with counts and weights

**6. Trip Status Action Buttons**
- TripDetail header shows contextual action buttons:
  - Planning → "Mark as Loading"
  - Loading → "Mark as In Transit"
  - In Transit → "Mark as Delivered"
  - Delivered → "Close Trip"

**7. Input Field Width Fixes (CRITICAL)**
- ParcelIntake: Qty, Weight, L, W, H inputs widened to min-w-[70-80px]
- All number inputs right-aligned (text-right class)
- InvoiceEditor: Qty, Rate, Amount inputs widened
- Adjustment amount inputs widened to w-[140px]

**8. Recipient Column in Add Parcels Modal**
- InvoiceEditor "Add Parcels from Trip" modal now shows Recipient column
- Dialog widened to max-w-2xl to fit new column

### New Status Colors
- `arrived`: bg-[#4A90D9] (blue)
- `collected`: bg-[#7B68EE] (purple)

### Schema Updates
- Shipment model: Added verified, verified_by, verified_at, collected, collected_by, collected_at

### Files Modified
- `/app/frontend/src/pages/Warehouse.jsx` - client filter, verification, collection
- `/app/frontend/src/pages/LoadingStaging.jsx` - complete rebuild with modes
- `/app/frontend/src/pages/TripDetail.jsx` - status action buttons
- `/app/frontend/src/pages/ParcelIntake.jsx` - input width fixes
- `/app/frontend/src/components/InvoiceEditor.jsx` - input widths, recipient column
- `/app/backend/routes/shipment_routes.py` - verify endpoint
- `/app/backend/routes/warehouse_routes.py` - bulk-collect endpoint
- `/app/backend/models/schemas.py` - Shipment verification/collection fields

### Testing
- ✅ Backend: 100% pass rate (16 tests)
- ✅ Frontend: 100% pass rate
- Test report: /app/test_reports/iteration_30.json

---

## Update: Feb 19, 2026 - Session 6 - Financial Features & Client Data Connections

### Completed Features

**1. Currency Toggle (ZAR ↔ KES)**
- Global toggle in Finance page header
- Exchange rate loaded from `/api/settings/currencies`
- Applies to all tabs: Client Statements, Trip Worksheets, Overdue
- Shows exchange rate info "(1 ZAR = 6.67 KES)"

**2. Invoice Amount Validation**
- Real-time calculation breakdown in Invoice Editor
- Shows: "Line items subtotal (N items): R X,XXX.XX"
- Each adjustment displayed with +/- sign
- Total validation before save (within 0.01 tolerance)

**3. Client Data Auto-Population**
- When selecting client in Invoice Editor:
  - Shows VAT number below dropdown
  - Shows default rate (R XX.XX/kg)
  - Auto-populates currency from client settings
- Updates line item rates when client rate changes

**4. WhatsApp Bulk Send**
- Overdue tab: Checkbox selection with "WhatsApp Selected (N)" button
- Trip Worksheets: "WhatsApp Selected" in batch actions bar
- Opens wa.me links sequentially (2s delay between each)
- Logs each send to `/api/invoices/{id}/log-whatsapp`
- Warning toast for clients without WhatsApp numbers

**5. Unsaved Changes Warning**
- Tracks dirty state comparing form vs initial values
- Yellow warning banner: "You have unsaved changes"
- Browser beforeunload warning on page close
- Dialog with Save/Discard/Stay options when navigating

**6. Invoice PDF Complete Data**
- FROM section: Company name, address, contact
- TO section: Client name, VAT, address, phone, email
- SHIP TO section: Recipient details (if different)
- Line items: Parcel #, description, dimensions (L×W×H), weight (4 decimals), qty, rate, amount
- Payment terms section with calculated amounts
- Banking details: FNB account info with invoice reference
- Footer with generation timestamp

### New API Endpoints
- `GET /api/settings/currencies` - Get exchange rates
- `PUT /api/settings/currencies` - Update exchange rates
- `POST /api/invoices/{id}/log-whatsapp` - Log WhatsApp sends

### Files Modified
- `/app/frontend/src/pages/Finance.jsx` - Currency toggle, fmtCurrency helper, WhatsApp bulk
- `/app/frontend/src/components/InvoiceEditor.jsx` - Calculation breakdown, unsaved changes
- `/app/backend/routes/finance_routes.py` - Currencies endpoints

### Testing
- ✅ Backend: 100% pass rate (11 tests)
- ✅ Frontend: 100% verified
- Test report: /app/test_reports/iteration_31.json

---

## Update: Feb 19, 2026 - Session: CSV Import/Export & Invoice Display Fixes

### Changes Made:

**1. Invoice Line Items Display Fix (CRITICAL)**
- Fixed QTY column showing weight instead of quantity
- Fixed Weight column not showing proper values
- Added smart display for legacy data (detects when quantity contains weight)
- Weight now formatted to 2 decimals (e.g., "17.50 kg")
- Dimensions formatted to 1 decimal when available
- Amount column min-width 140px for large values (up to 10 digits)
- Rate column max-width 80px (narrow for 3-digit values)
- Added `getItemDisplayValues()` helper function for legacy data handling

**2. Client CSV Import**
- Import Clients button in Settings → Data tab
- File picker accepts .csv files
- Auto-detects headers (case-insensitive check for "Client Name" or "name")
- Preview modal shows:
  - Total clients to import
  - First few rows preview
  - Duplicate detection warnings
- Creates clients with default values:
  - default_currency = "ZAR"
  - default_rate_type = "per_kg"
  - default_rate_value = 36.0
  - status = "active"
- Skips rows with empty/missing client name
- Success message shows count of imported clients and skipped rows

**3. Client CSV Export**
- Export Clients CSV button in Settings → Data tab
- Downloads CSV with headers:
  - Client Name, Phone, Email, VAT No, Physical Address, Billing Address, Rate
- Filename: `Servex_Clients_Export_YYYY-MM-DD.csv`
- Includes all active clients with their default_rate_value

**4. Parcel CSV Import with Preview**
- Import Parcels button in Settings → Data tab
- Expected CSV columns: `Sent By, Primary Recipient, Secondary Recipient, Description, L, W, H, KG, QTY`
- Preview modal shows:
  - Total parcels to create (accounting for QTY > 1)
  - Client matching info (found vs. will create new)
  - First 10 rows preview table
  - Import summary with total weight
- Client auto-matching:
  - Case-insensitive match to existing clients
  - Creates new client if not found (with tenant defaults)
- QTY > 1 handling:
  - Creates QTY separate parcel records
  - Each parcel gets `parcel_sequence` (1, 2, 3...) and `total_in_sequence` (QTY value)
  - Example: QTY=5 creates parcels numbered "1 of 5", "2 of 5", ..., "5 of 5"
- Imported parcels:
  - status = "warehouse"
  - Generate barcode for each
  - Calculate volumetric weight: (L × W × H) / 5000
  - Chargeable weight = max(actual, volumetric)
- Skips rows with:
  - Missing weight (KG = 0 or empty)
  - Missing description
- Optional target warehouse selector

**5. Data Migration Endpoint**
- Added `POST /api/data/fix-invoice-line-items` endpoint
- Attempts to match line items to shipments by trip_id, description, and weight
- Fixes missing weight, quantity, dimensions, and recipient data

### New API Endpoints
- `GET /api/export/clients` - Export clients as CSV
- `POST /api/import/clients` - Import clients from CSV
- `POST /api/import/parcels` - Import parcels from CSV (updated with sequence support)
- `POST /api/data/fix-invoice-line-items` - Migration to fix legacy invoice data

### Files Modified
- `/app/frontend/src/components/InvoiceEditor.jsx` - Added getItemDisplayValues(), updated table widths
- `/app/frontend/src/pages/Settings.jsx` - Added parcel import preview modal with client matching
- `/app/backend/routes/data_routes.py` - Added parcel_sequence, total_in_sequence, migration endpoint

### Testing
- ✅ Backend: 100% pass rate (12 tests)
- ✅ Frontend: 100% verified
- Test report: /app/test_reports/iteration_32.json

## Backlog / Future Tasks
- P0: None - all critical issues resolved
- P1: Parcel Classification System (Category dropdown + classified packing list)
- P1: Merge Duplicate Clients (UI + backend logic)
- P1: Add "Add Recipient" button on Parcel Intake page
- P2: Review trip loading percentage calculation (recurring issue - 3 occurrences)
- P2: Split `schemas.py` into domain-specific files
- P2: Responsive design for different screen sizes (15", 17", 27")
- P2: Invoice total validation (strict backend blocking on mismatch)
- P3: Implement notification bell showing unread count

---

## Update: Feb 19, 2026 - Session 2: Invoice Table Overhaul & New Features

### Changes Made:

**1. Invoice Line Items Table Overhaul**
- Complete redesign of the line items table with new columns:
  - `#` - Sequential row number
  - `Recipient` - Recipient name
  - `Description` - Parcel description (read-only)
  - `Qty` - Quantity (read-only)
  - `KG` - Actual weight (read-only)
  - `L`, `W`, `H` - Dimensions in cm (read-only)
  - `Vol Wt` - Volumetric weight = (L×W×H)/5000
  - `Ship Wt` - Shipping weight = max(KG, Vol Wt)
  - `Rate` - Editable rate per kg
  - `Amount` - Calculated total
- Ship Wt column color-coded:
  - Green when using actual weight (KG ≥ Vol Wt)
  - Amber when using volumetric weight (Vol Wt > KG)
- All parcel data now read-only in invoice (prevent calculation bugs)
- Only Rate field is editable per line item

**2. Add from Warehouse Feature**
- New "Add from Warehouse" button next to "Add from Trip"
- Opens dialog showing all warehouse parcels (status: warehouse, staged, loaded)
- Filters: Search by description/barcode/recipient, Client dropdown
- Parcel table shows: Client, Recipient, Description, KG, Dimensions, Vol Wt, Status
- Select all / individual selection with checkboxes
- Shows count: "Showing X parcel(s) • X selected"
- Excludes parcels already in current invoice

**3. CSV Template Downloads**
- Settings → Data → Import Clients now has "Download Template" link
- Settings → Data → Import Parcels dialog now includes:
  - Complete CSV format documentation with all 9 columns explained
  - Note about QTY > 1 creating multiple parcels
  - "Download Template CSV" button
- Templates include example rows with realistic data

**4. Helper Functions Added**
- `calculateVolumetricWeight(L, W, H)` - Returns (L×W×H)/5000
- `getShippingWeight(actual, volumetric)` - Returns max of both
- `filteredWarehouseParcels` - Memoized filtered list for warehouse dialog

### New UI Components
- Warehouse Parcels Dialog with search and filters
- CSV format documentation section in import modals

### Files Modified
- `/app/frontend/src/components/InvoiceEditor.jsx` - Major table overhaul, warehouse dialog
- `/app/frontend/src/pages/Settings.jsx` - Template download functions, format docs

### Testing
- ✅ Frontend: 100% pass rate
- Test report: /app/test_reports/iteration_33.json

---

## Update: Feb 19, 2026 - Session 3: Critical Invoice Workflow Bug Fixes

### Changes Made:

**1. Fix: Deleted Parcels Now Appear in Add from Trip**
- `removeLineItem()` now calls PATCH `/api/shipments/{id}` to clear `invoice_id` on backend
- Parcels deleted from invoice are now available for re-selection
- Added `isProcessingParcels` flag to prevent unsaved changes dialog during operations

**2. Fix: Add from Warehouse Now Shows Parcels**
- Fixed query to include `not_invoiced=true` parameter
- Backend now supports `not_invoiced` filter in shipments list
- Also supports comma-separated status filter (e.g., `status=warehouse,staged,loaded`)
- Dialog shows 500+ available parcels with proper filtering

**3. Fix: Removed "+ Add Item" Button**
- Invoice line items now only has "Add from Trip" and "Add from Warehouse" buttons
- Parcels can only be added from existing shipments, not created inline
- Empty state message updated accordingly

**4. New: Warehouse Highlight & Auto-Open**
- Warehouse page accepts `?highlight=PARCEL_ID` URL parameter
- Parcel row flashes amber 3 times with CSS animation
- Detail modal auto-opens after 300ms delay
- URL param cleared after 2 seconds

**5. New: PATCH Endpoint for Shipments**
- Added `PATCH /api/shipments/{id}` endpoint
- Supports partial updates including clearing `invoice_id: null`
- Used when removing parcels from invoices

### New API Endpoints
- `PATCH /api/shipments/{shipment_id}` - Partial shipment update

### Backend Changes
- `/app/backend/routes/shipment_routes.py`:
  - Added `not_invoiced` filter parameter
  - Added `limit` parameter
  - Support comma-separated status values
  - New PATCH endpoint for partial updates

### Frontend Changes
- `/app/frontend/src/components/InvoiceEditor.jsx`:
  - `removeLineItem()` now async, calls backend PATCH
  - Added `isProcessingParcels` state to prevent false dirty warnings
  - Removed "+ Add Item" button
  - Updated empty state message
- `/app/frontend/src/pages/Warehouse.jsx`:
  - Added URL search params handling
  - Added highlight flash animation
  - Auto-opens detail modal for highlighted parcel
- `/app/frontend/src/index.css`:
  - Added `@keyframes highlight-flash` animation

### Testing
- ✅ Backend: 100% pass rate (7/7 tests)
- ✅ Frontend: 100% verified
- Test report: /app/test_reports/iteration_34.json

---

## Update: Feb 20, 2026 - Session 4: Loading/Unloading Workflow & Blocking Fixes

### Changes Made:

**1. Invoice Column Added to Warehouse**
- New "Invoice" column in warehouse table
- Shows invoice number (clickable link) if parcel.invoice_id is set
- Shows "Not Invoiced" badge in red/amber if null
- Helps identify which parcels are ready for loading

**2. Block Non-Invoiced Parcels from Loading**
- Loading page now shows "Invoice" column in staging table
- Non-invoiced parcels have disabled checkbox with `cursor-not-allowed`
- "Select All" only selects invoiced parcels
- Attempting to load non-invoiced parcels shows error toast:
  - "Cannot load X parcel(s) - not invoiced: E1DF9124, ..."
- Red "Not Invoiced" badge visible on each non-invoiced parcel row

**3. Trip Departed/Arrived Tracking**
- Added fields to Trip schema:
  - `actual_departure` - Set automatically when status changes to `in_transit`
  - `actual_arrival` - Set automatically when status changes to `delivered`
- Backend auto-sets timestamps during status transitions
- Enables trip timeline: Created → Loading → Departed (date) → Arrived (date)

**4. Invoice Dimensions Persistence Fix**
- When saving invoice, backend now fetches dimensions from linked shipment
- Fields saved: `length_cm`, `width_cm`, `height_cm`, `weight`
- Dimensions now persist when revisiting invoice
- Vol Wt and Ship Wt columns display correctly on return

### New Schema Fields
- `Trip.actual_departure` (Optional[str])
- `Trip.actual_arrival` (Optional[str])
- `TripUpdate.actual_departure`, `TripUpdate.actual_arrival`

### Backend Changes
- `/app/backend/routes/invoice_routes.py`:
  - Line items now fetch and store dimensions from shipment
- `/app/backend/routes/trip_routes.py`:
  - Status change to `in_transit` sets `actual_departure`
  - Status change to `delivered` sets `actual_arrival`
- `/app/backend/models/schemas.py`:
  - Added `actual_departure`, `actual_arrival` to Trip schema

### Frontend Changes
- `/app/frontend/src/pages/Warehouse.jsx`:
  - Added Invoice column with invoice_number or "Not Invoiced" badge
- `/app/frontend/src/pages/LoadingStaging.jsx`:
  - Added Invoice column with `showInvoiceCheck` prop
  - Disabled checkbox for non-invoiced parcels
  - Block loading with error toast if non-invoiced selected
  - Updated ParcelTable to handle selectable parcels filtering

### Testing
- ✅ Backend: 100% pass rate (6/6 passed, 1 skipped)
- ✅ Frontend: 100% verified
- Test report: /app/test_reports/iteration_35.json

---

## Update: Feb 20, 2026 - Session 6

### Features Implemented

**1. Trip Destination Warehouse**
- Added `destination_warehouse_id` field to Trip schema (TripBase, TripCreate, TripUpdate, Trip)
- Trip creation form now includes "Destination Warehouse" dropdown
- Helper text: "Parcels will be placed in this warehouse upon arrival"
- Options: "No destination (All Warehouses)" + list of active warehouses
- When parcels arrive via bulk status update to "arrived":
  - If trip has destination warehouse → parcels get that warehouse_id
  - If no destination warehouse → parcels get warehouse_id = null (visible in "All Warehouses")

**2. Barcode Scanner Fix (Loading Page)**
- Scanner now supports multiple lookup methods:
  - Full barcode (e.g., S123-001-01)
  - Partial shipment ID (first 8 characters, case-insensitive)
  - Full shipment ID (UUID format)
- `/api/pieces/scan/{barcode}` endpoint updated to search by multiple methods
- Helpful error message: "Parcel not found - check the barcode or ID"

**3. Warehouse Collection Scanner**
- New purple-highlighted section "Scan Parcel for Collection" on Warehouse page
- Input field with scan button for entering barcode or parcel ID
- Only accepts parcels with "arrived" status
- Error message for non-arrived parcels: "Parcel status is '{status}'. Only parcels with 'arrived' status can be collected."
- Collected parcels are removed from all warehouses (warehouse_id = null, collected = true)
- New endpoint: `POST /api/warehouse/scan-collect`
  - Returns: parcel_id, description, client_name, collected_at

**4. Loading Page UI Cleanup**
- Removed "Transit/Arrived" toggle (was scan target toggle)
- Removed "Staging/Truck" toggle
- Simplified UI - scanning now auto-routes based on mode:
  - Loading mode: scanned parcels go to "loaded" status
  - Unloading mode: scanned parcels go to "arrived" status

### Schema Changes
- `TripBase.destination_warehouse_id: Optional[str]`
- `TripCreate.destination_warehouse_id: Optional[str]`
- `TripUpdate.destination_warehouse_id: Optional[str]`
- `Trip.destination_warehouse_id: Optional[str]`

### New API Endpoints
- `POST /api/warehouse/scan-collect` - Scan and collect parcel from warehouse

### Modified API Endpoints
- `GET /api/pieces/scan/{barcode}` - Now supports partial parcel ID lookup
- `PUT /api/warehouse/parcels/bulk-status` - Now handles destination warehouse assignment on "arrived" status

### Frontend Changes
- `/app/frontend/src/pages/Trips.jsx`:
  - Added warehouses state and fetch
  - Added destination_warehouse_id to formData
  - Added "Destination Warehouse" dropdown in trip form
- `/app/frontend/src/pages/LoadingStaging.jsx`:
  - Removed scanTarget state and Switch import
  - Simplified handleBarcodeScan() - auto-routes based on mode
  - Updated placeholder text: "Scan barcode or enter parcel ID..."
- `/app/frontend/src/pages/Warehouse.jsx`:
  - Added collection scanner state (collectionBarcode, collectionScanning)
  - Added handleCollectionScan() and handleCollectionKeyPress() functions
  - Added purple "Scan Parcel for Collection" card UI

### Testing
- ✅ Backend: 100% pass rate (14/14 passed)
- ✅ Frontend: 100% verified
- Test report: /app/test_reports/iteration_37.json
- Test file: /app/backend/tests/test_new_features_iter37.py

---

## Prioritized Backlog

### P0 - Critical (Next Up)
- None currently

### P1 - Important
- Trip Departed/Arrived UI buttons on TripDetail page
- Warehouse Filters - default checked/unchecked statuses
- Fix Delete Invoice Prompt bug

### P2 - Lower Priority
- Save Loading Progress (localStorage)
- Fix incorrect loading percentage on trip cards (recurring issue)

### Future/Backlog
- Comprehensive responsive design overhaul
- Audit number formatting across all pages/PDFs
- Refactor schemas.py into domain-specific model files