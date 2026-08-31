import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class FleetDriver(Document):
	def validate(self):
		if self.license_expiry_date and getdate(self.license_expiry_date) < getdate(nowdate()):
			frappe.msgprint(
				f"License for driver {self.driver_name} expired on {self.license_expiry_date}.",
				indicator="orange",
				alert=True,
			)
