import frappe

def assess_mcu_grade(
	result_text, group, item_code, 
	min_value=None, max_value=None, normal_value=None, test_name=None):
	if not all([result_text, group, item_code]) or not (all([min_value, max_value]) or normal_value):
		return None, None, "Missing required inputs or valid min/max or normal_value"
	grade = None
	if normal_value and str(result_text).strip() == str(normal_value).strip():
		grade = 'A'
	elif min_value and max_value:
		try:
			if float(min_value) <= float(result_text) <= float(max_value):
				grade = 'A'
		except ValueError:
			return None, None, "Invalid numeric input"
	if grade:
		filters = {'item_group': group, 'item_code': item_code, 'grade': grade}
		if test_name:
			filters['test_name'] = test_name
		if grade_data := frappe.db.get_value('MCU Grade', filters, ['name', 'description']):
			return grade_data[0], grade_data[1], None
		return None, None, "No matching grade found"
	return None, None, "Result does not meet grading criteria"