import frappe
from frappe.model.document import Document


class FleetVehicle(Document):
	def before_insert(self):
		if not self.current_status:
			self.current_status = "Available"

	def validate(self):
		if self.get_doc_before_save():
			before = self.get_doc_before_save()
			system_managed_fields = ("current_status", "current_driver", "current_odometer")
			user_roles = frappe.get_roles(frappe.session.user)
			privileged = "System Manager" in user_roles or "Fleet Administrator" in user_roles
			if not privileged:
				for fieldname in system_managed_fields:
					self.set(fieldname, before.get(fieldname))
