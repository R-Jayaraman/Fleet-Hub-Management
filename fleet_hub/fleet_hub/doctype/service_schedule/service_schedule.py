import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate


class ServiceSchedule(Document):
	def validate(self):
		if not self.interval_km and not self.interval_days:
			frappe.throw(_("Set at least one of Interval (km) or Interval (days)."))
		self.recalculate_next_due()

	def recalculate_next_due(self):
		if self.last_service_date and self.interval_days:
			self.next_due_date = add_days(getdate(self.last_service_date), self.interval_days)
		if self.last_service_odometer and self.interval_km:
			self.next_due_odometer = (self.last_service_odometer or 0) + self.interval_km
