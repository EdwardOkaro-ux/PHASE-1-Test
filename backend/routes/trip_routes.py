"""
Trip routes for Servex Holdings backend.
Handles trip CRUD operations, trip details, and expense management.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id
from models.schemas import Trip, TripCreate, TripUpdate, TripExpense, TripExpenseCreate, TripExpenseUpdate, create_audit_log
from models.enums import TripStatus, ExpenseCategory, AuditAction
from services.barcode_service import generate_barcode

router = APIRouter()

@router.get("/trips/next-number")
async def get_next_trip_number(tenant_id: str = Depends(get_tenant_id)):
    """Get the next sequential trip number for creating a new trip"""
    # Find the latest trip number starting with 'S' followed by 1-4 digits only
    trips = await db.trips.find(
        {"tenant_id": tenant_id, "trip_number": {"$regex": "^S\\d{1,4}$"}},
        {"trip_number": 1, "_id": 0}
    ).to_list(1000)
    
    max_num = 0
    for trip in trips:
        try:
            num = int(trip["trip_number"][1:])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue
    
    next_number = f"S{max_num + 1}"
    return {"next_trip_number": next_number}

@router.get("/trips", response_model=List[Trip])
async def list_trips(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all trips. Status can be comma-separated for multiple values (e.g., 'planning,loading')"""
    query = {"tenant_id": tenant_id}
    if status:
        # Support comma-separated status values
        if "," in status:
            query["status"] = {"$in": status.split(",")}
        else:
            query["status"] = status
    
    trips = await db.trips.find(query, {"_id": 0}).sort("departure_date", -1).to_list(100)
    return trips
    return trips

@router.get("/trips/{trip_id}")
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

@router.post("/trips", response_model=Trip)
async def create_trip(
    request: Request,
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
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.create,
        table_name="trips",
        record_id=trip.id,
        new_value=doc,
        ip_address=request.client.host if request.client else None
    )
    
    return trip

@router.put("/trips/{trip_id}")
async def update_trip(
    request: Request,
    trip_id: str,
    update_data: TripUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update trip - handles locking when status changes to 'closed'"""
    # Get current trip
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    old_trip = dict(trip)
    
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
    
    # Determine action type
    action = AuditAction.status_change if "status" in update_dict else AuditAction.update
    
    # Handle status change to 'closed' - set locked_at timestamp
    if update_dict.get("status") == "closed" and trip.get("status") != "closed":
        update_dict["locked_at"] = datetime.now(timezone.utc).isoformat()
    
    # Handle status change to 'in_transit' - set actual_departure timestamp
    if update_dict.get("status") == "in_transit" and trip.get("status") != "in_transit":
        if not trip.get("actual_departure"):
            update_dict["actual_departure"] = datetime.now(timezone.utc).isoformat()
    
    # Handle status change to 'delivered' - set actual_arrival timestamp
    if update_dict.get("status") == "delivered" and trip.get("status") != "delivered":
        if not trip.get("actual_arrival"):
            update_dict["actual_arrival"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.trips.update_one(
            {"id": trip_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    new_trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=action,
        table_name="trips",
        record_id=trip_id,
        old_value=old_trip,
        new_value=new_trip,
        ip_address=request.client.host if request.client else None
    )
    
    return new_trip

@router.delete("/trips/{trip_id}")
async def delete_trip(
    request: Request,
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a trip (only if not locked or user is owner)"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    old_trip = dict(trip)
    
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
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.delete,
        table_name="trips",
        record_id=trip_id,
        old_value=old_trip,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Trip deleted"}

@router.post("/trips/{trip_id}/assign-shipment/{shipment_id}")
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

@router.post("/trips/{trip_id}/unassign-shipment/{shipment_id}")
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

@router.get("/trips/{trip_id}/summary")
async def get_trip_summary(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get comprehensive trip summary with statistics"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get vehicle details if assigned
    vehicle = None
    if trip.get("vehicle_id"):
        vehicle = await db.vehicles.find_one({"id": trip["vehicle_id"]}, {"_id": 0})
    
    # Get driver details if assigned
    driver = None
    if trip.get("driver_id"):
        driver = await db.drivers.find_one({"id": trip["driver_id"]}, {"_id": 0})
    
    # Get shipments assigned to this trip
    shipments = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Calculate stats
    total_parcels = len(shipments)
    total_weight = sum(s.get("total_weight", 0) or 0 for s in shipments)
    unique_clients = set(s.get("client_id") for s in shipments if s.get("client_id"))
    
    # Count pieces
    total_pieces = 0
    for shipment in shipments:
        pieces = await db.shipment_pieces.count_documents({"shipment_id": shipment["id"]})
        total_pieces += pieces
    
    # Count loaded parcels (status in ['staged', 'loaded', 'in_transit', 'delivered'])
    loaded_statuses = ['staged', 'loaded', 'in_transit', 'delivered']
    loaded_parcels = sum(1 for s in shipments if s.get("status") in loaded_statuses)
    loading_percentage = round((loaded_parcels / total_parcels * 100) if total_parcels > 0 else 0)
    
    # Get invoiced value - query invoices by BOTH trip_id and shipment_ids
    shipment_ids = [s["id"] for s in shipments]
    
    # First get invoices linked directly by trip_id
    trip_invoices = await db.invoices.find(
        {"tenant_id": tenant_id, "trip_id": trip_id},
        {"id": 1, "total": 1, "_id": 0}
    ).to_list(1000)
    
    # Also get invoices linked by shipment_ids (for backward compatibility)
    shipment_invoices = await db.invoices.find(
        {"tenant_id": tenant_id, "shipment_ids": {"$in": shipment_ids}},
        {"id": 1, "total": 1, "_id": 0}
    ).to_list(1000) if shipment_ids else []
    
    # Combine and deduplicate
    seen_invoice_ids = set()
    invoiced_value = 0
    for inv in trip_invoices + shipment_invoices:
        if inv["id"] not in seen_invoice_ids:
            seen_invoice_ids.add(inv["id"])
            invoiced_value += inv.get("total", 0) or 0
    
    # Get created by user
    created_by_user = None
    if trip.get("created_by"):
        created_by_user = await db.users.find_one({"id": trip["created_by"]}, {"name": 1, "_id": 0})
    
    return {
        "trip": {
            **trip,
            "vehicle": vehicle,
            "driver": driver
        },
        "stats": {
            "total_parcels": total_parcels,
            "total_pieces": total_pieces,
            "total_weight": round(total_weight, 2),
            "total_clients": len(unique_clients),
            "invoiced_value": round(invoiced_value, 2),
            "loaded_parcels": loaded_parcels,
            "loading_percentage": loading_percentage
        },
        "created_by": created_by_user.get("name") if created_by_user else None,
        "created_at": trip.get("created_at")
    }

@router.get("/trips-with-stats")
async def list_trips_with_stats(
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all trips with calculated statistics"""
    query = {"tenant_id": tenant_id}
    if status and status != "all":
        query["status"] = status
    
    trips = await db.trips.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    result = []
    for trip in trips:
        # Get shipments for this trip
        shipments = await db.shipments.find(
            {"trip_id": trip["id"], "tenant_id": tenant_id},
            {"_id": 0, "id": 1, "total_weight": 1, "client_id": 1, "status": 1}
        ).to_list(1000)
        
        total_parcels = len(shipments)
        total_weight = sum(s.get("total_weight", 0) or 0 for s in shipments)
        unique_clients = set(s.get("client_id") for s in shipments if s.get("client_id"))
        
        # Count loaded
        loaded_statuses = ['staged', 'loaded', 'in_transit', 'delivered']
        loaded_parcels = sum(1 for s in shipments if s.get("status") in loaded_statuses)
        loading_percentage = round((loaded_parcels / total_parcels * 100) if total_parcels > 0 else 0)
        
        # Get invoiced value - query by BOTH trip_id and shipment_ids
        shipment_ids = [s["id"] for s in shipments]
        
        # Get invoices linked by trip_id
        trip_invoices = await db.invoices.find(
            {"tenant_id": tenant_id, "trip_id": trip["id"]},
            {"id": 1, "total": 1, "_id": 0}
        ).to_list(1000)
        
        # Also get invoices linked by shipment_ids
        shipment_invoices = []
        if shipment_ids:
            shipment_invoices = await db.invoices.find(
                {"tenant_id": tenant_id, "shipment_ids": {"$in": shipment_ids}},
                {"id": 1, "total": 1, "_id": 0}
            ).to_list(1000)
        
        # Combine and deduplicate
        seen_invoice_ids = set()
        invoiced_value = 0
        for inv in trip_invoices + shipment_invoices:
            if inv["id"] not in seen_invoice_ids:
                seen_invoice_ids.add(inv["id"])
                invoiced_value += inv.get("total", 0) or 0
        
        # Get vehicle and driver info
        vehicle = None
        if trip.get("vehicle_id"):
            vehicle = await db.vehicles.find_one({"id": trip["vehicle_id"]}, {"_id": 0, "registration_number": 1, "vehicle_type": 1})
        
        driver = None
        if trip.get("driver_id"):
            driver = await db.drivers.find_one({"id": trip["driver_id"]}, {"_id": 0, "name": 1, "phone": 1})
        
        result.append({
            **trip,
            "vehicle": vehicle,
            "driver": driver,
            "stats": {
                "total_parcels": total_parcels,
                "total_weight": round(total_weight, 2),
                "total_clients": len(unique_clients),
                "invoiced_value": round(invoiced_value, 2),
                "loaded_parcels": loaded_parcels,
                "loading_percentage": loading_percentage
            }
        })
    
    return result

# ============ TRIP EXPENSES ROUTES ============

@router.get("/trips/{trip_id}/expenses", response_model=List[TripExpense])
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

@router.post("/trips/{trip_id}/expenses", response_model=TripExpense)
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

@router.put("/trips/{trip_id}/expenses/{expense_id}")
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

@router.delete("/trips/{trip_id}/expenses/{expense_id}")
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

@router.get("/trips/{trip_id}/parcels")
async def get_trip_parcels(
    trip_id: str,
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get all parcels assigned to a trip with detailed info"""
    # Verify trip exists
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Build query
    query = {"trip_id": trip_id, "tenant_id": tenant_id}
    if status and status != "all":
        if status == "not_loaded":
            query["status"] = {"$in": ["warehouse", "staged"]}
        elif status == "loaded":
            query["status"] = "loaded"
        elif status == "delivered":
            query["status"] = "delivered"
    
    parcels = await db.shipments.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Enrich with client names and piece counts
    result = []
    for parcel in parcels:
        client = await db.clients.find_one({"id": parcel.get("client_id")}, {"_id": 0, "name": 1})
        pieces = await db.shipment_pieces.find({"shipment_id": parcel["id"]}, {"_id": 0}).to_list(100)
        
        result.append({
            **parcel,
            "client_name": client.get("name") if client else "Unknown",
            "pieces": pieces,
            "piece_count": len(pieces)
        })
    
    return result

@router.get("/trips/{trip_id}/clients-summary")
async def get_trip_clients_summary(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get client summary for a trip with invoice info"""
    # Verify trip exists
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get all parcels for this trip
    parcels = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(500)
    
    # Group by client
    client_data = {}
    for parcel in parcels:
        client_id = parcel.get("client_id")
        if not client_id:
            continue
        
        if client_id not in client_data:
            client = await db.clients.find_one({"id": client_id}, {"_id": 0})
            client_data[client_id] = {
                "client_id": client_id,
                "client_name": client.get("name") if client else "Unknown",
                "client_phone": client.get("phone") if client else None,
                "parcel_count": 0,
                "total_weight": 0,
                "shipment_ids": [],
                "invoices": []
            }
        
        client_data[client_id]["parcel_count"] += 1
        client_data[client_id]["total_weight"] += parcel.get("total_weight", 0) or 0
        client_data[client_id]["shipment_ids"].append(parcel["id"])
    
    # Get invoices for this trip (query by BOTH trip_id and shipment_ids)
    trip_invoices = await db.invoices.find(
        {"tenant_id": tenant_id, "trip_id": trip_id},
        {"_id": 0}
    ).to_list(100)
    
    # Build a map of client_id -> invoices from trip_invoices
    trip_invoice_map = {}
    for inv in trip_invoices:
        cid = inv.get("client_id")
        if cid:
            if cid not in trip_invoice_map:
                trip_invoice_map[cid] = []
            trip_invoice_map[cid].append(inv)
    
    # For each client, add their invoices (from trip_id query OR shipment_ids query)
    for client_id, data in client_data.items():
        # First check invoices linked by trip_id
        client_invoices = trip_invoice_map.get(client_id, [])
        
        # Also check invoices linked by shipment_ids (for backward compatibility)
        if data["shipment_ids"]:
            shipment_invoices = await db.invoices.find(
                {"tenant_id": tenant_id, "client_id": client_id, "shipment_ids": {"$in": data["shipment_ids"]}},
                {"_id": 0}
            ).to_list(100)
            # Add any invoices not already in the list
            existing_ids = {inv["id"] for inv in client_invoices}
            for inv in shipment_invoices:
                if inv["id"] not in existing_ids:
                    client_invoices.append(inv)
        
        for inv in client_invoices:
            payments = await db.payments.find({"invoice_id": inv["id"]}, {"_id": 0, "amount": 1}).to_list(100)
            paid_amount = sum(p.get("amount", 0) for p in payments)
            data["invoices"].append({
                "id": inv["id"],
                "invoice_number": inv.get("invoice_number"),
                "total": inv.get("total", 0),
                "status": inv.get("status"),
                "paid_amount": paid_amount
            })
    
    # Also add any clients from trip invoices that aren't in the parcels list
    for client_id, invs in trip_invoice_map.items():
        if client_id not in client_data:
            client = await db.clients.find_one({"id": client_id}, {"_id": 0})
            client_data[client_id] = {
                "client_id": client_id,
                "client_name": client.get("name") if client else "Unknown",
                "client_phone": client.get("phone") if client else None,
                "parcel_count": 0,
                "total_weight": 0,
                "shipment_ids": [],
                "invoices": []
            }
            for inv in invs:
                payments = await db.payments.find({"invoice_id": inv["id"]}, {"_id": 0, "amount": 1}).to_list(100)
                paid_amount = sum(p.get("amount", 0) for p in payments)
                client_data[client_id]["invoices"].append({
                    "id": inv["id"],
                    "invoice_number": inv.get("invoice_number"),
                    "total": inv.get("total", 0),
                    "status": inv.get("status"),
                    "paid_amount": paid_amount
                })
    
    # Calculate totals
    result = list(client_data.values())
    totals = {
        "total_clients": len(result),
        "total_parcels": sum(c["parcel_count"] for c in result),
        "total_weight": round(sum(c["total_weight"] for c in result), 2),
        "total_invoiced": sum(sum(inv["total"] for inv in c["invoices"]) for c in result),
        "total_paid": sum(sum(inv["paid_amount"] for inv in c["invoices"]) for c in result)
    }
    
    return {"clients": result, "totals": totals}

@router.get("/trips/{trip_id}/history")
async def get_trip_history(
    trip_id: str,
    filter_type: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get audit history for a trip and related records"""
    # Verify trip exists
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get shipment IDs for this trip
    shipments = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"id": 1, "_id": 0}
    ).to_list(500)
    shipment_ids = [s["id"] for s in shipments]
    
    # Build query for audit logs
    queries = [{"record_id": trip_id, "table_name": "trips"}]
    
    if filter_type == "parcels" or filter_type is None:
        for sid in shipment_ids:
            queries.append({"record_id": sid, "table_name": "shipments"})
    
    if filter_type == "expenses" or filter_type is None:
        expenses = await db.trip_expenses.find({"trip_id": trip_id}, {"id": 1, "_id": 0}).to_list(100)
        for exp in expenses:
            queries.append({"record_id": exp["id"], "table_name": "trip_expenses"})
    
    if filter_type == "invoices" or filter_type is None:
        invoices = await db.invoices.find(
            {"tenant_id": tenant_id, "shipment_ids": {"$in": shipment_ids}},
            {"id": 1, "_id": 0}
        ).to_list(100)
        for inv in invoices:
            queries.append({"record_id": inv["id"], "table_name": "invoices"})
    
    # Get audit logs
    audit_logs = await db.audit_logs.find(
        {"$or": queries, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    # Enrich with user names
    result = []
    user_cache = {}
    for log in audit_logs:
        user_id = log.get("user_id")
        if user_id and user_id not in user_cache:
            user = await db.users.find_one({"id": user_id}, {"name": 1, "_id": 0})
            user_cache[user_id] = user.get("name") if user else "Unknown"
        
        result.append({
            **log,
            "user_name": user_cache.get(user_id, "System")
        })
    
    return result

@router.post("/trips/{trip_id}/close")
async def close_trip(
    trip_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Close/lock a trip (owner only)"""
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can close trips")
    
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.get("locked_at"):
        raise HTTPException(status_code=400, detail="Trip is already closed")
    
    from datetime import datetime, timezone
    locked_at = datetime.now(timezone.utc).isoformat()
    
    old_value = dict(trip)
    await db.trips.update_one(
        {"id": trip_id},
        {"$set": {"status": "closed", "locked_at": locked_at}}
    )
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.update,
        table_name="trips",
        record_id=trip_id,
        old_value=old_value,
        new_value={"status": "closed", "locked_at": locked_at},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"Trip {trip.get('trip_number')} closed successfully", "locked_at": locked_at}

@router.post("/trips/{trip_id}/generate-invoices")
async def generate_trip_invoices(
    trip_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Generate invoices for all clients on a trip"""
    # Verify trip exists
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get all parcels grouped by client
    parcels = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(500)
    
    # Group by client
    client_parcels = {}
    for parcel in parcels:
        client_id = parcel.get("client_id")
        if not client_id:
            continue
        if client_id not in client_parcels:
            client_parcels[client_id] = []
        client_parcels[client_id].append(parcel)
    
    # Generate invoices for each client
    from datetime import datetime, timezone, timedelta
    invoices_created = []
    
    for client_id, client_shipments in client_parcels.items():
        # Check if invoice already exists for these shipments
        shipment_ids = [s["id"] for s in client_shipments]
        existing = await db.invoices.find_one({
            "tenant_id": tenant_id,
            "client_id": client_id,
            "shipment_ids": {"$all": shipment_ids}
        })
        if existing:
            continue
        
        # Get client info
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        
        # Generate invoice number
        year = datetime.now().year
        count = await db.invoices.count_documents({"tenant_id": tenant_id})
        invoice_number = f"INV-{year}-{str(count + 1).zfill(4)}"
        
        # Calculate totals
        total_weight = sum(s.get("total_weight", 0) or 0 for s in client_shipments)
        
        # Get client rate
        rate = await db.client_rates.find_one({"client_id": client_id}, {"_id": 0})
        rate_per_kg = rate.get("rate_per_kg", 50) if rate else 50
        
        subtotal = total_weight * rate_per_kg
        vat = subtotal * 0.15
        total = subtotal + vat
        
        invoice = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "client_id": client_id,
            "invoice_number": invoice_number,
            "shipment_ids": shipment_ids,
            "trip_id": trip_id,
            "subtotal": round(subtotal, 2),
            "vat": round(vat, 2),
            "total": round(total, 2),
            "status": "draft",
            "issue_date": datetime.now(timezone.utc).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "created_by": user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.invoices.insert_one(invoice)
        invoices_created.append({
            "invoice_number": invoice_number,
            "client_name": client.get("name") if client else "Unknown",
            "total": total
        })
    
    return {
        "message": f"Created {len(invoices_created)} invoice(s)",
        "invoices": invoices_created
    }

@router.delete("/trips/{trip_id}/parcels/{parcel_id}")
async def remove_parcel_from_trip(
    trip_id: str,
    parcel_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Remove a parcel from a trip (unassign)"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    if trip.get("locked_at"):
        raise HTTPException(status_code=403, detail="Cannot modify closed trip")
    
    parcel = await db.shipments.find_one({"id": parcel_id, "trip_id": trip_id}, {"_id": 0})
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found on this trip")
    
    old_value = dict(parcel)
    await db.shipments.update_one(
        {"id": parcel_id},
        {"$set": {"trip_id": None, "status": "warehouse"}}
    )
    
    # Reset barcodes to TEMP
    pieces = await db.shipment_pieces.find({"shipment_id": parcel_id}, {"_id": 0}).to_list(100)
    for piece in pieces:
        temp_barcode = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
        await db.shipment_pieces.update_one(
            {"id": piece["id"]},
            {"$set": {"barcode": temp_barcode}}
        )
    
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.update,
        table_name="shipments",
        record_id=parcel_id,
        old_value=old_value,
        new_value={"trip_id": None, "status": "warehouse"},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Parcel removed from trip"}


# ============ TRIP DOCUMENTS ROUTES ============

@router.get("/trips/{trip_id}/documents")
async def list_trip_documents(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all documents for a trip"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    docs = await db.trip_documents.find(
        {"trip_id": trip_id},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(100)
    
    # Enrich with uploader names
    result = []
    for doc in docs:
        uploader = await db.users.find_one({"id": doc.get("uploaded_by")}, {"name": 1, "_id": 0})
        result.append({
            **doc,
            "uploader_name": uploader.get("name") if uploader else "Unknown"
        })
    
    return result

@router.post("/trips/{trip_id}/documents")
async def upload_trip_document(
    trip_id: str,
    document: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Upload a document to a trip"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "file_name": document.get("file_name"),
        "file_type": document.get("file_type"),
        "file_data": document.get("file_data"),
        "category": document.get("category", "Other"),
        "uploaded_by": user["id"],
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trip_documents.insert_one(doc)
    
    return {"id": doc["id"], "message": "Document uploaded successfully"}

@router.delete("/trips/{trip_id}/documents/{doc_id}")
async def delete_trip_document(
    trip_id: str,
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a trip document"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    result = await db.trip_documents.delete_one({"id": doc_id, "trip_id": trip_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted"}

@router.get("/trips/{trip_id}/documents/{doc_id}/download")
async def download_trip_document(
    trip_id: str,
    doc_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get document data for download"""
    doc = await db.trip_documents.find_one({"id": doc_id, "trip_id": trip_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "file_name": doc["file_name"],
        "file_type": doc["file_type"],
        "file_data": doc["file_data"]
    }

# ============ TRIP DUPLICATE ROUTES ============

@router.post("/trips/{trip_id}/duplicate")
async def duplicate_trip(
    trip_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Duplicate a trip (creates new trip with same route and settings, but no parcels)"""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get next trip number
    trips = await db.trips.find(
        {"tenant_id": tenant_id, "trip_number": {"$regex": "^S\\d{1,4}$"}},
        {"trip_number": 1, "_id": 0}
    ).to_list(1000)
    
    max_num = 0
    for t in trips:
        try:
            num = int(t["trip_number"][1:])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError, TypeError):
            continue
    
    new_trip_number = f"S{max_num + 1}"
    
    new_trip = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "trip_number": new_trip_number,
        "status": "planning",
        "route": trip.get("route", []),
        "notes": f"Duplicated from {trip.get('trip_number')}",
        "vehicle_id": trip.get("vehicle_id"),
        "driver_id": trip.get("driver_id"),
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trips.insert_one(new_trip)
    
    return {"id": new_trip["id"], "trip_number": new_trip_number, "message": "Trip duplicated successfully"}
