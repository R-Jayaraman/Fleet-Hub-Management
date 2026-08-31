import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class VehicleDocument(Document):
	def validate(self):
		self.validate_dates()
		self.compute_status()
		self.sync_vehicle_cache()

	def validate_dates(self):
		if self.issue_date and self.expiry_date and getdate(self.expiry_date) <= getdate(self.issue_date):
			frappe.throw(_("Expiry Date must be after Issue Date."))

	def compute_status(self):
		if not self.expiry_date:
			return

		alert_days = frappe.db.get_single_value("Fleet Settings", "document_expiry_alert_days") or 30
		today = getdate(nowdate())
		expiry = getdate(self.expiry_date)

		if expiry < today:
			self.status = "Expired"
		elif expiry <= add_days(today, alert_days):
			self.status = "Expiring Soon"
		else:
			self.status = "Valid"

	def sync_vehicle_cache(self):
		if not self.vehicle:
			return
		if self.document_type == "Insurance":
			frappe.db.set_value("Fleet Vehicle", self.vehicle, "insurance_expiry", self.expiry_date)
		elif self.document_type == "RC":
			frappe.db.set_value("Fleet Vehicle", self.vehicle, "rc_expiry", self.expiry_date)
