import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time


class Route(Document):
	def validate(self):
		self.validate_stop_sequence()

	def validate_stop_sequence(self):
		if not self.stops:
			return

		reference_time = get_time(self.departure_time) if self.departure_time else None
		previous_stop = None

		for stop in self.stops:
			stop_time = get_time(stop.scheduled_time)

			if reference_time and stop_time < reference_time:
				frappe.throw(
					_("Stop {0} ({1}) cannot be scheduled before the route's Departure Time ({2}).").format(
						stop.idx, stop.location_name, self.departure_time
					)
				)

			if previous_stop and stop_time < get_time(previous_stop.scheduled_time):
				frappe.throw(
					_("Stop {0} ({1}) is scheduled earlier than the previous stop, {2} ({3}).").format(
						stop.idx, stop.location_name, previous_stop.idx, previous_stop.location_name
					)
				)

			previous_stop = stop
