import frappe
from frappe import _
from frappe.model.document import Document


class VehicleAssignment(Document):
	def validate(self):
		self.validate_vehicle_and_driver_status()
		self.validate_single_active_assignment()
		self.validate_odometer()

	def validate_vehicle_and_driver_status(self):
		vehicle_status = frappe.db.get_value("Fleet Vehicle", self.vehicle, "current_status")
		if vehicle_status == "Inactive":
			frappe.throw(_("Cannot assign Vehicle {0} because it is Inactive.").format(self.vehicle))

		driver_status = frappe.db.get_value("Fleet Driver", self.driver, "status")
		if driver_status != "Active":
			frappe.throw(
				_("Cannot assign Driver {0} because their status is {1}.").format(self.driver, driver_status)
			)

	def validate_single_active_assignment(self):
		if self.status != "Active":
			return

		existing_for_vehicle = frappe.db.exists(
			"Vehicle Assignment",
			{"vehicle": self.vehicle, "status": "Active", "name": ("!=", self.name)},
		)
		if existing_for_vehicle:
			frappe.throw(
				_("Vehicle {0} already has an active assignment ({1}).").format(
					self.vehicle, existing_for_vehicle
				)
			)

		existing_for_driver = frappe.db.exists(
			"Vehicle Assignment",
			{"driver": self.driver, "status": "Active", "name": ("!=", self.name)},
		)
		if existing_for_driver:
			frappe.throw(
				_("Driver {0} already has an active assignment ({1}).").format(
					self.driver, existing_for_driver
				)
			)

	def validate_odometer(self):
		if self.end_date and not self.end_odometer:
			frappe.throw(_("End Odometer is required when End Date is set."))
		if self.end_odometer and self.end_odometer < self.start_odometer:
			frappe.throw(_("End Odometer cannot be less than Start Odometer."))

	def on_update(self):
		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if self.status == "Active":
			vehicle.db_set("current_driver", self.driver)
			if vehicle.current_status not in ("On Trip", "Under Maintenance"):
				vehicle.db_set("current_status", "Assigned")
		elif self.status in ("Completed", "Cancelled") and vehicle.current_driver == self.driver:
			vehicle.db_set("current_driver", None)
			if vehicle.current_status not in ("On Trip", "Under Maintenance"):
				vehicle.db_set("current_status", "Available")
