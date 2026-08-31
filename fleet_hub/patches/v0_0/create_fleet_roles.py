import frappe

FLEET_ROLES = [
	"Fleet Administrator",
	"Fleet Manager",
	"Fleet Operator",
	"Maintenance Manager",
	"Accounts User",
	"Driver",
]


def execute():
	for role in FLEET_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)
