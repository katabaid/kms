import frappe

def execute():
    """
    Increase the content column length in tabDoctor Result Other Exam 
    from varchar(140) to varchar(2000).
    """
    # Check if the DocType exists
    if frappe.db.exists('DocType', 'Doctor Result Other Exam'):
        # Alter the column directly in the database
        frappe.db.sql("""
            ALTER TABLE `tabDoctor Result Other Exam` 
            MODIFY COLUMN `content` VARCHAR(2000)
        """)
        
        frappe.db.commit()
