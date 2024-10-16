import frappe

@frappe.whitelist()
def get_mcu_items():
  result = frappe.db.sql("""WITH RECURSIVE ItemGroupCTE AS (
    SELECT name, parent_item_group, is_group, custom_bundle_position
    FROM `tabItem Group`
    WHERE parent_item_group = 'Examination'
    UNION ALL
    SELECT ig.name, ig.parent_item_group, ig.is_group, ig.custom_bundle_position
    FROM `tabItem Group` ig
    INNER JOIN ItemGroupCTE cte ON ig.parent_item_group = cte.name)
    SELECT *
    FROM ItemGroupCTE
    WHERE is_group = 0
    ORDER BY custom_bundle_position""", as_dict=True)
  return [item['name'] for item in result]