import frappe
from frappe import _
from frappe.model.document import Document


class FuelLog(Document):
	def validate(self):
		self.calculate_total_amount()
		self.validate_odometer()

	def calculate_total_amount(self):
		self.total_amount = (self.quantity or 0) * (self.rate or 0)

	def validate_odometer(self):
		vehicle_odometer = frappe.db.get_value("Fleet Vehicle", self.vehicle, "current_odometer") or 0
		if self.odometer_reading and self.odometer_reading < vehicle_odometer:
			frappe.throw(
				_("Odometer Reading ({0}) cannot be less than the Vehicle's current odometer ({1}).").format(
					self.odometer_reading, vehicle_odometer
				)
			)

	def on_submit(self):
		vehicle = frappe.get_doc("Fleet Vehicle", self.vehicle)
		if self.odometer_reading and self.odometer_reading > (vehicle.current_odometer or 0):
			vehicle.db_set("current_odometer", self.odometer_reading)
