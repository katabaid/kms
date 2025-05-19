# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	message = frappe.db.get_value('Patient Appointment', filters.exam_id, 'patient_name')
	return columns, data, message

def make_column (label, name, type='Data', width=150, align='left'):
	return {
		'label': label,								'fieldname': name,						'fieldtype': type,
		'width': width,								'align': align
	}

def make_row (
	indent, exam_type='', status='', result_line='', result_value='', uom='', 
	min_value='', max_value=''):
	return {
		'exam_type': exam_type,				'status': status,							'result_line': result_line,
		'result_value': result_value,	'uom': uom,										'min_value': min_value,
		'max_value': max_value,				'indent': indent
	}

def get_columns():
	return [
		make_column(_('Exam Type'), 'exam_type', 'Data', 250),
		make_column(_('Status'), 'status', 'Data', 100),
		make_column(_('Result Line'), 'result_line', 'Data', 250),
		make_column(_('Result Value'), 'result_value', 'Data', 300),
		make_column(_('UOM'), 'uom'),
		make_column(_('Min Value'), 'min_value', 'Data', 100, 'right'),
		make_column(_('Max Value'), 'max_value', 'Data', 100, 'right'),
	]

def get_data(filters):
	exams = frappe.db.sql(f"""
		SELECT DISTINCT tma.examination_item, tma.item_name, tma.status
		FROM `tabMCU Appointment` tma , tabItem ti
		WHERE parent = '{filters.exam_id}'
		AND tma.examination_item = ti.name
		ORDER BY ti.custom_bundle_position""", as_dict = 1)
	group_data = []
	previous_exam_item = ''
	for exam in exams:
		group_data.append(make_row(0, exam.item_name, exam.status))
		if previous_exam_item != exam.item_code:
			for child in get_children(filters.exam_id, exam.item_name, exam.examination_item):
				group_data.append(make_row(
					1, '', '', child.result_line, child.result_text, child.uom, child.min_value, child.max_value
				))
		previous_exam_item = exam.examination_item
	return group_data

def get_children(exam_id, name, item):
	return frappe.db.sql(f"""
		SELECT idx, lab_test_event AS result_line, custom_min_value AS min_value, custom_max_value AS max_value, result_value AS result_text, lab_test_uom AS uom 
		FROM `tabNormal Test Result` tntr 
		WHERE EXISTS (SELECT 1 FROM `tabLab Test` tlt WHERE tntr.parent = tlt.name AND tlt.custom_appointment = '{exam_id}' AND docstatus = 1) 
		AND lab_test_name = '{name}'
		UNION
		SELECT idx, event, NULL, NULL, result, NULL FROM `tabSelective Test Template` tstt 
		WHERE EXISTS (SELECT 1 FROM `tabLab Test` tlt WHERE tstt.parent = tlt.name AND tlt.custom_appointment = '{exam_id}' AND docstatus = 1) 
		AND event = '{name}'
		UNION
		SELECT idx, result_line, NULL, NULL, result_text, result_check FROM `tabRadiology Results` trr 
		WHERE EXISTS (SELECT 1 FROM `tabRadiology Result` trr2 WHERE trr.parent = trr2.name AND trr2.appointment = '{exam_id}' AND docstatus = 1) 
		AND item_name = '{name}'
		UNION
		SELECT idx, result_line, NULL, NULL, result_text, result_check FROM `tabNurse Examination Selective Result` tdesr
		WHERE EXISTS (SELECT 1 FROM `tabNurse Examination` tde WHERE tde.name = tdesr.parent AND tde.appointment = '{exam_id}' AND docstatus = 1)
		AND item_name = '{name}'
		UNION
		SELECT idx, test_name, min_value, max_value, result_value, test_uom FROM `tabNurse Examination Result` tder 
		WHERE EXISTS (SELECT 1 FROM `tabNurse Examination` tde WHERE tde.name = tder.parent AND tde.appointment = '{exam_id}' AND docstatus = 1)
		AND item_code = '{item}'
		UNION
		SELECT idx, test_label, NULL, NULL, RESULT, NULL FROM `tabCalculated Exam` tce
		WHERE EXISTS (SELECT 1 FROM `tabNurse Examination` tde WHERE tde.name = tce.parent AND tde.appointment = '{exam_id}' AND docstatus = 1)
		AND item_code = '{item}'
		UNION
		SELECT idx, result_line, NULL, NULL, result_text, result_check FROM `tabNurse Examination Selective Result` tnesr
		WHERE EXISTS (SELECT 1 FROM `tabNurse Result` tnr WHERE tnr.name = tnesr.parent AND tnr.appointment = '{exam_id}' AND docstatus = 1)
		AND item_name = '{name}'
		UNION
		SELECT idx, test_name, result_value, test_uom, min_value, max_value FROM `tabNurse Examination Result` tner
		WHERE EXISTS (SELECT 1 FROM `tabNurse Result` tnr WHERE tnr.name = tner.parent AND tnr.appointment = '{exam_id}' AND docstatus = 1)
		AND item_code = '{item}'
		UNION
		SELECT idx, result_line, NULL, NULL, result_text, result_check FROM `tabDoctor Examination Selective Result` tdesr
		WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.name = tdesr.parent AND tde.appointment = '{exam_id}' AND docstatus = 1)
		AND item_name = '{name}'
		UNION
		SELECT idx, test_name, result_value, test_uom, min_value, max_value FROM `tabDoctor Examination Result` tder 
		WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.name = tder.parent AND tde.appointment = '{exam_id}' AND docstatus = 1)
		AND item_code = '{item}'
		UNION
		SELECT idx, 'Eyes', NULL, NULL,
		CONCAT_WS(
			', ', 
			CASE WHEN LENGTH(tde.eyes_left_others)>0 THEN CONCAT('Left: ', tde.eyes_left_others) END, 
			CASE WHEN LENGTH(tde.eyes_right_others)>0 THEN CONCAT('Right: ', tde.eyes_right_others) END
		),
		IF(tde.eyes_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.left_anemic>0 THEN 'Left Anemic' END, 
				CASE WHEN tde.left_icteric>0 THEN 'Left Icteric' END, 
				CASE WHEN tde.right_anemic>0 THEN 'Right Anemic' END, 
				CASE WHEN tde.right_icteric>0 THEN 'Rightt Icteric' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Ear', NULL, NULL, 
		CONCAT_WS(
			', ', 
			CASE WHEN LENGTH(tde.ear_left_others)>0 THEN CONCAT('Left: ', tde.ear_left_others) END, 
			CASE WHEN LENGTH(tde.ear_right_others)>0 THEN CONCAT('Right: ', tde.ear_right_others) END
		),
		IF(
			tde.ear_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.left_cerumen>0 THEN 'Left Cerumen' END, 
				CASE WHEN tde.left_cerumen_prop>0 THEN 'Left Cerumen Prop' END, 
				CASE WHEN tde.left_tympanic>0 THEN 'Left Tympanic membrane intact' END, 
				CASE WHEN tde.right_cerumen>0 THEN 'Right Cerumen' END, 
				CASE WHEN tde.right_cerumen_prop>0 THEN 'Right Cerumen Prop' END, 
				CASE WHEN tde.right_tympanic>0 THEN 'Right Tympanic membrane intact' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Nose', NULL, NULL,
		CONCAT_WS(
			', ', 
			CASE WHEN LENGTH(tde.nose_left_others)>0 THEN CONCAT('Left: ', tde.nose_left_others) END, 
			CASE WHEN LENGTH(tde.nose_right_others)>0 THEN CONCAT('Right: ', tde.nose_right_others) END
		),
		IF(
			tde.nose_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.deviated>0 THEN 'Deviated' END, 
				CASE WHEN tde.left_enlarged>0 THEN 'Left Enlarged' END, 
				CASE WHEN tde.left_hyperemic>0 THEN 'Left Hyperemic' END, 
				CASE WHEN tde.left_polyp>0 THEN 'Left Polyp' END, 
				CASE WHEN tde.right_enlarged>0 THEN 'Right Enlarged' END, 
				CASE WHEN tde.right_hyperemic>0 THEN 'Right Hyperemic' END, 
				CASE WHEN tde.right_polyp>0 THEN 'Right Polyp' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Throat', NULL, NULL, tde.throat_others,
		IF(
			tde.throat_check>0, 
			'No Abnormality', 
			CONCAT_WS(', ', CASE WHEN tde.enlarged_tonsil>0 THEN 'Enlarged Tonsil' END, CASE WHEN tde.hyperemic_pharynx>0 THEN 'Hyperemic Pharynx' END)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Neck', NULL, NULL, tde.neck_others,
		IF(
			tde.neck_check>0, 
			'No Abnormality', 
			CONCAT_WS(', ', CASE WHEN tde.enlarged_thyroid>0 THEN 'Enlarged Thyroid' END, CASE WHEN tde.enlarged_lymph_node>0 THEN 'Enlarged Lymph Node' END)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
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
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Breast', NULL, NULL,
		CONCAT_WS(
			', ', 
			CASE WHEN LENGTH(tde.breast_left_others)>0 THEN CONCAT('Left: ', tde.breast_left_others) END, 
			CASE WHEN LENGTH(tde.breast_right_others)>0 THEN CONCAT('Right: ', tde.breast_right_others) END
		),
		IF(
			tde.breast_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.left_enlarged_breast>0 THEN 'Enlarged Left Breast Glands' END, 
				CASE WHEN tde.left_lumps>0 THEN 'Left Lumps' END, 
				CASE WHEN tde.right_enlarged_breast>0 THEN 'Enlarged Right Breast Glands' END, 
				CASE WHEN tde.right_lumps>0 THEN 'Right Lumps' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Respiratory System', NULL, NULL,
		CONCAT_WS(
			', ', 
			CASE WHEN LENGTH(tde.resp_left_others)>0 THEN CONCAT('Left: ', tde.resp_left_others) END, 
			CASE WHEN LENGTH(tde.resp_right_others)>0 THEN CONCAT('Right: ', tde.resp_right_others) END
		),
		IF(
			tde.resp_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.left_ronkhi>0 THEN 'Left Ronkhi' END, 
				CASE WHEN tde.left_wheezing>0 THEN 'Left Wheezing' END, 
				CASE WHEN tde.right_ronkhi>0 THEN 'Enlarged Ronkhi' END, 
				CASE WHEN tde.right_wheezing>0 THEN 'Right Wheezing' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Abdomen', NULL, NULL, tde.abd_others,
		IF(
			tde.abd_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.tenderness>0 THEN 'Tenderness' END, 
				CASE WHEN tde.hepatomegaly>0 THEN 'Hepatomegaly' END, 
				CASE WHEN tde.splenomegaly>0 THEN 'Splenomegaly' END, 
				CASE WHEN tde.increased_bowel_sounds>0 THEN 'Increased Bowel Sounds' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Spine', NULL, NULL, tde.spine_details,
		IF(tde.spine_check>0, 'No Abnormality', '')
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Genitourinary', NULL, NULL, tde.genit_others,
		IF(
			tde.genit_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.hernia>0 THEN 'Hernia' END, 
				CASE WHEN tde.hemorrhoid>0 THEN 'Hemorrhoid' END, 
				CASE WHEN tde.inguinal_nodes>0 THEN 'Inguinal Nodes' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Neurological System', NULL, NULL, tde.neuro_others,
		IF(
			tde.neuro_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.motoric_system_abnormality>0 THEN 'Motoric System Abnormality' END, 
				CASE WHEN tde.reflexes_abnormality>0 THEN 'Reflexes Abnormality' END, 
				CASE WHEN tde.sensory_system_abnormality>0 THEN 'Sensory System Abnormality' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Skin', NULL, NULL, tde.skin_others,
		IF(
			tde.skin_check>0, 
			'No Abnormality', 
			CONCAT_WS(
				', ', 
				CASE WHEN tde.skin_psoriasis>0 THEN 'Psoriasis' END, 
				CASE WHEN tde.skin_tattoo>0 THEN 'Tattoo' END, 
				CASE WHEN tde.skin_tag>0 THEN 'Skin Tag' END
			)
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'physical_examination_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Visual Field Test', NULL, NULL, tde.visual_details, IF(tde.visual_check>0, 'Same As Examiner', '')
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'visual_field_test_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Romberg Test', NULL, NULL, tde.romberg_others, 
		IF(tde.romberg_check>0, 'No Abnormality', tde.romberg_abnormal)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'romberg_test_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Tinnel Test', NULL, NULL, tde.tinnel_details,
		IF(tde.tinnel_check>0, 'No Abnormality', '')
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'tinnel_test_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Phallen Test', NULL, NULL, tde.phallen_details,
		IF(tde.phallen_check>0, 'No Abnormality', '')
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'phallen_test_name' AND ts.value = tder.template))
		UNION
		SELECT idx, 'Rectal Examination', NULL, NULL, tde.rectal_others,
		IF(
			tde.rectal_check>0, 
			'No Abnormality', 
			CONCAT_WS(', ', IF(tde.enlarged_prostate>0, 'Enlarged Prostate', ''), CONCAT('Hemorrhoid: ', tde.rectal_hemorrhoid))
		)
		FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND EXISTS 
		(SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'rectal_test_name' AND ts.value = tder.template))
		UNION
		SELECT idx, result_line, min_value, max_value, result_text, uom FROM (
		SELECT 1, idx, 'Intra Oral' AS result_line, NULL AS min_value, NULL AS max_value, GROUP_CONCAT(intra_oral) AS result_text, NULL AS uom 
		FROM `tabIntra Oral` tio WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND tio.parent = tde.name 
		AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
		HAVING GROUP_CONCAT(intra_oral) IS NOT NULL
		UNION
		SELECT 2, idx, 'Extra Oral', NULL, NULL, GROUP_CONCAT(extra_oral), NULL 
		FROM `tabExtra Oral` teo WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND teo.parent = tde.name 
		AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
		HAVING GROUP_CONCAT(extra_oral) IS NOT NULL
		UNION
		SELECT 4, idx+100, other, NULL, NULL, selective_value, value 
		FROM `tabOther Dental` tod WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND tod.parent = tde.name 
		AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template)))
		UNION
		SELECT 3, idx+10, CONCAT_WS(': ', teeth_type, location), NULL, NULL, `position`, OPTIONS
		FROM `tabDental Detail` tdd WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination` tde WHERE tde.appointment = '{exam_id}' AND docstatus = 1 AND tdd.parent = tde.name 
		AND EXISTS (SELECT 1 FROM `tabDoctor Examination Request` tder WHERE tde.name = tder.parent AND tder.template = '{name}' AND EXISTS 
		(SELECT 1 FROM tabSingles ts WHERE ts.doctype = 'MCU Settings' AND ts.field = 'dental_examination_name' AND ts.value = tder.template))) ORDER BY 1, 2) AS t		
		ORDER BY 1
	""", as_dict=1)
