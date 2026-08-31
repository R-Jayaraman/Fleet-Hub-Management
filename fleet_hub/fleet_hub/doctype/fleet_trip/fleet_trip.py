import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, nowdate


class FleetTrip(Document):
	def validate(self):
		self.validate_vehicle_and_driver()
		self.validate_datetimes()
		self.calculate_distance()
		self.update_vehicle_status_for_draft_states()

	def validate_vehicle_and_driver(self):
		vehicle_status = frappe.db.get_value("Fleet Vehicle", self.vehicle, "current_status")
		if vehicle_status == "Inactive":
			frappe.throw(
				_("Cannot create a Trip for Vehicle {0} because it is Inactive.").format(self.vehicle)
			)

		license_expiry_date = frappe.db.get_value("Fleet Driver", self.driver, "license_expiry_date")
		if license_expiry_date and getdate(license_expiry_date) < getdate(nowdate()):
			frappe.throw(_("Driver {0}'s license expired on {1}.").format(self.driver, license_expiry_date))

		vehicle_odometer = frappe.db.get_value("Fleet Vehicle", self.vehicle, "current_odometer") or 0
		if self.start_odometer and self.start_odometer < vehicle_odometer:
			frappe.throw(
				_("Start Odometer ({0}) cannot be less than the Vehicle's current odometer ({1}).").format(
					self.start_odometer, vehicle_odometer
				)
			)

	def validate_datetimes(self):
		if self.start_datetime and self.end_datetime:
			if get_datetime(self.end_datetime) <= get_datetime(self.start_datetime):
				frappe.throw(_("End Datetime must be after Start Datetime."))
		if self.end_odometer and self.end_odometer < self.start_odometer:
			frappe.throw(_("End Odometer cannot be less than Start Odometer."))

	def calculate_distance(self):
		if self.start_odometer and self.end_odometer:
			self.distance = self.end_odometer - self.start_odometer

	def update_vehicle_status_for_draft_states(self):
		if self.status == "In Progress":
			frappe.db.set_value("Fleet Vehicle", self.vehicle, "current_status", "On Trip")

	def on_submit(self):
		if self.status != "Completed":
			frappe.throw(_("Only trips with status Completed can be submitted."))

		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if self.end_odometer and self.end_odometer > (vehicle.current_odometer or 0):
			vehicle.db_set("current_odometer", self.end_odometer)

		fallback_status = "Assigned" if vehicle.current_driver else "Available"
		vehicle.db_set("current_status", fallback_status)

	def on_cancel(self):
		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if vehicle.current_status == "On Trip":
			fallback_status = "Assigned" if vehicle.current_driver else "Available"
			vehicle.db_set("current_status", fallback_status)
