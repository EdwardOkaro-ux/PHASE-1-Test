"""
Fleet routes for Servex Holdings backend.
Handles vehicle and driver management including compliance tracking.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import base64

from database import db
from dependencies import get_current_user, get_tenant_id
from models.schemas import Vehicle, VehicleCreate, VehicleUpdate, VehicleCompliance, VehicleComplianceCreate, Driver, DriverCreate, DriverUpdate, DriverCompliance, DriverComplianceCreate, NotificationCreate, WhatsAppLogCreate
from models.enums import VehicleStatus, VehicleComplianceType, DriverStatus, DriverComplianceType, WhatsAppStatus

router = APIRouter()

@router.get("/vehicles")
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

@router.get("/vehicles/{vehicle_id}")
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

@router.post("/vehicles")
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

@router.put("/vehicles/{vehicle_id}")
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

@router.delete("/vehicles/{vehicle_id}")
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
@router.get("/vehicles/{vehicle_id}/compliance")
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

@router.post("/vehicles/{vehicle_id}/compliance")
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

@router.put("/vehicles/{vehicle_id}/compliance/{compliance_id}")
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

@router.delete("/vehicles/{vehicle_id}/compliance/{compliance_id}")
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

@router.get("/drivers")
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

@router.get("/drivers/{driver_id}")
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

@router.post("/drivers")
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

@router.put("/drivers/{driver_id}")
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

@router.delete("/drivers/{driver_id}")
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
@router.get("/drivers/{driver_id}/compliance")
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

@router.post("/drivers/{driver_id}/compliance")
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

@router.put("/drivers/{driver_id}/compliance/{compliance_id}")
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

@router.delete("/drivers/{driver_id}/compliance/{compliance_id}")
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

@router.get("/reminders")
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

@router.get("/compliance/all")
async def get_all_compliance_items(tenant_id: str = Depends(get_tenant_id)):
    """Get ALL compliance items (vehicles and drivers) sorted by expiry date ascending"""
    today = datetime.now(timezone.utc)
    today_str = today.strftime("%Y-%m-%d")
    thirty_days = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    sixty_days = (today + timedelta(days=60)).strftime("%Y-%m-%d")
    
    all_items = []
    
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
        expiry = item["expiry_date"]
        
        # Determine status color
        if expiry < today_str or expiry <= thirty_days:
            status_color = "red"
        elif expiry <= sixty_days:
            status_color = "yellow"
        else:
            status_color = "green"
        
        all_items.append({
            "type": "vehicle",
            "entity_id": item["vehicle_id"],
            "entity_name": vehicle.get("name", "Unknown"),
            "registration": vehicle.get("registration_number", ""),
            "compliance_id": item["id"],
            "item_type": item["item_type"],
            "item_label": item.get("item_label") or item["item_type"].replace("_", " ").title(),
            "expiry_date": expiry,
            "status_color": status_color,
            "provider": item.get("provider"),
            "policy_number": item.get("policy_number"),
            "file_name": item.get("file_name"),
            "file_type": item.get("file_type")
        })
    
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
        expiry = item["expiry_date"]
        
        # Determine status color
        if expiry < today_str or expiry <= thirty_days:
            status_color = "red"
        elif expiry <= sixty_days:
            status_color = "yellow"
        else:
            status_color = "green"
        
        all_items.append({
            "type": "driver",
            "entity_id": item["driver_id"],
            "entity_name": driver.get("name", "Unknown"),
            "phone": driver.get("phone", ""),
            "compliance_id": item["id"],
            "item_type": item["item_type"],
            "item_label": item.get("item_label") or item["item_type"].replace("_", " ").title(),
            "expiry_date": expiry,
            "status_color": status_color,
            "license_number": item.get("license_number"),
            "issuing_country": item.get("issuing_country"),
            "file_name": item.get("file_name"),
            "file_type": item.get("file_type")
        })
    
    # Sort all items by expiry date ascending
    all_items.sort(key=lambda x: x["expiry_date"])
    
    return all_items

# ============ DASHBOARD STATS ============

@router.get("/dashboard/stats")
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

# ============ AUDIT LOG ENDPOINTS ============

@router.get("/audit-logs/{table_name}/{record_id}")
async def get_audit_history(
    table_name: str,
    record_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get audit history for a specific record"""
    logs = []
    cursor = db.audit_logs.find(
        {"tenant_id": tenant_id, "table_name": table_name, "record_id": record_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(50)
    
    async for log in cursor:
        # Get user name
        user = await db.users.find_one({"id": log["user_id"]}, {"_id": 0, "name": 1})
        log["user_name"] = user["name"] if user else "Unknown"
        logs.append(log)
    
    return logs

# ============ NOTIFICATION ENDPOINTS ============

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get notifications for the current user"""
    query = {"tenant_id": tenant_id, "user_id": user["id"]}
    if unread_only:
        query["read_at"] = None
    
    notifications = []
    cursor = db.notifications.find(query, {"_id": 0}).sort("created_at", -1).limit(50)
    async for notification in cursor:
        notifications.append(notification)
    
    return notifications

@router.get("/notifications/count")
async def get_unread_notification_count(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "tenant_id": tenant_id,
        "user_id": user["id"],
        "read_at": None
    })
    return {"unread_count": count}

@router.post("/notifications")
async def create_notification_endpoint(
    notification_data: NotificationCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new notification"""
    notification = Notification(
        tenant_id=tenant_id,
        **notification_data.model_dump()
    )
    await db.notifications.insert_one(notification.model_dump())
    return {"id": notification.id, "message": "Notification created"}

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "tenant_id": tenant_id, "user_id": user["id"]},
        {"$set": {"read_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    result = await db.notifications.update_many(
        {"tenant_id": tenant_id, "user_id": user["id"], "read_at": None},
        {"$set": {"read_at": datetime.now(timezone.utc)}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

@router.put("/notifications/{notification_id}/resolve")
async def resolve_notification(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as resolved"""
    result = await db.notifications.update_one(
        {"id": notification_id, "tenant_id": tenant_id, "user_id": user["id"]},
        {"$set": {"resolved_at": datetime.now(timezone.utc), "read_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification resolved"}

# ============ WHATSAPP LOG ENDPOINTS ============

@router.get("/whatsapp-logs")
async def list_whatsapp_logs(
    invoice_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get WhatsApp message logs"""
    query = {"tenant_id": tenant_id}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    logs = []
    cursor = db.whatsapp_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(100)
    async for log in cursor:
        logs.append(log)
    
    return logs

@router.post("/whatsapp-logs")
async def create_whatsapp_log(
    log_data: WhatsAppLogCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new WhatsApp log entry"""
    log = WhatsAppLog(
        tenant_id=tenant_id,
        sent_by=user["id"],
        **log_data.model_dump()
    )
    await db.whatsapp_logs.insert_one(log.model_dump())
    return {"id": log.id, "message": "WhatsApp log created"}

@router.put("/whatsapp-logs/{log_id}/status")
async def update_whatsapp_status(
    log_id: str,
    status: WhatsAppStatus,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update WhatsApp message status (webhook callback)"""
    update_data = {"status": status.value}
    if status == WhatsAppStatus.delivered:
        update_data["delivered_at"] = datetime.now(timezone.utc)
    elif status == WhatsAppStatus.read:
        update_data["read_at"] = datetime.now(timezone.utc)
    
    result = await db.whatsapp_logs.update_one(
        {"id": log_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="WhatsApp log not found")
    return {"message": "Status updated"}
