# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, re
from frappe.model.document import Document
from frappe.utils import today
from frappe import _
from statistics import mean

class Dispatcher(Document):
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

	def validate(self):
		self.progress = self.calculate_progress()
		if self.status == "In Queue":
			self.update_status_if_all_rooms_finished()
		if self.status == "Finished" and self.status_changed_to_finished():
			self.update_patient_appointment()
			self.create_doctor_result()
	
	def before_insert(self):
		if frappe.db.exists(self.doctype,{
			'patient_appointment': self.patient_appointment,
			'date': self.date,
		}):
			frappe.throw(_("Patient already in Dispatcher's queue."))

	def update_status_if_all_rooms_finished(self):
		finished_statuses = {'Refused', 'Finished', 'Rescheduled', 'Partial Finished'}
		if all(room.status in finished_statuses for room in self.assignment_table):
			self.status = 'Waiting to Finish'

	def status_changed_to_finished(self):
		doc_before_save = self.get_doc_before_save()
		return doc_before_save and doc_before_save.status != "Finished"

	def update_patient_appointment(self):
		if self.patient_appointment:
			appointment = frappe.get_doc("Patient Appointment", self.patient_appointment)
			if appointment.status not in {"Closed", "Checked Out"}:
				appointment.db_set('status', 'Checked Out', commit=True)
				frappe.msgprint(_("Patient Appointment {0} has been Checked Out.").format(self.patient_appointment))
		else:
			frappe.msgprint(_("No linked Patient Appointment found."))
	
	def create_doctor_result(self):
		doc = frappe.new_doc('Doctor Result')
		doc.appointment = self.patient_appointment
		doc.patient = self.patient
		doc.age = self.age
		doc.gender = self.gender
		doc.dispatcher = self.name
		doc.created_date = today()
		#Nurse Result
		item_groups = frappe.db.sql(f"""SELECT DISTINCT tig.name, tig.custom_gradable 
			FROM `tabMCU Appointment` tma, tabItem ti, `tabItem Group` tig 
			WHERE tma.parent = '{self.patient_appointment}'
			AND tig.name = ti.item_group 
			AND ti.name = tma.examination_item 
			AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = ti.name)
			ORDER BY tig.custom_bundle_position""", as_dict=True)
		for item_group in item_groups:
			doc.append('nurse_grade', {
				'examination': item_group.name,
				'gradable': item_group.custom_gradable,
				'hidden_item_group': item_group.name,})
			items = frappe.db.sql(f"""SELECT DISTINCT tma.examination_item, tma.item_name, tma.status, ti.custom_gradable
				FROM `tabMCU Appointment` tma, tabItem ti
				WHERE EXISTS (SELECT 1 FROM `tabDispatcher` td 
				WHERE patient_appointment = '{self.patient_appointment}' AND tma.parent = td.name)
				AND tma.examination_item = ti.name
				AND ti.item_group = '{item_group.name}'
				ORDER BY ti.custom_bundle_position""", as_dict = 1)
			previous_exam_item = ''
			for item in items:
				if item.examination_item == 'Vital Sign Blood Pressure':
					grade = ''
					sistolic = frappe.db.get_value(
						'Nurse Examination Result', 
						{},
						'result_value'
					)
				doc.append('nurse_grade', {
					'examination': item.item_name,
					'gradable': item.custom_gradable,
					'hidden_item_group': item_group.name,
					'hidden_item_name': item.examination_item})
				if previous_exam_item != item.examination_item:
					exams = frappe.db.sql(f"""
						SELECT tner.idx AS idx, test_name AS result_line, FORMAT(min_value, 2) AS min_value, 
						FORMAT(max_value, 2) AS max_value, FORMAT(result_value, 2) AS result_text, test_uom AS uom, tne.name AS doc, tnerq.status AS status, 
						CASE WHEN min_value IS NOT NULL AND max_value IS NOT NULL AND (min_value <> 0 OR max_value <> 0) AND result_value IS NOT NULL THEN
						CASE WHEN result_value > max_value THEN CONCAT_WS('|||', 'Increase', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Increase')) 
						WHEN result_value < min_value THEN CONCAT_WS('|||', 'Decrease', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Decrease')) ELSE NULL END ELSE NULL END AS incdec,
						IFNULL((SELECT 1 FROM `tabMCU Grade` tmg WHERE tmg.item_group = '{item_group.name}' AND tmg.item_code = '{item.examination_item}' AND tmg.test_name = tner.test_name LIMIT 1), 0) AS gradable
						FROM `tabNurse Examination Result` tner, `tabNurse Examination` tne, `tabNurse Examination Request` tnerq
						WHERE tne.name = tner.parent AND tne.appointment = '{self.patient_appointment}' AND tne.docstatus = 1 
						AND tner.item_code = '{item.examination_item}' AND tnerq.parent = tne.name 
						AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = tner.item_code AND tnerq.template = tnet.item_name)
						UNION
						SELECT tnesr.idx+100, result_line, NULL, NULL, result_text, result_check, tne.name, tnerq.status, NULL, 0
						FROM `tabNurse Examination Selective Result` tnesr, `tabNurse Examination` tne, `tabNurse Examination Request` tnerq
						WHERE tne.name = tnesr.parent AND tne.appointment = '{self.patient_appointment}' AND tne.docstatus = 1 
						AND tnesr.item_code = '{item.examination_item}' AND tnerq.parent = tne.name 
						AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = tnesr.item_code AND tnerq.template = tnet.item_name)
						UNION
						SELECT tce.idx+200, test_label, NULL, NULL, FORMAT(result, 2), NULL, tne.name, tnerq.status, NULL, 0
						FROM `tabCalculated Exam` tce, `tabNurse Examination` tne, `tabNurse Examination Request` tnerq
						WHERE tne.name = tce.parent AND tne.appointment = '{self.patient_appointment}' AND tne.docstatus = 1 
						AND tce.item_code = '{item.examination_item}' AND tnerq.parent = tne.name 
						AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = tce.item_code AND tnerq.template = tnet.item_name)
						UNION
						SELECT tner.idx+300 AS idx, test_name AS result_line, FORMAT(min_value, 2) AS min_value, 
						FORMAT(max_value, 2) AS max_value, FORMAT(result_value, 2) AS result_text, test_uom AS uom, tnr.name AS doc, tnerq.status AS status, 
						CASE WHEN min_value IS NOT NULL AND max_value IS NOT NULL AND (min_value <> 0 OR max_value <> 0) AND result_value IS NOT NULL THEN
						CASE WHEN result_value > max_value THEN CONCAT_WS('|||', 'Increase', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Increase')) 
						WHEN result_value < min_value THEN CONCAT_WS('|||', 'Decrease', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Decrease')) ELSE NULL END ELSE NULL END AS incdec,
						IFNULL((SELECT 1 FROM `tabMCU Grade` tmg WHERE tmg.item_group = '{item_group.name}' AND tmg.item_code = '{item.examination_item}' AND tmg.test_name = tner.test_name LIMIT 1), 0) AS gradable
						FROM `tabNurse Examination Result` tner, `tabNurse Result` tnr, `tabNurse Examination Request` tnerq
						WHERE tnr.name = tner.parent AND tnr.appointment = '{self.patient_appointment}' AND tnr.docstatus IN (0,1)
						AND tner.item_code = '{item.examination_item}' AND tnerq.parent = tnr.name
						AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = tner.item_code AND tnerq.template = tnet.item_name AND tnet.result_in_exam = 0)
						UNION
						SELECT tnesr.idx+400, result_line, NULL, NULL, result_text, result_check, tnr.name, tnerq.status, NULL, 0
						FROM `tabNurse Examination Selective Result` tnesr, `tabNurse Result` tnr, `tabNurse Examination Request` tnerq
						WHERE tnr.name = tnesr.parent AND tnr.appointment = '{self.patient_appointment}' AND tnr.docstatus IN (0,1)
						AND tnesr.item_code = '{item.examination_item}' AND tnerq.parent = tnr.name 
						AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = tnesr.item_code AND tnerq.template = tnet.item_name AND tnet.result_in_exam = 0)
						ORDER BY 1""", as_dict=1)
					for exam in exams:
						grade = ''
						grade_description = ''
						if exam.incdec:
							incdec = exam.incdec.split('|||')
						else:
							incdec = ['','']
						if exam.gradable == 1 and exam.result_text and exam.min_value and exam.max_value and is_within_range(exam.result_text, exam.min_value, exam.max_value):
							grade = 'A'
							grade_description = frappe.db.get_value(
								'MCU Grade', 
								{'item_group': item_group.name, 'item_code': item.examination_item, 'test_name': exam.result_line, 'grade': 'A'}, 
								'description')
						if exam.result_line == 'BMI':
							bmi_rec = frappe.db.get_all('BMI Classification', fields=['name', 'min_value', 'max_value', 'grade'])
							exam_result_float = convert_to_float(exam.result_text)
							for bmi in bmi_rec:
								min_value_float = convert_to_float(bmi['min_value'])
								max_value_float = convert_to_float(bmi['max_value'])
								if is_within_range(exam_result_float, min_value_float, max_value_float):
									grade = bmi['grade']
									grade_description = bmi['name']
									break
								else:
									grade = ''
									grade_description = ''
						doc.append('nurse_grade', {
						'examination': exam.result_line,
						'gradable': exam.gradable,
						'result': exam.result_text,
						'min_value': exam.min_value,
						'max_value': exam.max_value,
						'grade': grade if grade else None,
						'description': grade_description if grade_description else None,
						'uom': exam.uom,
						'status': exam.status,
						'document': exam.doc,
						'incdec': incdec[0],
						'incdec_category': incdec[1] if len(incdec)>1 else '',
						'hidden_item_group': item_group.name,
						'hidden_item': item.examination_item})
				previous_exam_item = item.examination_item
		#Doctor Result
		doc_item_groups = frappe.db.sql(f"""SELECT DISTINCT tig.name, tig.custom_gradable 
			FROM `tabMCU Appointment` tma, tabItem ti, `tabItem Group` tig 
			WHERE tma.parent = '{self.patient_appointment}'
			AND tig.name = ti.item_group 
			AND ti.name = tma.examination_item 
			AND EXISTS (SELECT 1 FROM `tabDoctor Examination Template` tdet WHERE tdet.item_code = ti.name)
			ORDER BY tig.custom_bundle_position""", as_dict=True)
		for item_group in doc_item_groups:
			doc.append('doctor_grade', {
				'examination': item_group.name,
				'gradable': item_group.custom_gradable,
				'hidden_item_group': item_group.name,})
			items = frappe.db.sql(f"""SELECT DISTINCT tma.examination_item, tma.item_name, tma.status, ti.custom_gradable
				FROM `tabMCU Appointment` tma, tabItem ti
				WHERE EXISTS (SELECT 1 FROM `tabDispatcher` td 
				WHERE patient_appointment = '{self.patient_appointment}' AND tma.parent = td.name)
				AND tma.examination_item = ti.name
				AND ti.item_group = '{item_group.name}'
				ORDER BY ti.custom_bundle_position""", as_dict = 1)
			previous_exam_item = ''
			for item in items:
				doc.append('doctor_grade', {
					'examination': item.item_name,
					'gradable': item.custom_gradable,
					'hidden_item_group': item_group.name,
					'hidden_item': item.examination_item,})
				if previous_exam_item != item.examination_item:
					exams = frappe.db.sql(f"""
						SELECT idx, result_line, NULL AS min_value, NULL AS max_value, result_text, result_check AS uom, parent AS doc, NULL as incdec, 0 AS gradable FROM `tabDoctor Examination Selective Result` tdesr
						WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.name = tdesr.parent AND tde.appointment = '{self.patient_appointment}' AND docstatus = 1)
						AND item_name = '{item.item_name}'
						UNION
						SELECT idx, test_name, min_value, max_value, result_value, test_uom, parent, 
						CASE WHEN min_value IS NOT NULL AND max_value IS NOT NULL AND (min_value <> 0 OR max_value <> 0) AND result_value IS NOT NULL THEN
						CASE WHEN result_value > max_value THEN CONCAT_WS('|||', 'Increase', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Increase')) 
						WHEN result_value < min_value THEN CONCAT_WS('|||', 'Decrease', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = test_name AND tmc.selection = 'Decrease')) ELSE NULL END ELSE NULL END AS incdec,
						IFNULL((SELECT 1 FROM `tabMCU Grade` tmg WHERE tmg.item_group = '{item_group.name}' AND tmg.item_code = '{item.examination_item}' AND test_name = test_name LIMIT 1), 0) AS gradable
						FROM `tabDoctor Examination Result` tder 
						WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.name = tder.parent AND tde.appointment = '{self.patient_appointment}' AND docstatus = 1)
						AND item_code = '{item.examination_item}'
						UNION
						SELECT idx, 'Eyes', NULL, NULL,
						CONCAT_WS(', ', 
							CASE WHEN LENGTH(tde.eyes_left_others)>0 THEN CONCAT('Left: ', tde.eyes_left_others) END, 
							CASE WHEN LENGTH(tde.eyes_right_others)>0 THEN CONCAT('Right: ', tde.eyes_right_others) END),
						IF(tde.eyes_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.left_anemic>0 THEN 'Left Anemic' END, 
								CASE WHEN tde.left_icteric>0 THEN 'Left Icteric' END, 
								CASE WHEN tde.right_anemic>0 THEN 'Right Anemic' END, 
								CASE WHEN tde.right_icteric>0 THEN 'Right Icteric' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Ear', NULL, NULL, 
						CONCAT_WS(', ', 
							CASE WHEN LENGTH(tde.ear_left_others)>0 THEN CONCAT('Left: ', tde.ear_left_others) END, 
							CASE WHEN LENGTH(tde.ear_right_others)>0 THEN CONCAT('Right: ', tde.ear_right_others) END),
						IF(
							tde.ear_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.left_cerumen>0 THEN 'Left Cerumen' END, 
								CASE WHEN tde.left_cerumen_prop>0 THEN 'Left Cerumen Prop' END, 
								CASE WHEN tde.left_tympanic>0 THEN 'Left Tympanic membrane intact' END, 
								CASE WHEN tde.right_cerumen>0 THEN 'Right Cerumen' END, 
								CASE WHEN tde.right_cerumen_prop>0 THEN 'Right Cerumen Prop' END, 
								CASE WHEN tde.right_tympanic>0 THEN 'Right Tympanic membrane intact' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Nose', NULL, NULL,
						CONCAT_WS(', ', 
							CASE WHEN LENGTH(tde.nose_left_others)>0 THEN CONCAT('Left: ', tde.nose_left_others) END, 
							CASE WHEN LENGTH(tde.nose_right_others)>0 THEN CONCAT('Right: ', tde.nose_right_others) END),
						IF(
							tde.nose_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.deviated>0 THEN 'Deviated' END, 
								CASE WHEN tde.left_enlarged>0 THEN 'Left Enlarged' END, 
								CASE WHEN tde.left_hyperemic>0 THEN 'Left Hyperemic' END, 
								CASE WHEN tde.left_polyp>0 THEN 'Left Polyp' END, 
								CASE WHEN tde.right_enlarged>0 THEN 'Right Enlarged' END, 
								CASE WHEN tde.right_hyperemic>0 THEN 'Right Hyperemic' END, 
								CASE WHEN tde.right_polyp>0 THEN 'Right Polyp' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Throat', NULL, NULL, tde.throat_others,
						IF(
							tde.throat_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', CASE WHEN tde.enlarged_tonsil>0 THEN 'Enlarged Tonsil' END, CASE WHEN tde.hyperemic_pharynx>0 THEN 'Hyperemic Pharynx' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Neck', NULL, NULL, tde.neck_others,
						IF(
							tde.neck_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', CASE WHEN tde.enlarged_thyroid>0 THEN 'Enlarged Thyroid' END, CASE WHEN tde.enlarged_lymph_node>0 THEN 'Enlarged Lymph Node' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Cardiac', NULL, NULL, tde.OTHERS,
						IF(
							tde.cardiac_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
							CASE WHEN tde.regular_heart_sound>0 THEN 'Regular Heart Sound' END, 
							CASE WHEN tde.murmur>0 THEN 'Murmur' END, 
							CASE WHEN tde.gallop>0 THEN 'Gallop' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Breast', NULL, NULL,
						CONCAT_WS(', ', 
							CASE WHEN LENGTH(tde.breast_left_others)>0 THEN CONCAT('Left: ', tde.breast_left_others) END, 
							CASE WHEN LENGTH(tde.breast_right_others)>0 THEN CONCAT('Right: ', tde.breast_right_others) END),
						IF(
							tde.breast_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.left_enlarged_breast>0 THEN 'Enlarged Left Breast Glands' END, 
								CASE WHEN tde.left_lumps>0 THEN 'Left Lumps' END, 
								CASE WHEN tde.right_enlarged_breast>0 THEN 'Enlarged Right Breast Glands' END, 
								CASE WHEN tde.right_lumps>0 THEN 'Right Lumps' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Respiratory System', NULL, NULL,
						CONCAT_WS(', ', 
							CASE WHEN LENGTH(tde.resp_left_others)>0 THEN CONCAT('Left: ', tde.resp_left_others) END, 
							CASE WHEN LENGTH(tde.resp_right_others)>0 THEN CONCAT('Right: ', tde.resp_right_others) END),
						IF(
							tde.resp_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.left_ronkhi>0 THEN 'Left Ronkhi' END, 
								CASE WHEN tde.left_wheezing>0 THEN 'Left Wheezing' END, 
								CASE WHEN tde.right_ronkhi>0 THEN 'Enlarged Ronkhi' END, 
								CASE WHEN tde.right_wheezing>0 THEN 'Right Wheezing' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Abdomen', NULL, NULL, tde.abd_others,
						IF(
							tde.abd_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.tenderness>0 THEN 'Tenderness' END, 
								CASE WHEN tde.hepatomegaly>0 THEN 'Hepatomegaly' END, 
								CASE WHEN tde.splenomegaly>0 THEN 'Splenomegaly' END, 
								CASE WHEN tde.increased_bowel_sounds>0 THEN 'Increased Bowel Sounds' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Spine', NULL, NULL, tde.spine_details,
						IF(tde.spine_check>0, 'No Abnormality', ''), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Genitourinary', NULL, NULL, tde.genit_others,
						IF(
							tde.genit_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.hernia>0 THEN 'Hernia' END, 
								CASE WHEN tde.hemorrhoid>0 THEN 'Hemorrhoid' END, 
								CASE WHEN tde.inguinal_nodes>0 THEN 'Inguinal Nodes' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Neurological System', NULL, NULL, tde.neuro_others,
						IF(
							tde.neuro_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.motoric_system_abnormality>0 THEN 'Motoric System Abnormality' END, 
								CASE WHEN tde.reflexes_abnormality>0 THEN 'Reflexes Abnormality' END, 
								CASE WHEN tde.sensory_system_abnormality>0 THEN 'Sensory System Abnormality' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Skin', NULL, NULL, tde.skin_others,
						IF(
							tde.skin_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', 
								CASE WHEN tde.skin_psoriasis>0 THEN 'Psoriasis' END, 
								CASE WHEN tde.skin_tattoo>0 THEN 'Tattoo' END, 
								CASE WHEN tde.skin_tag>0 THEN 'Skin Tag' END)
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Visual Field Test', NULL, NULL, tde.visual_details, IF(tde.visual_check>0, 'Same As Examiner', ''), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'visual_field_test_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Romberg Test', NULL, NULL, tde.romberg_others, 
						IF(tde.romberg_check>0, 'No Abnormality', tde.romberg_abnormal), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'romberg_test_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Tinnel Test', NULL, NULL, tde.tinnel_details,
						IF(tde.tinnel_check>0, 'No Abnormality', ''), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'tinnel_test_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Phallen Test', NULL, NULL, tde.phallen_details,
						IF(tde.phallen_check>0, 'No Abnormality', ''), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'phallen_test_name' AND ts.value = tder.template))
						UNION
						SELECT idx, 'Rectal Examination', NULL, NULL, tde.rectal_others,
						IF(
							tde.rectal_check>0, 
							'No Abnormality', 
							CONCAT_WS(', ', IF(tde.enlarged_prostate>0, 'Enlarged Prostate', ''), CONCAT('Hemorrhoid: ', tde.rectal_hemorrhoid))
						), name, NULL, 0
						FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND EXISTS 
						(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'rectal_test_name' AND ts.value = tder.template))
						UNION
						SELECT idx, result_line, min_value, max_value, result_text, uom, doc, incdec, gradable FROM (
						SELECT 1, idx, 'Intra Oral' AS result_line, NULL AS min_value, NULL AS max_value, GROUP_CONCAT(intra_oral) AS result_text, NULL AS uom, name AS doc, NULL AS incdec, 0 AS gradable
						FROM `tabIntra Oral` tio WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND tio.parent = tde.name 
						AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
						HAVING GROUP_CONCAT(intra_oral) IS NOT NULL
						UNION
						SELECT 2, idx, 'Extra Oral', NULL, NULL, GROUP_CONCAT(extra_oral), NULL, name, NULL, 0
						FROM `tabExtra Oral` teo WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND teo.parent = tde.name 
						AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
						HAVING GROUP_CONCAT(extra_oral) IS NOT NULL
						UNION
						SELECT 4, idx+100, other, NULL, NULL, selective_value, value, name, NULL, 0
						FROM `tabOther Dental` tod WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND tod.parent = tde.name 
						AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
						UNION
						SELECT 3, idx+10, CONCAT_WS(': ', teeth_type, location), NULL, NULL, options, `position`, name, NULL, 0
						FROM `tabDental Detail` tdd WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{self.patient_appointment}' AND docstatus = 1 AND tdd.parent = tde.name 
						AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{item.item_name}' AND EXISTS 
						(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template))) ORDER BY 1, 2) AS t		
						ORDER BY 1""", as_dict=1)
					for exam in exams:
						grade = ''
						grade_description = ''
						if exam.incdec:
							incdec = exam.incdec.split('|||')
						else:
							incdec = ['','']
						if exam.gradable == 1 and exam.result_text and exam.min_value and exam.max_value and exam.result_text >= exam.min_value and exam.result_text <= exam.max_value :
							grade = 'A'
							grade_description = frappe.db.get_value(
								'MCU Grade', 
								{'item_group': item_group.name, 'item_code': item.examination_item, 'test_name': exam.result_line, 'grade': 'A'}, 
								'description')
						doc.append('doctor_grade', {
						'examination': exam.result_line,
						'gradable': exam.gradable,
						'result': exam.result_text,
						'min_value': exam.min_value,
						'max_value': exam.max_value,
						'grade': grade if grade else None,
						'description': grade_description if grade_description else None,
						'uom': exam.uom,
						'status': item.status,
						'document': exam.doc,
						'incdec': incdec[0],
						'incdec_category': incdec[1] if len(incdec)>1 else '',
						'hidden_item_group': item_group.name,
						'hidden_item': item.examination_item})
				previous_exam_item = item.examination_item
		#Radiology Result
		item_groups = frappe.db.sql(f"""SELECT DISTINCT tig.name, tig.custom_gradable 
			FROM `tabMCU Appointment` tma, tabItem ti, `tabItem Group` tig 
			WHERE tma.parent = '{self.patient_appointment}'
			AND tig.name = ti.item_group 
			AND ti.name = tma.examination_item 
			AND EXISTS (SELECT 1 FROM `tabRadiology Result Template` trrt WHERE trrt.item_code = ti.name)
			ORDER BY tig.custom_bundle_position""", as_dict=True)
		for item_group in item_groups:
			doc.append('radiology_grade', {
				'examination': item_group.name,
				'gradable': item_group.custom_gradable,
				'hidden_item_group': item_group.name,})
			items = frappe.db.sql(f"""SELECT DISTINCT tma.examination_item, tma.item_name, tma.status, ti.custom_gradable
				FROM `tabMCU Appointment` tma, tabItem ti
				WHERE EXISTS (SELECT 1 FROM `tabDispatcher` td 
				WHERE patient_appointment = '{self.patient_appointment}' AND tma.parent = td.name)
				AND tma.examination_item = ti.name
				AND ti.item_group = '{item_group.name}'
				ORDER BY ti.custom_bundle_position""", as_dict = 1)
			previous_exam_item = ''
			for item in items:
				doc.append('radiology_grade', {
					'examination': item.item_name,
					'gradable': item.custom_gradable,
					'hidden_item_group': item_group.name,
					'hidden_item': item.examination_item,})
				if previous_exam_item != item.examination_item:
					exams = frappe.db.sql(f"""
						SELECT trr.idx, result_line, NULL AS min_value, NULL as max_value, result_text, IF(trr.docstatus=1, result_check, NULL) AS uom, 
						trr.parent AS doc, trr2.workflow_state AS status, NULL AS incdec
						FROM `tabRadiology Results` trr,  `tabRadiology Result` trr2 
						WHERE trr.parent = trr2.name AND trr2.appointment = '{self.patient_appointment}' AND trr2.docstatus IN (0, 1)
						AND item_code = '{item.examination_item}' ORDER BY idx""", as_dict=1)
					for exam in exams:
						doc.append('radiology_grade', {
						'examination': exam.result_line,
						'gradable': 0,
						'result': exam.result_text,
						'min_value': exam.min_value,
						'max_value': exam.max_value,
						'uom': exam.uom,
						'status': exam.status,
						'document': exam.doc,
						'incdec': exam.incdec,
						'hidden_item_group': item_group.name,
						'hidden_item': item.examination_item})
				previous_exam_item = item.examination_item
		#Lab Result
		item_groups = frappe.db.sql(f"""SELECT DISTINCT tig.name, tig.custom_gradable 
			FROM `tabMCU Appointment` tma, tabItem ti, `tabItem Group` tig 
			WHERE tma.parent = '{self.patient_appointment}'
			AND tig.name = ti.item_group 
			AND ti.name = tma.examination_item 
			AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.lab_test_code = ti.name)
			ORDER BY tig.custom_bundle_position""", as_dict=True)
		for item_group in item_groups:
			doc.append('lab_test_grade', {
				'examination': item_group.name,
				'gradable': item_group.custom_gradable,
				'hidden_item_group': item_group.name,})
			items = frappe.db.sql(f"""SELECT DISTINCT tma.examination_item, tma.item_name, tma.status, ti.custom_gradable
				FROM `tabMCU Appointment` tma, tabItem ti
				WHERE EXISTS (SELECT 1 FROM `tabDispatcher` td 
				WHERE patient_appointment = '{self.patient_appointment}' AND tma.parent = td.name)
				AND tma.examination_item = ti.name
				AND ti.item_group = '{item_group.name}'
				ORDER BY ti.custom_bundle_position""", as_dict = 1)
			previous_exam_item = ''
			for item in items:
				doc.append('lab_test_grade', {
					'examination': item.item_name,
					'gradable': item.custom_gradable,
					'hidden_item_group': item_group.name,
					'hidden_item': item.examination_item,})
				if previous_exam_item != item.examination_item:
					exams = frappe.db.sql(f"""
						SELECT tntr.idx, lab_test_event AS result_line, custom_min_value AS min_value, custom_max_value AS max_value, result_value AS result_text, 
						lab_test_uom AS uom, tlt.name AS doc, tlt.status AS status,
						CASE WHEN custom_min_value IS NOT NULL AND custom_max_value IS NOT NULL AND (custom_min_value <> 0 OR custom_max_value <> 0) AND result_value IS NOT NULL THEN
						CASE WHEN result_value > custom_max_value THEN CONCAT_WS('|||', 'Increase', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = lab_test_event AND tmc.selection = 'Increase')) 
						WHEN result_value < custom_min_value THEN CONCAT_WS('|||', 'Decrease', (SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group.name}' AND tmc.item = '{item.examination_item}' AND tmc.test_name = lab_test_event AND tmc.selection = 'Decrease')) ELSE NULL END ELSE NULL END AS incdec,
						IFNULL((SELECT 1 FROM `tabMCU Grade` tmg WHERE tmg.item_group = '{item_group.name}' AND tmg.item_code = '{item.examination_item}' AND test_name = lab_test_event LIMIT 1), 0) AS gradable
						FROM `tabNormal Test Result` tntr, `tabLab Test` tlt WHERE tntr.parent = tlt.name AND tlt.custom_appointment = '{self.patient_appointment}' 
						AND tlt.docstatus IN (0, 1) AND tntr.lab_test_name = '{item.item_name}'
						UNION
						SELECT tstt.idx, event, NULL, NULL, result, NULL, tlt.name, tlt.status, NULL, 0
						FROM `tabSelective Test Template` tstt, `tabLab Test` tlt WHERE tstt.parent = tlt.name AND tlt.custom_appointment = '{self.patient_appointment}' 
						AND tlt.docstatus IN (0, 1) AND event = '{item.item_name}' ORDER BY idx""", as_dict=1)
					for exam in exams:
						grade = ''
						grade_description = ''
						if exam.incdec:
							incdec = exam.incdec.split('|||')
						else:
							incdec = ['','']
						if exam.gradable == 1 and exam.result_text and exam.min_value and exam.max_value and exam.result_text >= exam.min_value and exam.result_text <= exam.max_value :
							grade = 'A'
							grade_description = frappe.db.get_value(
								'MCU Grade', 
								{'item_group': item_group.name, 'item_code': item.examination_item, 'test_name': exam.result_line, 'grade': 'A'}, 
								'description')
						doc.append('lab_test_grade', {
						'examination': exam.result_line,
						'gradable': exam.gradable,
						'result': exam.result_text,
						'min_value': exam.min_value,
						'max_value': exam.max_value,
						'grade': grade if grade else None,
						'description': grade_description if grade_description else None,
						'uom': exam.uom,
						'status': exam.status,
						'document': exam.doc,
						'incdec': incdec[0],
						'incdec_category': incdec[1] if len(incdec)>1 else '',
						'hidden_item_group': item_group.name,
						'hidden_item': item.examination_item})
				previous_exam_item = item.examination_item
		doc.insert()

	def calculate_progress(self):
		child_items = frappe.get_all('MCU Appointment', filters={'parent': self.name}, fields=['status'])
		if not child_items:
			return 0
		else:
			return round(mean([100 if item.status == 'Finished' else 0 for item in child_items]))

def convert_to_float(value):
	return float(str(value).replace(",", "."))

def is_within_range(value, min_value, max_value):
	return min_value < value < max_value

@frappe.whitelist()
def get_queued_branch(branch):
	count = frappe.db.sql(f"""
		SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, tra.`user`, thsu.custom_default_doctype
		FROM `tabHealthcare Service Unit` thsu
		LEFT JOIN `tabDispatcher Room` tdr ON thsu.name = tdr.healthcare_service_unit AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
		LEFT JOIN `tabRoom Assignment` tra ON thsu.name = tra.healthcare_service_unit and tra.`date` = CURDATE()
		WHERE thsu.custom_branch = '{branch}' and thsu.is_group = 0 AND thsu.custom_default_doctype IS NOT NULL
		GROUP BY thsu.name""", as_dict=True)
	return count

@frappe.whitelist()
def checkin_room(dispatcher_id, hsu, doctype, docname):
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Room'
	doc.room = hsu
	related_rooms = get_related_rooms (hsu, dispatcher_id)
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Ongoing Examination'
			room.reference_doctype = doctype
			room.reference_doc = docname
		elif room.healthcare_service_unit in related_rooms:
			room.reference_doc = docname
	doc.save(ignore_permissions=True)
	return 'Checked In.'

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu):
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Queue'
	doc.room = ''
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Wait for Room Assignment'
			room.reference_doc = ''
	doc.save(ignore_permissions=True)
	return 'Removed from examination room.'

def get_related_rooms (hsu, dispatcher_id):
	return frappe.db.sql(f"""
		SELECT service_unit FROM `tabItem Group Service Unit` tigsu1
		WHERE tigsu1.parentfield = 'custom_room'
		AND 	tigsu1.parenttype = 'Item'
		AND 	tigsu1.service_unit != '{hsu}'
		AND 	EXISTS (
			SELECT 1 FROM `tabItem Group Service Unit` tigsu 
			WHERE tigsu.parentfield = 'custom_room'
			AND 	tigsu.parenttype = 'Item'
			AND 	tigsu.service_unit = '{hsu}'
			AND 	tigsu.parent = tigsu1.parent
			AND EXISTS (
				SELECT 1 FROM `tabMCU Appointment` tma
				WHERE tma.parent = '{dispatcher_id}'
				AND 	tma.parentfield = 'package'
				AND		tma.parenttype = 'Dispatcher'
				AND 	tma.examination_item = tigsu.parent))""", pluck = 'service_unit')

@frappe.whitelist()
def finish_exam(dispatcher_id, hsu, status, doctype, docname):
	if status == 'Removed':
		status = 'Wait for Room Assignment'
	doc = frappe.get_doc('Dispatcher', dispatcher_id)

	room_count = 0
	final_count = 0
	final_status = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished']
	target = ''

	related_rooms = get_related_rooms (hsu, dispatcher_id)

	exists_to_retest = False
	source_doc = frappe.get_doc(doctype, docname)
	if doctype == 'Sample Collection':
		for sample in source_doc.custom_sample_table:
			if sample.status == 'To Retest':
				exists_to_retest = True
	else:
		for item in source_doc.examination_item:
			if item.status == 'To Retest':
				exists_to_retest = True

	for room in doc.assignment_table:
		room_count += 1
		if room.status in final_status:
			final_count += 1
		if room.healthcare_service_unit == hsu:
			room.status = 'Additional or Retest Request' if exists_to_retest else status
		if room.healthcare_service_unit in related_rooms:
			room.status = 'Additional or Retest Request' if exists_to_retest else status
	doc.status = 'Waiting to Finish' if room_count == final_count else 'In Queue'
	doc.room = ''
	doc.save(ignore_permissions=True)

	if (status == 'Finished' or status == 'Partial Finished') and not exists_to_retest:
		match doctype:
			case 'Radiology':
				target = 'Radiology Result'
			case 'Nurse Examination':
				target = 'Nurse Result'
			case 'Sample Collection':
				target = 'Lab Test'
		if target:
			result_doc_name = create_result_doc(source_doc, target)
			return {'message': 'Finished', 'docname': result_doc_name}
	return {'message': 'Finished'}

@frappe.whitelist()
def update_exam_item_status(dispatcher_id, examination_item, status):
	flag = frappe.db.sql(f"""
		SELECT 1 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND item_name = '{examination_item}' 
		UNION ALL 
		SELECT 2 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name)
		""", as_dict=True)
	if flag[0].result == 1:
		frappe.db.sql(f"""
			UPDATE `tabMCU Appointment` 
			SET `status` = '{status}' 
			WHERE parent = '{dispatcher_id}' 
			AND item_name = '{examination_item}' 
			AND parentfield = 'package' 
			AND parenttype = 'Dispatcher'
			""")
	elif flag[0].result == 2:
		items = frappe.db.sql(f"""
			SELECT name 
			FROM `tabMCU Appointment` tma 
			WHERE `parent` = '{dispatcher_id}' 
			AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name)
			""", as_dict=True)
		for item in items:
			frappe.db.sql(f"""UPDATE `tabMCU Appointment` SET `status` = '{status}' WHERE name = '{item.name}'""")
	else:
		frappe.throw(f"Examination item {examination_item} does not exist.")
	return f"""Updated Dispatcher item: {examination_item} status to {status}."""

def create_result_doc(doc, target):
	not_created = True
	if target == 'Lab Test':
		not_created = False
		normal_toggle = 0
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'custom_branch': doc.custom_branch,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'custom_appointment': doc.custom_appointment,
			'custom_sample_collection': doc.name
		})
		for item in doc.custom_sample_table:
			if item.status == 'Finished':
				lab_test = frappe.db.sql(f"""
					SELECT name
					FROM `tabLab Test Template` tltt
					WHERE tltt.sample = '{item.sample}'
					AND EXISTS (
					SELECT 1 
					FROM `tabMCU Appointment` tma 
					WHERE tltt.name = tma.item_name
					AND tma.parent = '{doc.custom_dispatcher}'
					AND tma.parentfield = 'package'
					AND tma.parenttype = 'Dispatcher')""", pluck='name')
				for exam in lab_test:
					template_doc = frappe.get_doc('Lab Test Template', exam)
					non_selective = template_doc.get('normal_test_templates')
					selective = template_doc.get('custom_selective')
					if non_selective:
						match = re.compile(r'(\d+) Years?').match(doc.patient_age)
						age = int(match.group(1)) if match else None
						minmax = frappe.db.sql(f"""
							WITH cte AS (
								SELECT
									parent, lab_test_event, lab_test_uom, custom_age, custom_sex, custom_min_value, custom_max_value,
									MAX(CASE WHEN custom_age <= {age} THEN custom_age END) OVER (PARTITION BY parent, lab_test_event, custom_sex ORDER BY custom_age DESC) AS max_age
								FROM `tabNormal Test Template`
							)
							SELECT
								lab_test_event,
								lab_test_uom,
								COALESCE(
									(SELECT custom_min_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
									(SELECT custom_min_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age < {age}))
								) AS custom_min_value,
								COALESCE(
									(SELECT custom_max_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
									(SELECT custom_max_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age < {age}))
								) AS custom_max_value
							FROM cte c
							WHERE parent = '{exam}'
							AND custom_sex = '{doc.patient_sex}'
							GROUP BY
								lab_test_event;""", as_dict=True)
						for mm in minmax:
							new_doc.append('normal_test_items', {
								'lab_test_name': exam, 
								'custom_min_value': mm.custom_min_value, 
								'custom_max_value': mm.custom_max_value, 
								'lab_test_event': mm.lab_test_event, 
								'lab_test_uom': mm.lab_test_uom,
								'custom_sample': item.sample
							})
							normal_toggle = 1
					if selective:
						for sel in template_doc.custom_selective:
							new_doc.append('custom_selective_test_result', {
								'event': exam,
								'result_set': sel.result_select, 
								'result': sel.result_select.splitlines()[0],
								'sample': item.sample
							})
		new_doc.normal_toggle = normal_toggle
	else:
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'branch': doc.branch,
			'queue_pooling': doc.queue_pooling,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'patient_encounter': doc.patient_encounter,
			'appointment': doc.appointment,
			'dispatcher': doc.dispatcher,
			'service_unit': doc.service_unit,
			'created_date': today(),
			'remark': doc.remark,
			'exam': doc.name
		})
		if target == 'Nurse Result':
			count_nurse_result = frappe.db.sql(f"""SELECT count(*) count FROM `tabNurse Examination Template` tnet
				WHERE EXISTS (SELECT * FROM `tabNurse Examination Request` tner 
				WHERE tner.parent = '{doc.name}' AND tnet.name = tner.template)
				AND tnet.result_in_exam = 0""", as_dict = True)
			if count_nurse_result[0].count == 0:
				return
		for item in doc.examination_item:
			if item.status == 'Finished':
				item_status = 'Started'
				if target == 'Nurse Result' and frappe.db.get_value('Nurse Examination Template', item.template, 'result_in_exam'):
					item_status = 'Finished'
				new_doc.append('examination_item', {
					'status': item_status,
					'template': item.template,
					'status_time': item.status_time if item.status == 'Finished' else None
				})
				match target:
					case 'Radiology Result':
						not_created = False
						template = 'Radiology Result Template'
						template_doc = frappe.get_doc(template, item.template)
						for result in template_doc.items:
							if result.sex:
								if result.sex == doc.patient_sex:
									new_doc.append('result', {
										'result_line': result.result_text,
										'normal_value': result.normal_value,
										'mandatory_value': result.mandatory_value,
										'result_check': result.normal_value,
										'item_code': template_doc.item_code,
										'result_options': result.result_select
									})
							else:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select
								})
					case 'Nurse Result':
						not_created = False
						template = 'Nurse Examination Template'
						template_doc = frappe.get_doc(template, item.template)
						if getattr(template_doc, 'result_in_exam', None):
							for result in doc.result:
								if template_doc.item_code == result.item_code:
									new_doc.append('result', {
										'item_code': result.item_code,
										'item_name': result.item_name,
										'result_line': result.result_line,
										'result_check': result.result_check,
										'result_text': result.result_text,
										'normal_value': result.normal_value,
										'result_options': result.result_options,
										'mandatory_value': result.mandatory_value,
										'is_finished': True
									})
							for normal_item in doc.non_selective_result:
								if template_doc.item_code == normal_item.item_code:
									new_doc.append('non_selective_result', {
										'item_code': normal_item.item_code,
										'test_name': normal_item.test_name,
										'test_event': normal_item.test_event,
										'result_value': normal_item.result_value,
										'test_uom': normal_item.test_uom,
										'min_value': normal_item.min_value,
										'max_value': normal_item.max_value,
										'is_finished': True
									})
						else:
							for result in template_doc.items:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select,
									'is_finished': False
								})
							for normal_item in template_doc.normal_items:
								new_doc.append('non_selective_result', {
									'item_code': template_doc.item_code,
									'test_name': normal_item.heading_text,
									'test_event': normal_item.lab_test_event,
									'test_uom': normal_item.lab_test_uom,
									'min_value': normal_item.min_value,
									'max_value': normal_item.max_value,
									'is_finished': False
								})
					case _:
						frappe.throw(f"Unhandled Template for {target} DocType.")
	if not not_created:
		new_doc.insert(ignore_permissions=True)
	return new_doc.name
