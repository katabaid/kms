# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WeekNumber(Document):

	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		sql = get_week_number_info(self.name)

		data = frappe._dict({
			"name": self.name,
			"start_date_of_week": sql[0].start_date_of_week,
			"end_date_of_week": sql[0].end_date_of_week,
			"is_current_week": sql[0].is_current_week
		})
		
		super(Document, self).__init__(data)

	def db_update(self, *args, **kwargs):
		pass

	@staticmethod
	def get_list(args):
		data =  frappe.db.sql("""SELECT 
    CONCAT(YEAR(dt), LPAD(WEEK(dt, 1), 2, '0')) AS name,
    MIN(DATE(dt - INTERVAL DAYOFWEEK(dt - INTERVAL 1 DAY) - 1 DAY)) AS start_date_of_week,
    MAX(DATE(dt + INTERVAL 7 - DAYOFWEEK(dt - INTERVAL 1 DAY) DAY)) AS end_date_of_week,
    IF(WEEK(dt, 1) = WEEK(CURDATE(), 1) AND YEAR(dt) = YEAR(CURDATE()), 1, 0) AS is_current_week
FROM 
    (SELECT ADDDATE(DATE(CONCAT(YEAR(CURDATE()) - 1, '-12-01')), t4.i*10000 + t3.i*1000 + t2.i*100 + t1.i*10 + t0.i) dt 
     FROM 
        (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t0,
        (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t1,
        (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t2,
        (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t3,
        (SELECT 0 i UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t4
    ) v
WHERE 
    dt < DATE(CONCAT(YEAR(CURDATE()) + 1, '-02-01'))
GROUP BY 
    YEAR(dt), WEEK(dt, 1)
ORDER BY 
    dt;""", as_dict=True)
		if args.get("as_list"):
			return [(d.get("name"), d.get("start_date_of_week"), d.get("end_date_of_week"), d.get("is_current_week")) for d in data]
		return data

	@staticmethod
	def get_count(args):
		pass

	@staticmethod
	def get_stats(args):
		pass

@frappe.whitelist()
def get_week_number_info(week_number):
	return frappe.db.sql(f"""SELECT 
    DATE_SUB(STR_TO_DATE(CONCAT(SUBSTRING('{week_number}', 1, 4), ' ', SUBSTRING('{week_number}', 5, 2), ' Monday'), '%X %V %W'), INTERVAL 7 DAY) AS start_date_of_week,
    STR_TO_DATE(CONCAT(SUBSTRING('{week_number}', 1, 4), ' ', SUBSTRING('{week_number}', 5, 2), ' Sunday'), '%X %V %W') AS end_date_of_week,
    IF('{week_number}' = CONCAT(YEAR(CURDATE()), LPAD(WEEK(CURDATE(), 1), 2, '0')), 1, 0) AS is_current_week""", as_dict=True)

@frappe.whitelist()
def get_current_week_number():
	return frappe.db.sql("""SELECT 
    CONCAT(YEAR(CURDATE()), LPAD(WEEK(CURDATE(), 1), 2, '0')) AS current_week_number,
    DATE_SUB(STR_TO_DATE(CONCAT(YEAR(CURDATE()), ' ', WEEK(CURDATE(), 1), ' Monday'), '%X %V %W'), INTERVAL 7 DAY) AS start_date_of_week,
    STR_TO_DATE(CONCAT(YEAR(CURDATE()), ' ', WEEK(CURDATE(), 1), ' Sunday'), '%X %V %W') AS end_date_of_week;""", as_dict=True)