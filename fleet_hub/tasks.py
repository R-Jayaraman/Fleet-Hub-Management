import frappe
from frappe.utils import add_days, getdate, nowdate


def daily():
	document_expiry_sweep()
	license_expiry_sweep()
	service_due_sweep()


def weekly():
	vehicle_status_self_heal()


def document_expiry_sweep():
	"""Recompute Vehicle Document status and log alerts for Expiring Soon / Expired documents."""
	alert_days = frappe.db.get_single_value("Fleet Settings", "document_expiry_alert_days") or 30
	today = getdate(nowdate())

	documents = frappe.get_all(
		"Vehicle Document",
		filters={"expiry_date": ["is", "set"]},
		fields=["name", "vehicle", "document_type", "expiry_date", "status"],
	)

	for doc in documents:
		expiry = getdate(doc.expiry_date)
		if expiry < today:
			new_status = "Expired"
			severity = "Critical"
		elif expiry <= add_days(today, alert_days):
			new_status = "Expiring Soon"
			severity = "Warning"
		else:
			new_status = "Valid"
			severity = None

		if new_status != doc.status:
			frappe.db.set_value("Vehicle Document", doc.name, "status", new_status)

		if severity:
			_create_alert_if_missing(
				alert_type=f"{doc.document_type} Expiry"
				if doc.document_type in ("Insurance",)
				else "Document Expiry",
				reference_doctype="Vehicle Document",
				reference_name=doc.name,
				vehicle=doc.vehicle,
				due_date=doc.expiry_date,
				severity=severity,
				message=f"{doc.document_type} document for vehicle {doc.vehicle} is {new_status.lower()} (expiry: {doc.expiry_date}).",
			)


def license_expiry_sweep():
	"""Check driver license expiry and log alerts / optionally auto-suspend."""
	alert_days = frappe.db.get_single_value("Fleet Settings", "license_expiry_alert_days") or 30
	auto_suspend = frappe.db.get_single_value("Fleet Settings", "auto_suspend_on_license_expiry")
	today = getdate(nowdate())

	drivers = frappe.get_all(
		"Fleet Driver",
		filters={"license_expiry_date": ["is", "set"], "status": ["!=", "Inactive"]},
		fields=["name", "license_expiry_date", "status"],
	)

	for driver in drivers:
		expiry = getdate(driver.license_expiry_date)
		if expiry < today:
			_create_alert_if_missing(
				alert_type="License Expiry",
				reference_doctype="Fleet Driver",
				reference_name=driver.name,
				driver=driver.name,
				due_date=driver.license_expiry_date,
				severity="Critical",
				message=f"Driver {driver.name}'s license expired on {driver.license_expiry_date}.",
			)
			if auto_suspend and driver.status != "Suspended":
				frappe.db.set_value("Fleet Driver", driver.name, "status", "Suspended")
		elif expiry <= add_days(today, alert_days):
			_create_alert_if_missing(
				alert_type="License Expiry",
				reference_doctype="Fleet Driver",
				reference_name=driver.name,
				driver=driver.name,
				due_date=driver.license_expiry_date,
				severity="Warning",
				message=f"Driver {driver.name}'s license expires on {driver.license_expiry_date}.",
			)


def service_due_sweep():
	"""Check Service Schedule due dates/odometer against the linked Vehicle's current odometer."""
	km_threshold = frappe.db.get_single_value("Fleet Settings", "service_due_alert_km") or 500
	days_threshold = frappe.db.get_single_value("Fleet Settings", "service_due_alert_days") or 15
	today = getdate(nowdate())

	schedules = frappe.get_all(
		"Service Schedule",
		filters={"is_active": 1, "vehicle": ["is", "set"]},
		fields=["name", "vehicle", "next_due_date", "next_due_odometer"],
	)

	for schedule in schedules:
		current_odometer = frappe.db.get_value("Fleet Vehicle", schedule.vehicle, "current_odometer") or 0
		due_soon = False
		reasons = []

		if schedule.next_due_date and getdate(schedule.next_due_date) <= add_days(today, days_threshold):
			due_soon = True
			reasons.append(f"due by {schedule.next_due_date}")

		if schedule.next_due_odometer and (schedule.next_due_odometer - current_odometer) <= km_threshold:
			due_soon = True
			reasons.append(f"due at {schedule.next_due_odometer} km (current: {current_odometer} km)")

		if due_soon:
			_create_alert_if_missing(
				alert_type="Service Due",
				reference_doctype="Service Schedule",
				reference_name=schedule.name,
				vehicle=schedule.vehicle,
				due_date=schedule.next_due_date,
				severity="Warning",
				message=f"Service for vehicle {schedule.vehicle} is {', '.join(reasons)}.",
			)


def vehicle_status_self_heal():
	"""Detect vehicles stuck in On Trip / Under Maintenance with no matching active record."""
	stuck_on_trip = frappe.get_all(
		"Fleet Vehicle",
		filters={"current_status": "On Trip"},
		fields=["name", "current_driver"],
	)
	for vehicle in stuck_on_trip:
		has_active_trip = frappe.db.exists(
			"Fleet Trip", {"vehicle": vehicle.name, "status": "In Progress", "docstatus": ["!=", 2]}
		)
		if not has_active_trip:
			fallback_status = "Assigned" if vehicle.current_driver else "Available"
			frappe.db.set_value("Fleet Vehicle", vehicle.name, "current_status", fallback_status)

	stuck_in_maintenance = frappe.get_all(
		"Fleet Vehicle",
		filters={"current_status": "Under Maintenance"},
		fields=["name", "current_driver"],
	)
	for vehicle in stuck_in_maintenance:
		has_active_maintenance = frappe.db.exists(
			"Vehicle Maintenance", {"vehicle": vehicle.name, "status": "In Progress", "docstatus": ["!=", 2]}
		)
		if not has_active_maintenance:
			fallback_status = "Assigned" if vehicle.current_driver else "Available"
			frappe.db.set_value("Fleet Vehicle", vehicle.name, "current_status", fallback_status)


def _create_alert_if_missing(
	alert_type, reference_doctype, reference_name, severity, message, due_date=None, vehicle=None, driver=None
):
	"""Avoid spamming duplicate unresolved alerts for the same reference on the same day."""
	existing = frappe.db.exists(
		"Fleet Alert Log",
		{
			"alert_type": alert_type,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"is_resolved": 0,
			"alert_date": getdate(nowdate()),
		},
	)
	if existing:
		return

	frappe.get_doc(
		{
			"doctype": "Fleet Alert Log",
			"alert_type": alert_type,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"vehicle": vehicle,
			"driver": driver,
			"due_date": due_date,
			"severity": severity,
			"message": message,
		}
	).insert(ignore_permissions=True)
