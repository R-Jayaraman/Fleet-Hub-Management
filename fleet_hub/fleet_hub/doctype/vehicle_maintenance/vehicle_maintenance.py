import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class VehicleMaintenance(Document):
	def validate(self):
		self.calculate_total_cost()
		self.validate_next_service()
		self.update_vehicle_status_for_draft_states()

	def calculate_total_cost(self):
		self.total_cost = (self.parts_cost or 0) + (self.labor_cost or 0) + (self.other_cost or 0)

	def validate_next_service(self):
		if (
			self.next_service_date
			and self.service_date
			and getdate(self.next_service_date) <= getdate(self.service_date)
		):
			frappe.throw(_("Next Service Date must be after the Service Date."))
		if (
			self.next_service_odometer
			and self.odometer_reading
			and self.next_service_odometer <= self.odometer_reading
		):
			frappe.throw(_("Next Service Odometer must be greater than the current Odometer Reading."))

	def update_vehicle_status_for_draft_states(self):
		if self.status == "In Progress":
			frappe.db.set_value("Fleet Vehicle", self.vehicle, "current_status", "Under Maintenance")

	def on_submit(self):
		if self.status != "Completed":
			frappe.throw(_("Only maintenance records with status Completed can be submitted."))

		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if vehicle.current_status == "Under Maintenance":
			fallback_status = "Assigned" if vehicle.current_driver else "Available"
			vehicle.db_set("current_status", fallback_status)

		if self.service_schedule:
			schedule = frappe.get_doc("Service Schedule", self.service_schedule)
			schedule.db_set("last_service_date", self.service_date)
			schedule.db_set("last_service_odometer", self.odometer_reading)
			schedule.recalculate_next_due()
			schedule.save(ignore_permissions=True)

	def on_cancel(self):
		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if vehicle.current_status == "Under Maintenance":
			fallback_status = "Assigned" if vehicle.current_driver else "Available"
			vehicle.db_set("current_status", fallback_status)
