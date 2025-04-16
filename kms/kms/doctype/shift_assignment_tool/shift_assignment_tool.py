# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, json
from datetime import timedelta
import datetime

from frappe.model.document import Document

class ShiftAssignmentTool(Document):
	pass

@frappe.whitelist()
def get_employees(
	from_date: str | datetime.date, to_date: str | datetime.date, department: str = None, branch: str = None, company: str = None
) -> dict[str, list]:
	employee_list = frappe.db.sql(f"""
		select name, employee_name 
		from `tabEmployee` 
		where status = 'Active' 
		and date_of_joining<='{to_date}' 
		and company = '{company}' 
		and concat(ifnull(department, ''), ifnull(branch, '')) like '%{department if department else ''}{branch if branch else ''}%'""", 
		as_dict=True)
	assigned = []
	unassigned = []
	for employee in employee_list:
		for date in iterate_dates(datetime.datetime.strptime(from_date, '%Y-%m-%d'), datetime.datetime.strptime(to_date, '%Y-%m-%d')):
			shift_type = frappe.db.get_value('Shift Assignment', {'employee': employee.name, 'start_date': date, 'status': 'Active', 'docstatus': 1, 'company': company}, 'shift_type')
			if shift_type:
				assigned.append(frappe._dict({
					'name': employee.name,
					'employee_name': employee.employee_name,
					'date': date,
					'shift_type': shift_type
				}))
			else:
				unassigned.append(frappe._dict({
					'name': employee.name,
					'employee_name': employee.employee_name
				}))
	unassigned = [dict(t) for t in {tuple(d.items()) for d in unassigned}]
	return {'marked': assigned, 'unmarked': unassigned}

def iterate_dates(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)

@frappe.whitelist()
def assign_employee_shift(employee_list, from_date, to_date, shift):
	if isinstance(employee_list, str):
		employee_list = json.loads(employee_list)
	for employee in employee_list:
		for date in iterate_dates(datetime.datetime.strptime(from_date, '%Y-%m-%d'), datetime.datetime.strptime(to_date, '%Y-%m-%d')):
			if frappe.db.exists('Shift Assignment', {'employee': employee, 'start_date': date, 'status': 'Active', 'docstatus': 1}):
				pass
			else:
				shift_assignment = frappe.get_doc({
					'doctype': 'Shift Assignment',
					'employee': employee,
					'start_date': date,
					'end_date': date,
					'shift_type': shift
				})
				shift_assignment.insert()
				shift_assignment.submit()