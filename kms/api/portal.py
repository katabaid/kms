import frappe

@frappe.whitelist(allow_guest=True)
def get_branches_with_appointment_types():
  from collections import defaultdict
  data = frappe.db.sql("""
    SELECT tb.name, tbat.appointment_type, NVL2(tqt.name, 1, 0) xs
    FROM `tabBranch` tb
    LEFT JOIN `tabBranch Appointment Type` tbat ON tbat.parent = tb.name
    LEFT JOIN `tabQuestionnaire Template` tqt ON tqt.appointment_type = tbat.appointment_type
    ORDER BY tb.custom_abbr, appointment_type
  """, as_dict=True)
  result = defaultdict(list)
  for row in data:
    if row.appointment_type:
      result[row.name].append({row.appointment_type:row.xs})
    else:
      result[row.name] = result[row.name]
  return [{"name": name, "appointment_types": appts} for name, appts in result.items()]
