import frappe
from frappe import _
from frappe.model.document import Document


class VehicleExpense(Document):
	def validate(self):
		if self.amount is not None and self.amount <= 0:
			frappe.throw(_("Amount must be greater than zero."))
