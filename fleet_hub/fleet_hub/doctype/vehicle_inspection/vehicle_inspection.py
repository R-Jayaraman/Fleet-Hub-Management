from frappe.model.document import Document


class VehicleInspection(Document):
	def validate(self):
		self.suggest_overall_status()

	def suggest_overall_status(self):
		if self.overall_status or not self.checklist_items:
			return
		conditions = {row.condition for row in self.checklist_items}
		if "Poor" in conditions:
			self.overall_status = "Fail"
		elif "Fair" in conditions:
			self.overall_status = "Needs Attention"
		else:
			self.overall_status = "Pass"
