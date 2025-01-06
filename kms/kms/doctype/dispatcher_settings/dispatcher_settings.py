# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class DispatcherSettings(Document):
	def validate(self):
		if frappe.db.exists(self.doctype,{
			'branch': self.branch,
			'enable_date': self.enable_date,
		}):
			frappe.throw(_("The combination of Branch and Enable Date must be unique."))

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_dispatchers_for_branch(doctype, txt, searchfield, start, page_len, filters):
	branch = filters.get('branch')
	if not branch:
			return []
			
	# Get users with HC Dispatcher role who either have this branch
	# or don't have any branch permissions
	return frappe.db.sql("""
		SELECT DISTINCT u.name, u.full_name 
		FROM `tabUser` u
		INNER JOIN `tabHas Role` hr ON hr.parent = u.name
		LEFT JOIN `tabUser Permission` up ON up.user = u.name
		WHERE hr.role = 'HC Dispatcher'
		AND hr.parenttype = 'User'
		AND u.enabled = 1
		AND (
			u.name IN (
				SELECT user
				FROM `tabUser Permission`
				WHERE allow = 'Branch' 
				AND for_value = %(branch)s
			)
			OR u.name NOT IN (
				SELECT user
				FROM `tabUser Permission`
				WHERE allow = 'Branch'
			)
		)
		AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name
		LIMIT %(start)s, %(page_len)s""", {
		'branch': branch,
		'txt': "%%%s%%" % txt,
		'start': start,
		'page_len': page_len
	})