import frappe

def execute():
    """
    Add custom_is_locked field to Patient Appointment doctype.
    This field is used to prevent race conditions when multiple users
    try to assign the same patient to different rooms simultaneously.
    """
    # Check if the field already exists
    if frappe.db.exists('Custom Field', {'dt': 'Patient Appointment', 'fieldname': 'custom_is_locked'}):
        return
    
    # Create the custom field
    frappe.get_doc({
        'doctype': 'Custom Field',
        'dt': 'Patient Appointment',
        'fieldname': 'custom_is_locked',
        'fieldtype': 'Check',
        'label': 'Is Locked',
        'insert_after': 'custom_procedures',
        'hidden': 1,  # Hide from UI as it's only used internally
        'read_only': 1,
        'module': 'KMS',
        'description': 'Internal field to prevent concurrent room assignments. Managed by system.'
    }).insert()
    
    frappe.db.commit()
