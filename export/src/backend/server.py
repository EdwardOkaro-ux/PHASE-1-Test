from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import httpx
import random
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="AfroFreight Logistics API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ ENUMS ============
class UserRole(str, Enum):
    owner = "owner"
    manager = "manager"
    warehouse = "warehouse"
    finance = "finance"
    driver = "driver"

class UserStatus(str, Enum):
    active = "active"
    invited = "invited"
    suspended = "suspended"

class ClientStatus(str, Enum):
    active = "active"
    inactive = "inactive"

class RateType(str, Enum):
    per_kg = "per_kg"
    per_cbm = "per_cbm"
    flat_rate = "flat_rate"
    custom = "custom"

class ShipmentStatus(str, Enum):
    warehouse = "warehouse"
    staged = "staged"
    loaded = "loaded"
    in_transit = "in_transit"
    delivered = "delivered"

class TripStatus(str, Enum):
    planning = "planning"
    loading = "loading"
    in_transit = "in_transit"
    delivered = "delivered"
    closed = "closed"

class ExpenseCategory(str, Enum):
    fuel = "fuel"
    tolls = "tolls"
    border_fees = "border_fees"
    repairs = "repairs"
    food = "food"
    accommodation = "accommodation"
    other = "other"

class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"

class PaymentMethod(str, Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    mobile_money = "mobile_money"
    other = "other"

class VehicleStatus(str, Enum):
    available = "available"
    in_transit = "in_transit"
    repair = "repair"
    inactive = "inactive"

class VehicleComplianceType(str, Enum):
    license_disk = "license_disk"
    insurance = "insurance"
    roadworthy = "roadworthy"
    service = "service"
    custom = "custom"

class DriverStatus(str, Enum):
    available = "available"
    on_trip = "on_trip"
    on_leave = "on_leave"
    inactive = "inactive"

class DriverComplianceType(str, Enum):
    license = "license"
    work_permit = "work_permit"
    medical = "medical"
    prdp = "prdp"
    custom = "custom"

# ============ MODELS ============

# Tenant Models
class TenantBase(BaseModel):
    subdomain: str
    company_name: str
    logo_url: Optional[str] = None
    primary_color: str = "#27AE60"

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# User Models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.owner
    phone: Optional[str] = None

class UserCreate(UserBase):
    tenant_id: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: UserStatus = UserStatus.active
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    picture: Optional[str] = None

# Client Models
class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    credit_limit: float = 0.0
    payment_terms_days: int = 30
    default_currency: str = "ZAR"

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms_days: Optional[int] = None
    default_currency: Optional[str] = None
    status: Optional[ClientStatus] = None

class Client(ClientBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: ClientStatus = ClientStatus.active
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Client Rate Models
class ClientRateBase(BaseModel):
    rate_type: RateType
    rate_value: float
    effective_from: Optional[str] = None
    notes: Optional[str] = None

class ClientRateCreate(ClientRateBase):
    client_id: str

class ClientRate(ClientRateBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Shipment Models
class ShipmentBase(BaseModel):
    description: str
    destination: str
    total_pieces: int = 1
    total_weight: float
    total_cbm: Optional[float] = None

class ShipmentCreate(ShipmentBase):
    client_id: str
    trip_id: Optional[str] = None

class ShipmentUpdate(BaseModel):
    description: Optional[str] = None
    destination: Optional[str] = None
    total_pieces: Optional[int] = None
    total_weight: Optional[float] = None
    total_cbm: Optional[float] = None
    status: Optional[ShipmentStatus] = None
    trip_id: Optional[str] = None

class Shipment(ShipmentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    client_id: str
    trip_id: Optional[str] = None
    status: ShipmentStatus = ShipmentStatus.warehouse
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Shipment Piece Models
class ShipmentPieceBase(BaseModel):
    piece_number: int
    weight: float
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    photo_url: Optional[str] = None

class ShipmentPieceCreate(ShipmentPieceBase):
    shipment_id: str

class ShipmentPiece(ShipmentPieceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shipment_id: str
    barcode: str
    loaded_at: Optional[datetime] = None

# Trip Models
class TripBase(BaseModel):
    trip_number: str
    route: List[str] = []  # JSON array of stops e.g. ["Johannesburg", "Beitbridge", "Harare"]
    departure_date: str  # Required
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    notes: Optional[str] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    trip_number: Optional[str] = None
    route: Optional[List[str]] = None
    departure_date: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[TripStatus] = None

class Trip(TripBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: TripStatus = TripStatus.planning
    locked_at: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Trip Expense Models
class TripExpenseBase(BaseModel):
    category: ExpenseCategory
    amount: float
    currency: str = "ZAR"
    expense_date: str  # Required
    description: Optional[str] = None
    receipt_url: Optional[str] = None

class TripExpenseCreate(TripExpenseBase):
    pass

class TripExpenseUpdate(BaseModel):
    category: Optional[ExpenseCategory] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    expense_date: Optional[str] = None
    description: Optional[str] = None
    receipt_url: Optional[str] = None

class TripExpense(TripExpenseBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trip_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ FINANCIAL MODELS ============

# Invoice Models
class InvoiceBase(BaseModel):
    trip_id: Optional[str] = None
    client_id: str
    subtotal: float
    adjustments: float = 0
    currency: str = "ZAR"

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    subtotal: Optional[float] = None
    adjustments: Optional[float] = None
    currency: Optional[str] = None

class Invoice(InvoiceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    invoice_number: str
    status: InvoiceStatus = InvoiceStatus.draft
    total: float = 0
    sent_at: Optional[datetime] = None
    sent_by: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Invoice Line Item Models
class InvoiceLineItemBase(BaseModel):
    shipment_id: Optional[str] = None
    description: str
    quantity: int = 1
    weight: Optional[float] = None
    rate: float

class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass

class InvoiceLineItem(InvoiceLineItemBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_id: str
    amount: float = 0

# Payment Models
class PaymentBase(BaseModel):
    client_id: str
    invoice_id: Optional[str] = None
    amount: float
    payment_date: str
    payment_method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ FLEET MANAGEMENT MODELS ============

# Vehicle Models
class VehicleBase(BaseModel):
    name: str
    registration_number: str
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    max_weight_kg: Optional[float] = None
    max_volume_cbm: Optional[float] = None

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    max_weight_kg: Optional[float] = None
    max_volume_cbm: Optional[float] = None
    status: Optional[VehicleStatus] = None

class Vehicle(VehicleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: VehicleStatus = VehicleStatus.available
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Vehicle Compliance Models
class VehicleComplianceBase(BaseModel):
    item_type: VehicleComplianceType
    item_label: Optional[str] = None
    expiry_date: str
    reminder_days_before: int = 30
    notify_channels: List[str] = ["bell"]
    provider: Optional[str] = None
    policy_number: Optional[str] = None

class VehicleComplianceCreate(VehicleComplianceBase):
    pass

class VehicleCompliance(VehicleComplianceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Driver Models
class DriverBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    id_passport_number: Optional[str] = None
    nationality: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    id_passport_number: Optional[str] = None
    nationality: Optional[str] = None
    status: Optional[DriverStatus] = None

class Driver(DriverBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: DriverStatus = DriverStatus.available
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Driver Compliance Models
class DriverComplianceBase(BaseModel):
    item_type: DriverComplianceType
    item_label: Optional[str] = None
    expiry_date: str
    reminder_days_before: int = 30
    notify_channels: List[str] = ["bell"]
    license_number: Optional[str] = None
    issuing_country: Optional[str] = None

class DriverComplianceCreate(DriverComplianceBase):
    pass

class DriverCompliance(DriverComplianceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    driver_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Auth Response
class AuthUser(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    role: Optional[str] = None

# ============ HELPER FUNCTIONS ============

def generate_barcode(trip_number: Optional[str], shipment_seq: int, piece_number: int) -> str:
    """Generate barcode in format: [trip_number]-[shipment_seq]-[piece_number] or TEMP-[random]"""
    if trip_number:
        return f"{trip_number}-{shipment_seq:03d}-{piece_number:02d}"
    else:
        random_digits = ''.join(random.choices(string.digits, k=6))
        return f"TEMP-{random_digits}"

async def generate_invoice_number(tenant_id: str) -> str:
    """Generate invoice number in format: INV-YYYY-NNN"""
    current_year = datetime.now(timezone.utc).year
    
    # Find the highest invoice number for this tenant this year
    pattern = f"INV-{current_year}-"
    last_invoice = await db.invoices.find_one(
        {"tenant_id": tenant_id, "invoice_number": {"$regex": f"^{pattern}"}},
        {"_id": 0, "invoice_number": 1},
        sort=[("invoice_number", -1)]
    )
    
    if last_invoice:
        # Extract the sequence number and increment
        last_num = int(last_invoice["invoice_number"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    return f"INV-{current_year}-{next_num:03d}"

def calculate_due_date(payment_terms_days: int) -> str:
    """Calculate due date from today + payment terms"""
    due = datetime.now(timezone.utc) + timedelta(days=payment_terms_days)
    return due.strftime("%Y-%m-%d")

async def get_current_user(request: Request) -> dict:
    """Get current user from session token (cookie or header)"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Find user
    user_doc = await db.users.find_one(
        {"id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user_doc

async def get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    """Extract tenant_id from current user"""
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User not associated with a tenant")
    return tenant_id

# ============ AUTH ROUTES ============

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Call Emergent Auth to get user data
    async with httpx.AsyncClient() as client_http:
        auth_response = await client_http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        auth_data = auth_response.json()
    
    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["id"]
        tenant_id = existing_user.get("tenant_id")
        role = existing_user.get("role", "owner")
        
        # Update last login
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "last_login": datetime.now(timezone.utc).isoformat(),
                "picture": picture
            }}
        )
    else:
        # Create new tenant and user for first-time login
        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        subdomain = email.split("@")[0].lower().replace(".", "")[:20]
        
        # Check if subdomain exists, append random if needed
        existing_tenant = await db.tenants.find_one({"subdomain": subdomain})
        if existing_tenant:
            subdomain = f"{subdomain}{random.randint(100, 999)}"
        
        # Create tenant
        tenant_doc = {
            "id": tenant_id,
            "subdomain": subdomain,
            "company_name": f"{name}'s Company",
            "logo_url": None,
            "primary_color": "#27AE60",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tenants.insert_one(tenant_doc)
        
        # Create user
        user_doc = {
            "id": user_id,
            "tenant_id": tenant_id,
            "name": name,
            "email": email,
            "role": "owner",
            "phone": None,
            "status": "active",
            "last_login": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "picture": picture
        }
        await db.users.insert_one(user_doc)
        role = "owner"
    
    # Get tenant name
    tenant_doc = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant_name = tenant_doc.get("company_name") if tenant_doc else None
    
    # Store session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    return {
        "id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "role": role
    }

@api_router.get("/auth/me", response_model=AuthUser)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user"""
    tenant_doc = await db.tenants.find_one({"id": user.get("tenant_id")}, {"_id": 0})
    tenant_name = tenant_doc.get("company_name") if tenant_doc else None
    
    return AuthUser(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        picture=user.get("picture"),
        tenant_id=user.get("tenant_id"),
        tenant_name=tenant_name,
        role=user.get("role")
    )

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ============ TENANT ROUTES ============

@api_router.get("/tenant", response_model=Tenant)
async def get_current_tenant(tenant_id: str = Depends(get_tenant_id)):
    """Get current tenant info"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@api_router.put("/tenant")
async def update_tenant(
    update_data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update tenant settings (owner only)"""
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can update tenant settings")
    
    allowed_fields = ["company_name", "logo_url", "primary_color"]
    update_dict = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if update_dict:
        await db.tenants.update_one({"id": tenant_id}, {"$set": update_dict})
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return tenant

# ============ USER ROUTES ============

@api_router.get("/users", response_model=List[User])
async def list_users(tenant_id: str = Depends(get_tenant_id)):
    """List all users in tenant"""
    users = await db.users.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    return users

@api_router.post("/users", response_model=User)
async def create_user(
    user_data: UserBase,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create/invite a new user"""
    if current_user.get("role") not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Only owner/manager can create users")
    
    # Check if email exists in tenant
    existing = await db.users.find_one(
        {"tenant_id": tenant_id, "email": user_data.email},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    user = User(
        **user_data.model_dump(),
        tenant_id=tenant_id,
        status=UserStatus.invited
    )
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    
    return user

@api_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update user"""
    if current_user.get("role") not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Only owner/manager can update users")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.users.update_one(
            {"id": user_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
    
    user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id}, {"_id": 0})
    return user

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete user"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can delete users")
    
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted"}

# ============ CLIENT ROUTES ============

@api_router.get("/clients", response_model=List[Client])
async def list_clients(tenant_id: str = Depends(get_tenant_id)):
    """List all clients"""
    clients = await db.clients.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    return clients

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single client"""
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@api_router.post("/clients", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new client"""
    client = Client(**client_data.model_dump(), tenant_id=tenant_id)
    
    doc = client.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.clients.insert_one(doc)
    
    return client

@api_router.put("/clients/{client_id}")
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update client"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.clients.update_one(
            {"id": client_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Client not found")
    
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    return client

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Delete client"""
    result = await db.clients.delete_one({"id": client_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted"}

# ============ CLIENT RATES ROUTES ============

@api_router.get("/clients/{client_id}/rates", response_model=List[ClientRate])
async def list_client_rates(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List rates for a client"""
    # Verify client belongs to tenant
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    rates = await db.client_rates.find({"client_id": client_id}, {"_id": 0}).to_list(100)
    return rates

@api_router.post("/clients/{client_id}/rates", response_model=ClientRate)
async def create_client_rate(
    client_id: str,
    rate_data: ClientRateBase,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create rate for a client"""
    # Verify client belongs to tenant
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    rate = ClientRate(
        **rate_data.model_dump(),
        client_id=client_id,
        created_by=user["id"]
    )
    
    if not rate.effective_from:
        rate.effective_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    doc = rate.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.client_rates.insert_one(doc)
    
    return rate

# ============ SHIPMENT ROUTES ============

@api_router.get("/shipments", response_model=List[Shipment])
async def list_shipments(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all shipments"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    shipments = await db.shipments.find(query, {"_id": 0}).to_list(1000)
    return shipments

@api_router.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single shipment with pieces"""
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    pieces = await db.shipment_pieces.find({"shipment_id": shipment_id}, {"_id": 0}).to_list(100)
    
    return {**shipment, "pieces": pieces}

@api_router.post("/shipments", response_model=Shipment)
async def create_shipment(
    shipment_data: ShipmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new shipment"""
    # Verify client belongs to tenant
    client = await db.clients.find_one(
        {"id": shipment_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    shipment = Shipment(
        **shipment_data.model_dump(),
        tenant_id=tenant_id,
        created_by=user["id"]
    )
    
    doc = shipment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.shipments.insert_one(doc)
    
    return shipment

@api_router.put("/shipments/{shipment_id}")
async def update_shipment(
    shipment_id: str,
    update_data: ShipmentUpdate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update shipment"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.shipments.update_one(
            {"id": shipment_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Shipment not found")
    
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    return shipment

@api_router.delete("/shipments/{shipment_id}")
async def delete_shipment(shipment_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Delete shipment and its pieces"""
    result = await db.shipments.delete_one({"id": shipment_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Delete associated pieces
    await db.shipment_pieces.delete_many({"shipment_id": shipment_id})
    
    return {"message": "Shipment deleted"}

# ============ SHIPMENT PIECES ROUTES ============

@api_router.post("/shipments/{shipment_id}/pieces", response_model=ShipmentPiece)
async def create_shipment_piece(
    shipment_id: str,
    piece_data: ShipmentPieceBase,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add a piece to shipment"""
    # Verify shipment belongs to tenant
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get trip number if assigned
    trip_number = None
    if shipment.get("trip_id"):
        trip = await db.trips.find_one({"id": shipment["trip_id"]}, {"_id": 0})
        if trip:
            trip_number = trip.get("trip_number")
    
    # Count existing shipments for sequence number
    shipment_count = await db.shipments.count_documents({
        "tenant_id": tenant_id,
        "trip_id": shipment.get("trip_id")
    })
    
    # Generate barcode
    barcode = generate_barcode(trip_number, shipment_count, piece_data.piece_number)
    
    piece = ShipmentPiece(
        **piece_data.model_dump(),
        shipment_id=shipment_id,
        barcode=barcode
    )
    
    doc = piece.model_dump()
    if doc.get('loaded_at'):
        doc['loaded_at'] = doc['loaded_at'].isoformat()
    await db.shipment_pieces.insert_one(doc)
    
    return piece

@api_router.get("/pieces/scan/{barcode}")
async def scan_barcode(barcode: str, tenant_id: str = Depends(get_tenant_id)):
    """Scan a barcode and return piece + shipment info"""
    piece = await db.shipment_pieces.find_one({"barcode": barcode}, {"_id": 0})
    if not piece:
        raise HTTPException(status_code=404, detail="Barcode not found")
    
    shipment = await db.shipments.find_one(
        {"id": piece["shipment_id"], "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    client = await db.clients.find_one({"id": shipment["client_id"]}, {"_id": 0})
    
    return {
        "piece": piece,
        "shipment": shipment,
        "client": client
    }

@api_router.put("/pieces/{piece_id}/load")
async def mark_piece_loaded(piece_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Mark a piece as loaded"""
    piece = await db.shipment_pieces.find_one({"id": piece_id}, {"_id": 0})
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")
    
    # Verify shipment belongs to tenant
    shipment = await db.shipments.find_one(
        {"id": piece["shipment_id"], "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.shipment_pieces.update_one(
        {"id": piece_id},
        {"$set": {"loaded_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Piece marked as loaded"}

# ============ TRIP ROUTES ============

@api_router.get("/trips", response_model=List[Trip])
async def list_trips(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all trips"""
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    
    trips = await db.trips.find(query, {"_id": 0}).sort("departure_date", -1).to_list(100)
    return trips

@api_router.get("/trips/{trip_id}")
async def get_trip(trip_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single trip with shipments and expenses"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    shipments = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(100)
    
    expenses = await db.trip_expenses.find(
        {"trip_id": trip_id},
        {"_id": 0}
    ).sort("expense_date", -1).to_list(100)
    
    # Calculate expense totals by category
    expense_totals = {}
    total_expenses = 0
    for expense in expenses:
        category = expense.get("category", "other")
        amount = expense.get("amount", 0)
        expense_totals[category] = expense_totals.get(category, 0) + amount
        total_expenses += amount
    
    return {
        **trip,
        "shipments": shipments,
        "expenses": expenses,
        "expense_totals": expense_totals,
        "total_expenses": total_expenses
    }

@api_router.post("/trips", response_model=Trip)
async def create_trip(
    trip_data: TripCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new trip"""
    # Check trip_number uniqueness within tenant
    existing = await db.trips.find_one({
        "tenant_id": tenant_id,
        "trip_number": trip_data.trip_number
    })
    if existing:
        raise HTTPException(status_code=400, detail="Trip number already exists for this tenant")
    
    trip = Trip(
        **trip_data.model_dump(),
        tenant_id=tenant_id,
        created_by=user["id"]
    )
    
    doc = trip.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('locked_at'):
        doc['locked_at'] = doc['locked_at'].isoformat()
    await db.trips.insert_one(doc)
    
    return trip

@api_router.put("/trips/{trip_id}")
async def update_trip(
    trip_id: str,
    update_data: TripUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update trip - handles locking when status changes to 'closed'"""
    # Get current trip
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if trip is locked (only owner can modify locked trips)
    if trip.get("locked_at") and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Trip is locked. Only owner can modify.")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Check if trip_number is being changed and ensure uniqueness
    if "trip_number" in update_dict and update_dict["trip_number"] != trip.get("trip_number"):
        existing = await db.trips.find_one({
            "tenant_id": tenant_id,
            "trip_number": update_dict["trip_number"],
            "id": {"$ne": trip_id}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Trip number already exists for this tenant")
    
    # Handle status change to 'closed' - set locked_at timestamp
    if update_dict.get("status") == "closed" and trip.get("status") != "closed":
        update_dict["locked_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.trips.update_one(
            {"id": trip_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    return trip

@api_router.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a trip (only if not locked or user is owner)"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.get("locked_at") and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Cannot delete locked trip")
    
    # Unassign all shipments from this trip
    await db.shipments.update_many(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"$set": {"trip_id": None, "status": "warehouse"}}
    )
    
    # Delete associated expenses
    await db.trip_expenses.delete_many({"trip_id": trip_id})
    
    # Delete trip
    await db.trips.delete_one({"id": trip_id, "tenant_id": tenant_id})
    
    return {"message": "Trip deleted"}

@api_router.post("/trips/{trip_id}/assign-shipment/{shipment_id}")
async def assign_shipment_to_trip(
    trip_id: str,
    shipment_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Assign a shipment to a trip"""
    # Verify trip exists and is not locked
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.get("locked_at"):
        raise HTTPException(status_code=403, detail="Cannot modify shipments on a locked trip")
    
    # Update shipment
    result = await db.shipments.update_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"$set": {"trip_id": trip_id, "status": "staged"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Update piece barcodes with new trip number
    pieces = await db.shipment_pieces.find({"shipment_id": shipment_id}, {"_id": 0}).to_list(100)
    
    shipment_count = await db.shipments.count_documents({
        "tenant_id": tenant_id,
        "trip_id": trip_id
    })
    
    for piece in pieces:
        new_barcode = generate_barcode(trip["trip_number"], shipment_count, piece["piece_number"])
        await db.shipment_pieces.update_one(
            {"id": piece["id"]},
            {"$set": {"barcode": new_barcode}}
        )
    
    return {"message": "Shipment assigned to trip"}

@api_router.post("/trips/{trip_id}/unassign-shipment/{shipment_id}")
async def unassign_shipment_from_trip(
    trip_id: str,
    shipment_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Remove a shipment from a trip"""
    # Verify trip exists and is not locked
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.get("locked_at"):
        raise HTTPException(status_code=403, detail="Cannot modify shipments on a locked trip")
    
    # Update shipment
    result = await db.shipments.update_one(
        {"id": shipment_id, "tenant_id": tenant_id, "trip_id": trip_id},
        {"$set": {"trip_id": None, "status": "warehouse"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shipment not found or not assigned to this trip")
    
    # Update piece barcodes back to TEMP format
    pieces = await db.shipment_pieces.find({"shipment_id": shipment_id}, {"_id": 0}).to_list(100)
    
    for piece in pieces:
        new_barcode = generate_barcode(None, 0, piece["piece_number"])
        await db.shipment_pieces.update_one(
            {"id": piece["id"]},
            {"$set": {"barcode": new_barcode}}
        )
    
    return {"message": "Shipment removed from trip"}

# ============ TRIP EXPENSES ROUTES ============

@api_router.get("/trips/{trip_id}/expenses", response_model=List[TripExpense])
async def list_trip_expenses(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all expenses for a trip"""
    # Verify trip exists and belongs to tenant
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    expenses = await db.trip_expenses.find(
        {"trip_id": trip_id},
        {"_id": 0}
    ).sort("expense_date", -1).to_list(100)
    
    return expenses

@api_router.post("/trips/{trip_id}/expenses", response_model=TripExpense)
async def create_trip_expense(
    trip_id: str,
    expense_data: TripExpenseCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Add an expense to a trip"""
    # Verify trip exists and belongs to tenant
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    expense = TripExpense(
        **expense_data.model_dump(),
        trip_id=trip_id,
        created_by=user["id"]
    )
    
    doc = expense.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.trip_expenses.insert_one(doc)
    
    return expense

@api_router.put("/trips/{trip_id}/expenses/{expense_id}")
async def update_trip_expense(
    trip_id: str,
    expense_id: str,
    update_data: TripExpenseUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update a trip expense (locked trips: owner only)"""
    # Verify trip exists and belongs to tenant
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if trip is locked (only owner can edit expenses on locked trips)
    if trip.get("locked_at") and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Trip is locked. Only owner can edit expenses.")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.trip_expenses.update_one(
            {"id": expense_id, "trip_id": trip_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Expense not found")
    
    expense = await db.trip_expenses.find_one({"id": expense_id, "trip_id": trip_id}, {"_id": 0})
    return expense

@api_router.delete("/trips/{trip_id}/expenses/{expense_id}")
async def delete_trip_expense(
    trip_id: str,
    expense_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a trip expense (locked trips: owner only)"""
    # Verify trip exists and belongs to tenant
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if trip is locked
    if trip.get("locked_at") and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Trip is locked. Only owner can delete expenses.")
    
    result = await db.trip_expenses.delete_one({"id": expense_id, "trip_id": trip_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {"message": "Expense deleted"}

# ============ INVOICE ROUTES ============

@api_router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all invoices with overdue status check"""
    query = {"tenant_id": tenant_id}
    if status and status != "all":
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Check for overdue invoices and update status
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for invoice in invoices:
        if invoice["status"] not in ["paid", "overdue"] and invoice["due_date"] < today:
            # Update to overdue
            await db.invoices.update_one(
                {"id": invoice["id"]},
                {"$set": {"status": "overdue"}}
            )
            invoice["status"] = "overdue"
        
        # Enrich with client name
        client = await db.clients.find_one({"id": invoice["client_id"]}, {"_id": 0, "name": 1})
        invoice["client_name"] = client["name"] if client else "Unknown"
    
    return invoices

@api_router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single invoice with line items and payments"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get line items
    line_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get payments
    payments = await db.payments.find(
        {"invoice_id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("payment_date", -1).to_list(100)
    
    total_paid = sum(p["amount"] for p in payments)
    
    # Get client info
    client = await db.clients.find_one({"id": invoice["client_id"]}, {"_id": 0})
    
    # Check overdue
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if invoice["status"] not in ["paid", "overdue"] and invoice["due_date"] < today:
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "overdue"}}
        )
        invoice["status"] = "overdue"
    
    return {
        **invoice,
        "line_items": line_items,
        "payments": payments,
        "total_paid": total_paid,
        "balance_due": invoice["total"] - total_paid,
        "client": client
    }

@api_router.post("/invoices")
async def create_invoice(
    invoice_data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new invoice"""
    # Verify client exists
    client = await db.clients.find_one(
        {"id": invoice_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate invoice number
    invoice_number = await generate_invoice_number(tenant_id)
    
    # Calculate due date
    due_date = calculate_due_date(client.get("payment_terms_days", 30))
    
    # Calculate total
    total = invoice_data.subtotal + invoice_data.adjustments
    
    invoice = Invoice(
        **invoice_data.model_dump(),
        tenant_id=tenant_id,
        invoice_number=invoice_number,
        total=total,
        due_date=due_date
    )
    
    doc = invoice.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('sent_at'):
        doc['sent_at'] = doc['sent_at'].isoformat()
    if doc.get('paid_at'):
        doc['paid_at'] = doc['paid_at'].isoformat()
    await db.invoices.insert_one(doc)
    
    return invoice

@api_router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    update_data: InvoiceUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update invoice"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Recalculate total if subtotal or adjustments changed
    subtotal = update_dict.get("subtotal", invoice["subtotal"])
    adjustments = update_dict.get("adjustments", invoice["adjustments"])
    update_dict["total"] = subtotal + adjustments
    
    # Handle status changes
    if update_dict.get("status") == "sent" and invoice["status"] == "draft":
        update_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
        update_dict["sent_by"] = user["id"]
    elif update_dict.get("status") == "paid" and invoice["status"] != "paid":
        update_dict["paid_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.invoices.update_one(
            {"id": invoice_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    return invoice

@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete invoice (only drafts or by owner)"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft" and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can delete non-draft invoices")
    
    # Delete line items
    await db.invoice_line_items.delete_many({"invoice_id": invoice_id})
    
    # Delete invoice
    await db.invoices.delete_one({"id": invoice_id, "tenant_id": tenant_id})
    
    return {"message": "Invoice deleted"}

# ============ INVOICE LINE ITEMS ROUTES ============

@api_router.get("/invoices/{invoice_id}/items")
async def list_invoice_items(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List invoice line items"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    return items

@api_router.post("/invoices/{invoice_id}/items")
async def add_invoice_item(
    invoice_id: str,
    item_data: InvoiceLineItemCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add line item to invoice"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only add items to draft invoices")
    
    # Calculate amount
    if item_data.weight:
        amount = item_data.weight * item_data.rate
    else:
        amount = item_data.quantity * item_data.rate
    
    item = InvoiceLineItem(
        **item_data.model_dump(),
        invoice_id=invoice_id,
        amount=amount
    )
    
    doc = item.model_dump()
    await db.invoice_line_items.insert_one(doc)
    
    # Update invoice subtotal
    all_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0, "amount": 1}
    ).to_list(100)
    
    new_subtotal = sum(i["amount"] for i in all_items)
    new_total = new_subtotal + invoice["adjustments"]
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"subtotal": new_subtotal, "total": new_total}}
    )
    
    return item

@api_router.delete("/invoices/{invoice_id}/items/{item_id}")
async def delete_invoice_item(
    invoice_id: str,
    item_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete line item from invoice"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only remove items from draft invoices")
    
    result = await db.invoice_line_items.delete_one(
        {"id": item_id, "invoice_id": invoice_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Recalculate subtotal
    all_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0, "amount": 1}
    ).to_list(100)
    
    new_subtotal = sum(i["amount"] for i in all_items)
    new_total = new_subtotal + invoice["adjustments"]
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"subtotal": new_subtotal, "total": new_total}}
    )
    
    return {"message": "Item deleted"}

# ============ PAYMENT ROUTES ============

@api_router.get("/payments")
async def list_payments(
    client_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all payments"""
    query = {"tenant_id": tenant_id}
    if client_id:
        query["client_id"] = client_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("payment_date", -1).to_list(500)
    
    # Enrich with client and invoice info
    for payment in payments:
        client = await db.clients.find_one({"id": payment["client_id"]}, {"_id": 0, "name": 1})
        payment["client_name"] = client["name"] if client else "Unknown"
        
        if payment.get("invoice_id"):
            invoice = await db.invoices.find_one(
                {"id": payment["invoice_id"]},
                {"_id": 0, "invoice_number": 1}
            )
            payment["invoice_number"] = invoice["invoice_number"] if invoice else None
    
    return payments

@api_router.post("/payments")
async def create_payment(
    payment_data: PaymentCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Record a payment"""
    # Verify client exists
    client = await db.clients.find_one(
        {"id": payment_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Verify invoice if provided
    if payment_data.invoice_id:
        invoice = await db.invoices.find_one(
            {"id": payment_data.invoice_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment = Payment(
        **payment_data.model_dump(),
        tenant_id=tenant_id,
        created_by=user["id"]
    )
    
    doc = payment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.payments.insert_one(doc)
    
    # Check if invoice is fully paid
    if payment_data.invoice_id:
        invoice = await db.invoices.find_one(
            {"id": payment_data.invoice_id},
            {"_id": 0}
        )
        payments = await db.payments.find(
            {"invoice_id": payment_data.invoice_id},
            {"_id": 0, "amount": 1}
        ).to_list(100)
        
        total_paid = sum(p["amount"] for p in payments)
        
        if total_paid >= invoice["total"]:
            await db.invoices.update_one(
                {"id": payment_data.invoice_id},
                {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
            )
    
    return payment

@api_router.delete("/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a payment (owner/finance only)"""
    if user.get("role") not in ["owner", "finance"]:
        raise HTTPException(status_code=403, detail="Only owner/finance can delete payments")
    
    payment = await db.payments.find_one(
        {"id": payment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    invoice_id = payment.get("invoice_id")
    
    await db.payments.delete_one({"id": payment_id, "tenant_id": tenant_id})
    
    # Recheck invoice paid status
    if invoice_id:
        invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if invoice and invoice["status"] == "paid":
            payments = await db.payments.find(
                {"invoice_id": invoice_id},
                {"_id": 0, "amount": 1}
            ).to_list(100)
            
            total_paid = sum(p["amount"] for p in payments)
            
            if total_paid < invoice["total"]:
                # Revert to sent or overdue
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                new_status = "overdue" if invoice["due_date"] < today else "sent"
                await db.invoices.update_one(
                    {"id": invoice_id},
                    {"$set": {"status": new_status, "paid_at": None}}
                )
    
    return {"message": "Payment deleted"}

# ============ FINANCIAL SUMMARY ============

@api_router.get("/finance/summary")
async def get_financial_summary(tenant_id: str = Depends(get_tenant_id)):
    """Get financial overview"""
    # Invoice totals by status
    draft_total = 0
    sent_total = 0
    paid_total = 0
    overdue_total = 0
    
    invoices = await db.invoices.find(
        {"tenant_id": tenant_id},
        {"_id": 0, "status": 1, "total": 1, "due_date": 1}
    ).to_list(1000)
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    for inv in invoices:
        status = inv["status"]
        # Auto-check overdue
        if status not in ["paid", "overdue"] and inv["due_date"] < today:
            status = "overdue"
        
        if status == "draft":
            draft_total += inv["total"]
        elif status == "sent":
            sent_total += inv["total"]
        elif status == "paid":
            paid_total += inv["total"]
        elif status == "overdue":
            overdue_total += inv["total"]
    
    # Total payments received
    payments = await db.payments.find(
        {"tenant_id": tenant_id},
        {"_id": 0, "amount": 1}
    ).to_list(1000)
    
    total_received = sum(p["amount"] for p in payments)
    
    # Recent invoices
    recent_invoices = await db.invoices.find(
        {"tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    for inv in recent_invoices:
        client = await db.clients.find_one({"id": inv["client_id"]}, {"_id": 0, "name": 1})
        inv["client_name"] = client["name"] if client else "Unknown"
    
    return {
        "invoice_totals": {
            "draft": draft_total,
            "sent": sent_total,
            "paid": paid_total,
            "overdue": overdue_total
        },
        "total_outstanding": sent_total + overdue_total,
        "total_received": total_received,
        "invoice_count": len(invoices),
        "recent_invoices": recent_invoices
    }

# ============ VEHICLE ROUTES ============

@api_router.get("/vehicles")
async def list_vehicles(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all vehicles"""
    query = {"tenant_id": tenant_id}
    if status and status != "all":
        query["status"] = status
    
    vehicles = await db.vehicles.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    
    # Add compliance summary for each vehicle
    for vehicle in vehicles:
        compliance_items = await db.vehicle_compliance.find(
            {"vehicle_id": vehicle["id"]},
            {"_id": 0, "expiry_date": 1, "item_type": 1}
        ).to_list(100)
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        overdue_count = sum(1 for c in compliance_items if c["expiry_date"] < today)
        vehicle["compliance_issues"] = overdue_count
    
    return vehicles

@api_router.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single vehicle with compliance items"""
    vehicle = await db.vehicles.find_one(
        {"id": vehicle_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    compliance = await db.vehicle_compliance.find(
        {"vehicle_id": vehicle_id},
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    return {**vehicle, "compliance": compliance}

@api_router.post("/vehicles")
async def create_vehicle(
    vehicle_data: VehicleCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new vehicle"""
    vehicle = Vehicle(
        **vehicle_data.model_dump(),
        tenant_id=tenant_id
    )
    
    doc = vehicle.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vehicles.insert_one(doc)
    
    return vehicle

@api_router.put("/vehicles/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str,
    update_data: VehicleUpdate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update vehicle"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.vehicles.update_one(
            {"id": vehicle_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
    return vehicle

@api_router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete vehicle and its compliance items"""
    result = await db.vehicles.delete_one({"id": vehicle_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Delete compliance items
    await db.vehicle_compliance.delete_many({"vehicle_id": vehicle_id})
    
    return {"message": "Vehicle deleted"}

# Vehicle Compliance Routes
@api_router.get("/vehicles/{vehicle_id}/compliance")
async def list_vehicle_compliance(
    vehicle_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List compliance items for a vehicle"""
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    compliance = await db.vehicle_compliance.find(
        {"vehicle_id": vehicle_id},
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    return compliance

@api_router.post("/vehicles/{vehicle_id}/compliance")
async def add_vehicle_compliance(
    vehicle_id: str,
    compliance_data: VehicleComplianceCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add compliance item to vehicle"""
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    compliance = VehicleCompliance(
        **compliance_data.model_dump(),
        vehicle_id=vehicle_id
    )
    
    doc = compliance.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vehicle_compliance.insert_one(doc)
    
    return compliance

@api_router.put("/vehicles/{vehicle_id}/compliance/{compliance_id}")
async def update_vehicle_compliance(
    vehicle_id: str,
    compliance_id: str,
    update_data: VehicleComplianceCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update vehicle compliance item"""
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    update_dict = update_data.model_dump()
    
    result = await db.vehicle_compliance.update_one(
        {"id": compliance_id, "vehicle_id": vehicle_id},
        {"$set": update_dict}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    
    compliance = await db.vehicle_compliance.find_one({"id": compliance_id}, {"_id": 0})
    return compliance

@api_router.delete("/vehicles/{vehicle_id}/compliance/{compliance_id}")
async def delete_vehicle_compliance(
    vehicle_id: str,
    compliance_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete vehicle compliance item"""
    vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    result = await db.vehicle_compliance.delete_one({"id": compliance_id, "vehicle_id": vehicle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    
    return {"message": "Compliance item deleted"}

# ============ DRIVER ROUTES ============

@api_router.get("/drivers")
async def list_drivers(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all drivers"""
    query = {"tenant_id": tenant_id}
    if status and status != "all":
        query["status"] = status
    
    drivers = await db.drivers.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    
    # Add compliance summary for each driver
    for driver in drivers:
        compliance_items = await db.driver_compliance.find(
            {"driver_id": driver["id"]},
            {"_id": 0, "expiry_date": 1, "item_type": 1}
        ).to_list(100)
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        overdue_count = sum(1 for c in compliance_items if c["expiry_date"] < today)
        driver["compliance_issues"] = overdue_count
    
    return drivers

@api_router.get("/drivers/{driver_id}")
async def get_driver(driver_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single driver with compliance items"""
    driver = await db.drivers.find_one(
        {"id": driver_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    compliance = await db.driver_compliance.find(
        {"driver_id": driver_id},
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    return {**driver, "compliance": compliance}

@api_router.post("/drivers")
async def create_driver(
    driver_data: DriverCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new driver"""
    driver = Driver(
        **driver_data.model_dump(),
        tenant_id=tenant_id
    )
    
    doc = driver.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.drivers.insert_one(doc)
    
    return driver

@api_router.put("/drivers/{driver_id}")
async def update_driver(
    driver_id: str,
    update_data: DriverUpdate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update driver"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.drivers.update_one(
            {"id": driver_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Driver not found")
    
    driver = await db.drivers.find_one({"id": driver_id, "tenant_id": tenant_id}, {"_id": 0})
    return driver

@api_router.delete("/drivers/{driver_id}")
async def delete_driver(
    driver_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete driver and their compliance items"""
    result = await db.drivers.delete_one({"id": driver_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    # Delete compliance items
    await db.driver_compliance.delete_many({"driver_id": driver_id})
    
    return {"message": "Driver deleted"}

# Driver Compliance Routes
@api_router.get("/drivers/{driver_id}/compliance")
async def list_driver_compliance(
    driver_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List compliance items for a driver"""
    driver = await db.drivers.find_one({"id": driver_id, "tenant_id": tenant_id}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    compliance = await db.driver_compliance.find(
        {"driver_id": driver_id},
        {"_id": 0}
    ).sort("expiry_date", 1).to_list(100)
    
    return compliance

@api_router.post("/drivers/{driver_id}/compliance")
async def add_driver_compliance(
    driver_id: str,
    compliance_data: DriverComplianceCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add compliance item to driver"""
    driver = await db.drivers.find_one({"id": driver_id, "tenant_id": tenant_id}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    compliance = DriverCompliance(
        **compliance_data.model_dump(),
        driver_id=driver_id
    )
    
    doc = compliance.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.driver_compliance.insert_one(doc)
    
    return compliance

@api_router.put("/drivers/{driver_id}/compliance/{compliance_id}")
async def update_driver_compliance(
    driver_id: str,
    compliance_id: str,
    update_data: DriverComplianceCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update driver compliance item"""
    driver = await db.drivers.find_one({"id": driver_id, "tenant_id": tenant_id}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    update_dict = update_data.model_dump()
    
    result = await db.driver_compliance.update_one(
        {"id": compliance_id, "driver_id": driver_id},
        {"$set": update_dict}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    
    compliance = await db.driver_compliance.find_one({"id": compliance_id}, {"_id": 0})
    return compliance

@api_router.delete("/drivers/{driver_id}/compliance/{compliance_id}")
async def delete_driver_compliance(
    driver_id: str,
    compliance_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete driver compliance item"""
    driver = await db.drivers.find_one({"id": driver_id, "tenant_id": tenant_id}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    result = await db.driver_compliance.delete_one({"id": compliance_id, "driver_id": driver_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Compliance item not found")
    
    return {"message": "Compliance item deleted"}

# ============ COMPLIANCE REMINDERS ============

@api_router.get("/reminders")
async def get_compliance_reminders(tenant_id: str = Depends(get_tenant_id)):
    """Get all upcoming compliance expirations grouped by urgency"""
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    week_later = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    month_later = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    
    reminders = {
        "overdue": [],
        "due_this_week": [],
        "due_this_month": [],
        "upcoming": []
    }
    
    # Get all vehicles
    vehicles = await db.vehicles.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    vehicle_map = {v["id"]: v for v in vehicles}
    
    # Get vehicle compliance items
    vehicle_compliance = await db.vehicle_compliance.find(
        {"vehicle_id": {"$in": list(vehicle_map.keys())}},
        {"_id": 0}
    ).to_list(500)
    
    for item in vehicle_compliance:
        vehicle = vehicle_map.get(item["vehicle_id"], {})
        reminder_date = (datetime.strptime(item["expiry_date"], "%Y-%m-%d") - 
                        timedelta(days=item.get("reminder_days_before", 30))).strftime("%Y-%m-%d")
        
        # Only include if within reminder window or overdue
        if item["expiry_date"] < today_str or reminder_date <= today_str:
            entry = {
                "type": "vehicle",
                "entity_id": item["vehicle_id"],
                "entity_name": vehicle.get("name", "Unknown"),
                "registration": vehicle.get("registration_number", ""),
                "compliance_id": item["id"],
                "item_type": item["item_type"],
                "item_label": item.get("item_label") or item["item_type"].replace("_", " ").title(),
                "expiry_date": item["expiry_date"],
                "notify_channels": item.get("notify_channels", []),
                "provider": item.get("provider"),
                "policy_number": item.get("policy_number")
            }
            
            if item["expiry_date"] < today_str:
                reminders["overdue"].append(entry)
            elif item["expiry_date"] <= week_later:
                reminders["due_this_week"].append(entry)
            elif item["expiry_date"] <= month_later:
                reminders["due_this_month"].append(entry)
            else:
                reminders["upcoming"].append(entry)
    
    # Get all drivers
    drivers = await db.drivers.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    driver_map = {d["id"]: d for d in drivers}
    
    # Get driver compliance items
    driver_compliance = await db.driver_compliance.find(
        {"driver_id": {"$in": list(driver_map.keys())}},
        {"_id": 0}
    ).to_list(500)
    
    for item in driver_compliance:
        driver = driver_map.get(item["driver_id"], {})
        reminder_date = (datetime.strptime(item["expiry_date"], "%Y-%m-%d") - 
                        timedelta(days=item.get("reminder_days_before", 30))).strftime("%Y-%m-%d")
        
        # Only include if within reminder window or overdue
        if item["expiry_date"] < today_str or reminder_date <= today_str:
            entry = {
                "type": "driver",
                "entity_id": item["driver_id"],
                "entity_name": driver.get("name", "Unknown"),
                "phone": driver.get("phone", ""),
                "compliance_id": item["id"],
                "item_type": item["item_type"],
                "item_label": item.get("item_label") or item["item_type"].replace("_", " ").title(),
                "expiry_date": item["expiry_date"],
                "notify_channels": item.get("notify_channels", []),
                "license_number": item.get("license_number"),
                "issuing_country": item.get("issuing_country")
            }
            
            if item["expiry_date"] < today_str:
                reminders["overdue"].append(entry)
            elif item["expiry_date"] <= week_later:
                reminders["due_this_week"].append(entry)
            elif item["expiry_date"] <= month_later:
                reminders["due_this_month"].append(entry)
            else:
                reminders["upcoming"].append(entry)
    
    # Sort each category by expiry date
    for category in reminders:
        reminders[category].sort(key=lambda x: x["expiry_date"])
    
    return {
        "reminders": reminders,
        "summary": {
            "overdue": len(reminders["overdue"]),
            "due_this_week": len(reminders["due_this_week"]),
            "due_this_month": len(reminders["due_this_month"]),
            "upcoming": len(reminders["upcoming"]),
            "total": sum(len(reminders[k]) for k in reminders)
        }
    }

# ============ DASHBOARD STATS ============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(tenant_id: str = Depends(get_tenant_id)):
    """Get dashboard statistics"""
    # Count totals
    total_clients = await db.clients.count_documents({"tenant_id": tenant_id, "status": "active"})
    total_shipments = await db.shipments.count_documents({"tenant_id": tenant_id})
    total_trips = await db.trips.count_documents({"tenant_id": tenant_id})
    
    # Status counts
    warehouse_count = await db.shipments.count_documents({"tenant_id": tenant_id, "status": "warehouse"})
    in_transit_count = await db.shipments.count_documents({"tenant_id": tenant_id, "status": "in_transit"})
    delivered_count = await db.shipments.count_documents({"tenant_id": tenant_id, "status": "delivered"})
    
    # Recent shipments
    recent_shipments = await db.shipments.find(
        {"tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    # Enrich with client names
    for shipment in recent_shipments:
        client = await db.clients.find_one({"id": shipment["client_id"]}, {"_id": 0, "name": 1})
        shipment["client_name"] = client["name"] if client else "Unknown"
    
    return {
        "total_clients": total_clients,
        "total_shipments": total_shipments,
        "total_trips": total_trips,
        "shipment_status": {
            "warehouse": warehouse_count,
            "in_transit": in_transit_count,
            "delivered": delivered_count
        },
        "recent_shipments": recent_shipments
    }

# ============ HEALTH CHECK ============

@api_router.get("/")
async def root():
    return {"message": "AfroFreight Logistics API", "status": "healthy"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_indexes():
    """Create indexes on startup"""
    # Tenants
    await db.tenants.create_index("subdomain", unique=True)
    
    # Users
    await db.users.create_index("tenant_id")
    await db.users.create_index([("tenant_id", 1), ("email", 1)], unique=True)
    
    # Clients
    await db.clients.create_index("tenant_id")
    await db.clients.create_index("status")
    
    # Shipments
    await db.shipments.create_index("tenant_id")
    await db.shipments.create_index("client_id")
    await db.shipments.create_index("trip_id")
    await db.shipments.create_index("status")
    await db.shipments.create_index("created_at")
    
    # Shipment Pieces
    await db.shipment_pieces.create_index("shipment_id")
    await db.shipment_pieces.create_index("barcode", unique=True)
    
    # Trips
    await db.trips.create_index("tenant_id")
    await db.trips.create_index([("tenant_id", 1), ("trip_number", 1)], unique=True)
    await db.trips.create_index("status")
    await db.trips.create_index("departure_date")
    
    # Trip Expenses
    await db.trip_expenses.create_index("trip_id")
    await db.trip_expenses.create_index("expense_date")
    
    # Invoices
    await db.invoices.create_index("tenant_id")
    await db.invoices.create_index([("tenant_id", 1), ("invoice_number", 1)], unique=True)
    await db.invoices.create_index("status")
    await db.invoices.create_index("client_id")
    await db.invoices.create_index("trip_id")
    await db.invoices.create_index("due_date")
    
    # Invoice Line Items
    await db.invoice_line_items.create_index("invoice_id")
    
    # Payments
    await db.payments.create_index("tenant_id")
    await db.payments.create_index("client_id")
    await db.payments.create_index("invoice_id")
    await db.payments.create_index("payment_date")
    
    # Client Rates
    await db.client_rates.create_index("client_id")
    
    # Vehicles
    await db.vehicles.create_index("tenant_id")
    await db.vehicles.create_index("status")
    
    # Vehicle Compliance
    await db.vehicle_compliance.create_index("vehicle_id")
    await db.vehicle_compliance.create_index("expiry_date")
    
    # Drivers
    await db.drivers.create_index("tenant_id")
    await db.drivers.create_index("status")
    
    # Driver Compliance
    await db.driver_compliance.create_index("driver_id")
    await db.driver_compliance.create_index("expiry_date")
    
    # Sessions
    await db.user_sessions.create_index("session_token")
    await db.user_sessions.create_index("user_id")
    
    logger.info("Database indexes created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
