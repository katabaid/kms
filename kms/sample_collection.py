import frappe# , json
#from frappe.utils import today

@frappe.whitelist()
def get_items():
  item_group = frappe.db.sql(f"""
    WITH RECURSIVE ItemHierarchy AS (
    SELECT name, parent_item_group, is_group
    FROM `tabItem Group` tig 
    WHERE parent_item_group = 'Laboratory'
    UNION ALL
    SELECT t.name, t.parent_item_group, t.is_group
    FROM `tabItem Group` t
    INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
    )
    SELECT name, parent_item_group, is_group
    FROM ItemHierarchy""", as_dict=True)
  item = frappe.db.sql(f"""
    SELECT tltt.name, tltt.item, tltt.lab_test_group FROM `tabLab Test Template` tltt
    WHERE EXISTS (SELECT 1 FROM tabItem ti WHERE tltt.item = ti.name) 
    AND EXISTS (SELECT 1 FROM (WITH RECURSIVE ItemHierarchy AS (
        SELECT name, parent_item_group, is_group
        FROM `tabItem Group` tig 
        WHERE parent_item_group = 'Laboratory'
        UNION ALL
        SELECT t.name, t.parent_item_group, t.is_group
        FROM `tabItem Group` t
        INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
    )  SELECT name, parent_item_group, is_group FROM ItemHierarchy) ih WHERE tltt.lab_test_group = ih.name)""", as_dict=True)
  return {'item_group': item_group, 'item': item}

@frappe.whitelist()
def create_sc(name, appointment):
  appt_doc = frappe.get_doc('Patient Appointment', appointment)

  #how to determine service unit if more than 1 per branch is registered in item group (i.e. : usg male/usg female, sample1/sample2)
  sus = frappe.db.sql(f"""
    SELECT DISTINCT tigsu.service_unit
    FROM `tabItem Group Service Unit` tigsu, `tabLab Prescription` tlp 
    WHERE tlp.parent = '{name}' 
    AND tlp.custom_exam_item = tigsu.parent
    AND branch = '{appt_doc.custom_branch}'""", as_dict=True)
  
  resp = []
  
  for su in sus:
    sample_doc = frappe.get_doc({
      'doctype': 'Sample Collection',
      'custom_appointment': appt_doc.name,
      'patient': appt_doc.patient,
      'patient_name': appt_doc.patient_name,
      'patient_age': appt_doc.patient_age,
      'patient_sex': appt_doc.patient_sex,
      'company': appt_doc.company,
      'custom_branch': appt_doc.custom_branch,
      'custom_service_unit': su.service_unit,
      'custom_status': 'Started',
      'custom_document_date': frappe.utils.now(),
      'custom_encounter': name
    })
    samples = frappe.db.sql(f"""
    SELECT distinct tltt.sample
    FROM `tabItem Group Service Unit` tigsu, `tabLab Prescription` tlp, `tabLab Test Template` tltt 
    WHERE tlp.parent = '{name}' 
    AND tlp.custom_exam_item = tigsu.parent
    AND branch = '{appt_doc.custom_branch}'
    and tigsu.service_unit = '{su.service_unit}'
    AND tltt.name = tlp.lab_test_name
    AND tltt.sample IS NOT NULL""", as_dict=True)
    for sample in samples:
      sample_doc.append('custom_sample_table', {
        'sample': sample.sample,
      })
    enc_doc = frappe.get_doc('Patient Encounter', name)
    for lab in enc_doc.lab_test_prescription:
      entries = dict()
      entries['template'] = lab.lab_test_code
      entries['item_code'] = lab.custom_exam_item
      sample_doc.append('custom_examination_item', entries)
    sample_doc.insert(ignore_permissions=True)
    lab_test_prescription = enc_doc.get('lab_test_prescription', [])
    lt = [item for item in lab_test_prescription
      if item.get('custom_sample_collection') is None
    ]
    for item in lt:
      item.set('custom_sample_collection', sample_doc.name)
    enc_doc.save(ignore_permissions=True)
  return resp