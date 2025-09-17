# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from kms.kms.doctype.doctor_result.doctor_result import _create_result_pdf_report

class NurseResult(Document):
	def before_submit (self):
		self.status = 'Finished'
		for non_selective_result in self.non_selective_result:
			if not non_selective_result.result_value:
				frappe.throw (f"""Result Value {non_selective_result.test_name} is mandatory before submitting the document.""")
		for examination_item in self.examination_item:
			if examination_item.status == 'Started':
				examination_item.status = 'Finished'

	def on_submit(self):
		self._validate_conclusion()
		self._update_linked_records()
		_create_result_pdf_report('Nurse Result', self.name)

	def before_update_after_submit(self):
		if self.need_review:
			self._validate_conclusion()
			self._update_linked_records()
		else:
			frappe.throw('Need Review flag must be active.')
		existing_file = frappe.db.exists('File', {
			'file_name': ["like", f"{self.name}%.pdf"],
			'attached_to_doctype': self.doctype,
			'attached_to_name': self.name
		})
		if existing_file:
			frappe.delete_doc('File', existing_file)
			_create_result_pdf_report('Nurse Result', self.name)
	
	def on_update(self):
		result_queue_exists = frappe.db.exists('Result Queue', {'doc_name': self.name, 'doc_type': 'Nurse Result'})
		workflow_state_changed = self.has_value_changed('workflow_state')
		if result_queue_exists and workflow_state_changed:
			frappe.db.set_value('Result Queue', {'doc_name': self.name, 'doc_type': 'Nurse Result'}, {
				'status': self.workflow_state or 'Finished',
			})

	def _update_linked_records(self):
		doctor_result_name = frappe.db.get_value('Doctor Result', {
			'appointment': self.appointment,
			'docstatus': 0
		}, 'name')
		for exam in self.examination_item:
			conclusion_text = [row.conclusion for row in self.conclusion if row.item == exam.item]
			if conclusion_text:
				conclusion_result = ', '.join(conclusion_text)
			item_group = frappe.db.get_value('Item', exam.item, 'item_group')
			self._update_mcu_grade(doctor_result_name, exam, item_group, conclusion_result)

	def _update_mcu_grade(self, doctor_result, exam, item_group, conclusion):
		filters = {
			"hidden_item": exam.item,
			"hidden_item_group": item_group,
			"parent": doctor_result,
			"is_item": 1
		}
		if frappe.db.exists("MCU Exam Grade", filters):
			frappe.db.set_value("MCU Exam Grade", filters, {
				"result": conclusion,
				"status": self.get("workflow_state") or "Finished",
				"document_type": "Nurse Result",
				"document_name": self.name,
			})
	
	def _validate_conclusion(self):
		for exam in self.examination_item:
			conclusion_text = [row.conclusion for row in self.conclusion if row.item == exam.item]
			if not conclusion_text:
				frappe.throw(f'Conclusion for examination item {exam.item} is required before submit.')	

@frappe.whitelist()
def test_print(dt, dn):
	related_files = frappe.get_all('File', filters={
		"attached_to_doctype": dt,
		"attached_to_name": dn,
		"file_type": 'PDF',
		}, pluck='name')
	if related_files:
		for f in related_files:
			frappe.delete_doc('File', f)
	_create_result_pdf_report(dt, dn)