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
def get_columns():
	return [
		make_column(_('Exam #'), 'parent', 'Data', 250),
		make_column(_('Test Name'), 'test_name', 'Data', 250),
		make_column(_('Test Event'), 'test_event', 'Data', 250),
		make_column(_('Result Value'), 'result_value', 'Float', 100, 'right'),
		make_column(_('UOM'), 'test_uom', 'Data', 100),
		make_column(_('Min Value'), 'min_value', 'Float', 100, 'right'),
		make_column(_('Max Value'), 'max_value', 'Float', 100, 'right'),
	]
def get_data(filters):
	return frappe.db.sql(f"""
		SELECT parent, test_name, test_event, result_value, test_uom, min_value, max_value FROM `tabDoctor Examination Result` tner, `tabDoctor Examination` tne 
		WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination Template` tnet WHERE tner.item_code = tnet.item_code)
		AND tne.name = tner.parent AND tne.appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT parent, test_label, NULL, result, NULL, NULL, NULL FROM `tabCalculated Exam` tce, `tabDoctor Examination` tne 
		WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination Template` tnet WHERE tce.item_code = tnet.item_code)
		AND tne.name = tce.parent AND tne.appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT parent, result_line, NULL, result_check, result_text, NULL, NULL FROM `tabDoctor Examination Selective Result` tnesr, `tabDoctor Examination` tne 
		WHERE EXISTS (SELECT 1 FROM `tabDoctor Examination Template` tnet WHERE tnesr.item_code = tnet.item_code)
		AND tne.name = tnesr.parent AND tne.appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT
		name, 'Eyes', NULL, IF(tde.eyes_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.left_anemic>0 THEN 'Left Anemic' END, CASE WHEN tde.left_icteric>0 THEN 'Left Icteric' END, CASE WHEN tde.right_anemic>0 THEN 'Right Anemic' END, CASE WHEN tde.right_icteric>0 THEN 'Rightt Icteric' END)),
		CONCAT_WS(', ', CASE WHEN LENGTH(tde.eyes_left_others)>0 THEN CONCAT('Left: ', tde.eyes_left_others) END, CASE WHEN LENGTH(tde.eyes_right_others)>0 THEN CONCAT('Right: ', tde.eyes_right_others) END),
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Ear', NULL, IF(tde.ear_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.left_cerumen>0 THEN 'Left Cerumen' END, CASE WHEN tde.left_cerumen_prop>0 THEN 'Left Cerumen Prop' END, CASE WHEN tde.left_tympanic>0 THEN 'Left Tympanic membrane intact' END, CASE WHEN tde.right_cerumen>0 THEN 'Right Cerumen' END, CASE WHEN tde.right_cerumen_prop>0 THEN 'Right Cerumen Prop' END, CASE WHEN tde.right_tympanic>0 THEN 'Right Tympanic membrane intact' END)), 
		CONCAT_WS(', ', CASE WHEN LENGTH(tde.ear_left_others)>0 THEN CONCAT('Left: ', tde.ear_left_others) END, CASE WHEN LENGTH(tde.ear_right_others)>0 THEN CONCAT('Right: ', tde.ear_right_others) END), 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Nose', NULL, IF(tde.nose_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.deviated>0 THEN 'Deviated' END, CASE WHEN tde.left_enlarged>0 THEN 'Left Enlarged' END, CASE WHEN tde.left_hyperemic>0 THEN 'Left Hyperemic' END, CASE WHEN tde.left_polyp>0 THEN 'Left Polyp' END, CASE WHEN tde.right_enlarged>0 THEN 'Right Enlarged' END, CASE WHEN tde.right_hyperemic>0 THEN 'Right Hyperemic' END, CASE WHEN tde.right_polyp>0 THEN 'Right Polyp' END)), 
		CONCAT_WS(', ', CASE WHEN LENGTH(tde.nose_left_others)>0 THEN CONCAT('Left: ', tde.nose_left_others) END, CASE WHEN LENGTH(tde.nose_right_others)>0 THEN CONCAT('Right: ', tde.nose_right_others) END), 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Throat', NULL, IF(tde.throat_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.enlarged_tonsil>0 THEN 'Enlarged Tonsil' END, CASE WHEN tde.hyperemic_pharynx>0 THEN 'Hyperemic Pharynx' END)),
		tde.throat_others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Neck', NULL, IF(tde.neck_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.enlarged_thyroid>0 THEN 'Enlarged Thyroid' END, CASE WHEN tde.enlarged_lymph_node>0 THEN 'Enlarged Lymph Node' END)),
		tde.neck_others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Cardiac', NULL, IF(tde.cardiac_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.regular_heart_sound>0 THEN 'Regular Heart Sound' END, CASE WHEN tde.murmur>0 THEN 'Murmur' END, CASE WHEN tde.gallop>0 THEN 'Gallop' END)),
		tde.others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Breast', NULL, IF(tde.breast_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.left_enlarged_breast>0 THEN 'Enlarged Left Breast Glands' END, CASE WHEN tde.left_lumps>0 THEN 'Left Lumps' END, CASE WHEN tde.right_enlarged_breast>0 THEN 'Enlarged Right Breast Glands' END, CASE WHEN tde.right_lumps>0 THEN 'Right Lumps' END)), 
		CONCAT_WS(', ', CASE WHEN LENGTH(tde.breast_left_others)>0 THEN CONCAT('Left: ', tde.breast_left_others) END, CASE WHEN LENGTH(tde.breast_right_others)>0 THEN CONCAT('Right: ', tde.breast_right_others) END), 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Respiratory System', NULL, IF(tde.resp_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.left_ronkhi>0 THEN 'Left Ronkhi' END, CASE WHEN tde.left_wheezing>0 THEN 'Left Wheezing' END, CASE WHEN tde.right_ronkhi>0 THEN 'Enlarged Ronkhi' END, CASE WHEN tde.right_wheezing>0 THEN 'Right Wheezing' END)), 
		CONCAT_WS(', ', CASE WHEN LENGTH(tde.resp_left_others)>0 THEN CONCAT('Left: ', tde.resp_left_others) END, CASE WHEN LENGTH(tde.resp_right_others)>0 THEN CONCAT('Right: ', tde.resp_right_others) END), 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Abdomen', NULL, IF(tde.abd_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.tenderness>0 THEN 'Tenderness' END, CASE WHEN tde.hepatomegaly>0 THEN 'Hepatomegaly' END, CASE WHEN tde.splenomegaly>0 THEN 'Splenomegaly' END, CASE WHEN tde.increased_bowel_sounds>0 THEN 'Increased Bowel Sounds' END)),
		tde.abd_others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Spine', NULL, IF(tde.spine_check>0, 'No Abnormality', ''),
		tde.spine_details, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Genitourinary', NULL, IF(tde.genit_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.hernia>0 THEN 'Hernia' END, CASE WHEN tde.hemorrhoid>0 THEN 'Hemorrhoid' END, CASE WHEN tde.inguinal_nodes>0 THEN 'Inguinal Nodes' END)),
		tde.genit_others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')
		UNION
		SELECT 
		name, 'Neurological System', NULL, IF(tde.neuro_check>0, 'No Abnormality', CONCAT_WS(', ', CASE WHEN tde.motoric_system_abnormality>0 THEN 'Motoric System Abnormality' END, CASE WHEN tde.reflexes_abnormality>0 THEN 'Reflexes Abnormality' END, CASE WHEN tde.sensory_system_abnormality>0 THEN 'Sensory System Abnormality' END)),
		tde.neuro_others, 
		NULL, NULL
		FROM `tabDoctor Examination` tde WHERE appointment = '{filters.exam_id}' AND service_unit IN  ('{filters.room}')""", as_dict = 1)
