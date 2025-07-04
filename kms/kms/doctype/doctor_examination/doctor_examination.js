const customBeforeSubmit = (frm) => {
  if (frm.doc.some_field === 'some_value') {
    frappe.throw('Cannot submit when some_field is some_value');
  } else {
    doctorExaminationController.utils.handleBeforeSubmit(frm);
  }
};

const handleTabVisibility = (frm) => {
  const sectionsToHide = [
    'eyes_section', 'ear_section', 'nose_section', 'throat_section', 'neck_section', 
    'cardiac_section', 'breast_section', 'resp_section', 'abd_section', 'spine_section', 
    'genit_section', 'neuro_section', 'skin_section', 'measurement_section', 'dental_section', 
    'teeth_section', 'grade_section', 'visual_field_test_section', 'romberg_test_section',
     'tinnel_test_section', 'phallen_test_section', 'rectal_examination_section'
  ];
  const visibleStatus = ['Checked In', 'Finished', 'Partial Finished'];
  const visibleRowStatus = ['Started', 'Checked In', 'Finished', 'Partial Finished'];
  sectionsToHide.forEach(section => frm.set_df_property(section, 'hidden', 1));
  if (visibleStatus.includes(frm.doc.status)) {
    const examItems = frm.doc.examination_item.filter(row => visibleRowStatus.includes(row.status)).map(row => row.template)
    const matchingItems = mcu_settings.filter(item => examItems.includes(item.value));
    if (matchingItems.length > 0) {
      matchingItems.forEach(item => {
        if (item.field === 'physical_examination_name') sectionsToHide.slice(0, 14).forEach(section => frm.set_df_property(section, 'hidden', 0));
        if (item.field === 'visual_field_test_name') frm.set_df_property('visual_field_test_section', 'hidden', 0);
        if (item.field === 'romberg_test_name') frm.set_df_property('romberg_test_section', 'hidden', 0);
        if (item.field === 'tinnel_test_name') frm.set_df_property('tinnel_test_section', 'hidden', 0);
        if (item.field === 'phallen_test_name') frm.set_df_property('phallen_test_section', 'hidden', 0);
        if (item.field === 'rectal_test_name') frm.set_df_property('rectal_examination_section', 'hidden', 0);
        if (item.field === 'dental_examination_name') sectionsToHide.slice(14, 17).forEach(section => frm.set_df_property(section, 'hidden', 0));
      });
    }
  }
}

// Function to determine if dental sections should be handled
const shouldShowDentalSections = (frm, settings) => {
  let dentalTemplateName = '';
  // Ensure settings is loaded and is an array
  if (Array.isArray(settings)) {
    const dentalSetting = settings.find(item => item.field === 'dental_examination_name');
    if (dentalSetting) {
      dentalTemplateName = dentalSetting.value;
    }
  }

  // Ensure examination_item exists and dentalTemplateName was found
  if (dentalTemplateName && Array.isArray(frm.doc.examination_item)) {
    return frm.doc.examination_item.some(item => item.template === dentalTemplateName);
  }
  return false; // Return false if conditions aren't met
}

const handleDentalSections = (frm) => {
  prepareDentalSections(frm);
  prepareStaticDental(frm);
  prepareOtherDentalOptions(frm);
}

const prepareDentalSections = (frm) => {
  const referenceArray = [
    'missing', 'filling', 'radix', 'abrasion', 'crown', 'veneer', 'persistent', 'abscess', 'impaction', 
    'caries', 'fracture', 'tooth mobility', 'bridge', 'gingival recession', 'exfoliation', 'fistula',
    'loose filling', 'loose crown', 'broken filling', 'broken crown'
  ];

  const generateOptions = item => referenceArray.reduce((acc, key) => {
    acc[key] = (item.options && item.options.split(', ').includes(key)) ? 1 : 0;
    return acc;
  }, {});

  const mapDetails = data => data.map(item => ({
    idx: item.idx,
    teeth_type: item.teeth_type,
    location: item.location,
    position: item.position,
    options: generateOptions(item)
  }));

  const generateRadioHtml = (data, customType, alignment) => {
    const gridTemplateColumns = '1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr';
    const justifyContent = alignment === 'left' ? 'start' : 'end';
    const filler = alignment.concat(customType) === 'startPrimary Teeth' ? '<div></div><div></div><div></div>' : '';
    const labelColor = customType === 'Primary Teeth' ? 'blue' : 'inherit';
    return `
      <div style="display:grid;grid-template-columns: ${gridTemplateColumns};justify-content: ${justifyContent};">
        ${filler}
        ${data.reduce((html, item) => `${html}
        <label style="display: flex; flex-direction: column; align-items: center; color: ${labelColor};">
          <input type="radio" name="custom_radio" style="margin:0 !important;" value="${item.position}">
          ${item.position}
        </label>`, '')}
      </div>
    `;
  };

  const filterAndMapDetails = (detail, custom_type, location) => {
    const filteredData = detail.filter(record => record.teeth_type === custom_type && record.location === location);
    return mapDetails(filteredData);
  };

  const transformDataToObjectArray = (data) => {
    const result = [];
    for (const [key, value] of Object.entries(data)) {
      const obj = { key, value };
      result.push(obj);
    }
    return result;
  };
  const pt_ul_map = filterAndMapDetails(frm.doc.dental_detail, 'Permanent Teeth', 'ul');
  const pt_ur_map = filterAndMapDetails(frm.doc.dental_detail, 'Permanent Teeth', 'ur');
  const pt_ll_map = filterAndMapDetails(frm.doc.dental_detail, 'Permanent Teeth', 'll');
  const pt_lr_map = filterAndMapDetails(frm.doc.dental_detail, 'Permanent Teeth', 'lr');
  const pr_ul_map = filterAndMapDetails(frm.doc.dental_detail, 'Primary Teeth', 'ul');
  const pr_ur_map = filterAndMapDetails(frm.doc.dental_detail, 'Primary Teeth', 'ur');
  const pr_ll_map = filterAndMapDetails(frm.doc.dental_detail, 'Primary Teeth', 'll');
  const pr_lr_map = filterAndMapDetails(frm.doc.dental_detail, 'Primary Teeth', 'lr');

  let radio_html = `
    <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
      ${generateRadioHtml(pt_ul_map, 'Permanent Teeth', 'end')}
      ${generateRadioHtml(pt_ur_map, 'Permanent Teeth', 'start')}
    </div>
    <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
      ${generateRadioHtml(pr_ul_map, 'Primary Teeth', 'start')}
      ${generateRadioHtml(pr_ur_map, 'Primary Teeth', 'end')}
    </div>
    <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
      ${generateRadioHtml(pr_ll_map, 'Primary Teeth', 'start')}
      ${generateRadioHtml(pr_lr_map, 'Primary Teeth', 'end')}
    </div>
    <div style="display:grid;grid-gap:1rem;grid-template-columns: 1fr 1fr;margin-bottom: 2rem;">
      ${generateRadioHtml(pt_ll_map, 'Permanent Teeth', 'end')}
      ${generateRadioHtml(pt_lr_map, 'Permanent Teeth', 'start')}
    </div>
  `;
  const data = pt_ul_map.concat(pt_ur_map, pt_ll_map, pt_lr_map, pr_ul_map, pr_ur_map, pr_ll_map, pr_lr_map);
  $(frm.fields_dict.dental_teeth_html.wrapper).html(radio_html);
  $(frm.fields_dict.dental_teeth_html.wrapper).find('input[type=radio][name=custom_radio]').on('change', function () {
    unhide_field('teeth_options_html');
    const selected = data.find(item => item.position == $(this).val());
    const selected_array = transformDataToObjectArray(selected.options);
    const $wrapper = frm.get_field("teeth_options_html").$wrapper;
    $wrapper.empty();
    const options_wrapper = $(`<div class="options_wrapper">`).appendTo($wrapper);
    frm.options_multicheck = frappe.ui.form.make_control({
      parent: options_wrapper,
      df: {
        fieldname: "options_multicheck",
        fieldtype: "MultiCheck",
        select_all: false,
        columns: 8,
        get_data: () => {
          const currentPosition = selected.position;
          // Check cache (dirtyDentalOptions stores an array of selected option keys for a position)
          const dirtyOptionsArray = frm.dirtyDentalOptions[currentPosition];

          return selected_array.map((option) => {
            let isChecked;
            if (dirtyOptionsArray !== undefined) {
              // Use cache if available
              isChecked = dirtyOptionsArray.includes(option.key);
            } else {
              // Otherwise, use the original value from the document/initial load
              isChecked = option.value;
            }
            return {
              label: option.key === 'rg' ? 'Gingival Recession' : option.key.toLowerCase().replace(/\b\w/g, s => s.toUpperCase()),
              value: option.key,
              checked: isChecked,
            };
          });
        },
      },
      render_input: true,
    });
    frm.options_multicheck.refresh_input();
    setTimeout(() => {
      frm.options_multicheck.$wrapper.find('.unit-checkbox').css('margin-bottom', '30px');
      frm.options_multicheck.$wrapper.find(`input[type="checkbox"]`).each(function () {
        $(this).change(() => {
          const multicheck_field = frm.options_multicheck.$wrapper.find('input[type="checkbox"]');
          const selected_options = [];
          multicheck_field.each(function () {
            if ($(this).is(':checked')) {
              selected_options.push($(this).attr('data-unit'));
            }
          });
          // Update the cache
          frm.dirtyDentalOptions[selected.position] = selected_options;

          // Update the document field (marks form as dirty)
          $.each(frm.doc.dental_detail || [], (index, row) => {
            if (row.position === selected.position) {
              frappe.model.set_value(row.doctype, row.name, 'options', selected_options.join(', '));
            }
          });
        });
      });
    }, 100);
  });
  $('input[type=radio][name=custom_radio]').change(function () {
    $(frm.fields_dict.dental_teeth_html.wrapper).find('label').css('font-weight', 'normal');
    if (this.checked) {
        $(this).parent('label').css('font-weight', 'bold');
    }
  });
}

const prepareStaticDental = (frm) => {
  const transform = (source) => {
    const map = {};
    const locations = ['ul', 'ur', 'll', 'lr'];
    // Initialize map with empty arrays for each location and type
    locations.forEach(location => {
      map[location] = {
        'Permanent Teeth': Array(8).fill(null),
        'Primary Teeth': Array(5).fill(null)
      };
    });
  
    // Fill the map with data from arr1
    source.forEach(item => {
      const { location, position, teeth_type, options } = item;
      const index = parseInt(position) % 10 - 1;
      map[location][teeth_type][index] = { position, options: options || '' };
    });
  
    const result = [];
  
    // Build the result array
    for (let i = 0; i < 8; i++) {
      const row = {
        l_perm: map.ul['Permanent Teeth'][i] ? map.ul['Permanent Teeth'][i].position : '',
        l_opt_perm: map.ul['Permanent Teeth'][i] ? map.ul['Permanent Teeth'][i].options : '',
        l_prim: map.ul['Primary Teeth'][i] ? map.ul['Primary Teeth'][i].position : '',
        l_opt_prim: map.ul['Primary Teeth'][i] ? map.ul['Primary Teeth'][i].options : '',
        r_perm: map.ur['Permanent Teeth'][i] ? map.ur['Permanent Teeth'][i].position : '',
        r_opt_perm: map.ur['Permanent Teeth'][i] ? map.ur['Permanent Teeth'][i].options : '',
        r_prim: map.ur['Primary Teeth'][i] ? map.ur['Primary Teeth'][i].position : '',
        r_opt_prim: map.ur['Primary Teeth'][i] ? map.ur['Primary Teeth'][i].options : ''
      };
      result.push(row);
    }
  
    for (let i = 0; i < 8; i++) {
      const row = {
        l_perm: map.ll['Permanent Teeth'][i] ? map.ll['Permanent Teeth'][i].position : '',
        l_opt_perm: map.ll['Permanent Teeth'][i] ? map.ll['Permanent Teeth'][i].options : '',
        l_prim: map.ll['Primary Teeth'][i] ? map.ll['Primary Teeth'][i].position : '',
        l_opt_prim: map.ll['Primary Teeth'][i] ? map.ll['Primary Teeth'][i].options : '',
        r_perm: map.lr['Permanent Teeth'][i] ? map.lr['Permanent Teeth'][i].position : '',
        r_opt_perm: map.lr['Permanent Teeth'][i] ? map.lr['Permanent Teeth'][i].options : '',
        r_prim: map.lr['Primary Teeth'][i] ? map.lr['Primary Teeth'][i].position : '',
        r_opt_prim: map.lr['Primary Teeth'][i] ? map.lr['Primary Teeth'][i].options : ''
      };
      result.push(row);
    }
  
    return result;
  };
  const reverseLastHalf = (array) => {
    const halfIndex = Math.floor(array.length / 2);
    const firstHalf = array.slice(0, halfIndex);
    const secondHalf = array.slice(halfIndex).reverse();
    return firstHalf.concat(secondHalf);
  };
  const addColumn = (
    name,               content,          width = 50, 
    format = null,      editable = false, sortable = false, 
    focusable = false,  dropdown = false, align = 'left') => {
      return {
        name: name,
        id: name,
        content: content,
        editable: editable,
        sortable: sortable,
        focusable: focusable,
        dropdown: dropdown,
        align: align,
        width: width,
        format: format ? format : (value) => value
      }
    };
  const $wrapper = frm.get_field('dental_detail_html').$wrapper;
  const detail_wrapper = $(`<div class="detail_wrapper">`).appendTo($wrapper);
  const newdata = transform(frm.doc.dental_detail);
  const data = reverseLastHalf(newdata);

  const columns = [
    addColumn('l_perm', `${__("Pos")}`),
    addColumn('l_opt_perm', `${__("Opt")}`, 250, (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`),
    addColumn('l_prim', `${__("Pos")}`),
    addColumn('l_opt_prim', `${__("Opt")}`, 250, (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`),
    addColumn('r_opt_prim', `${__("Opt")}`, 250, (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`),
    addColumn('r_prim', `${__("Pos")}`),
    addColumn('r_opt_perm', `${__("Opt")}`, 250, (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`),
    addColumn('r_perm', `${__("Pos")}`),
  ];
  if (!frm.static_dental_datatable) {
    const datatable_options = {
      columns: columns,
      data: data,
      dynamicRowHeight: true,
      inlineFilters: false,
      layout: 'fixed',
      serialNoColumn: false,
      noDataMessage: __("No Data"),
      disableReorderColumn: true
    }
    frm.static_dental_datatable = new frappe.DataTable(
      detail_wrapper.get(0),
      datatable_options
    );
  } else {
    frm.static_dental_datatable.refresh(data, columns);
  }
}

const prepareOtherDentalOptions = (frm) => {
  if (frm.doc.docstatus === 0) {
    if (frm.doc.other_dental) {
      frm.refresh_field ('other_dental');
      setTimeout(()=>{
        $.each (frm.doc.other_dental, (key, value) => {
          frappe.db
          .get_value('Other Dental Option', value.other, 'selections')
          .then(opt=> {
            frappe.meta.get_docfield('Other Dental', 'selective_value', value.name).options = opt.message.selections.split('\n')
          })
        })
      }, 500)
    }
  }
}

const addCustomButtons = (frm) => {
  frm.add_custom_button(
    __('Exam Notes'),
    () => {
      window.open(`/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.appointment}`, '_blank');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('Questionnaires'),
    () => {
      window.open(`/app/questionnaire?patient_appointment=${frm.doc.appointment}`, '_blank');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('Patient Result'),
    () => {
      window.open(`/app/query-report/Result per Appointment?exam_id=${frm.doc.appointment}`, '_blank');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('Vital Sign'),
    () => {
      window.open(`/app/query-report/Vital SIgn and Anthropometry?exam_id=${frm.doc.appointment}`, '_blank');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('History'),
    () => {
      window.open(`/app/query-report/Doctor Examination History?exam_id=${frm.doc.appointment}&room=${frm.doc.service_unit}`, '_blank');
    },
    __('Reports')
  )
  if (ecg_doc_no && frm.doc.docstatus !== 2) {
    frm.add_custom_button(
      __('View ECG'),
      () => {
        // Construct the URL and open in a new tab
        const url = `/app/nurse-examination/${ecg_doc_no}`;
        window.open(url, '_blank');
      },
      __('Reports') // Adding under a 'Navigate' group, adjust if needed
    );
  }

};

const handleReadOnlyExams = (frm) => {
  const pe_fields = ['eyes_check','left_anemic','left_icteric','eyes_left_others','right_anemic','right_icteric',
    'eyes_right_others','ear_check','left_cerumen','left_cerumen_prop','left_tympanic','ear_left_others','right_cerumen',
    'right_cerumen_prop','right_tympanic','ear_right_others','nose_check','deviated','left_enlarged','left_hyperemic',
    'left_polyp','nose_left_others','right_enlarged','right_hyperemic','right_polyp','nose_right_others','throat_check',
    'enlarged_tonsil','hyperemic_pharynx','throat_others','neck_check','enlarged_thyroid','enlarged_thyroid_details',
    'enlarged_lymph_node','enlarged_lymph_node_details','neck_others','cardiac_check','regular_heart_sound','murmur',
    'gallop','others','breast_check','left_enlarged_breast','left_lumps','breast_left_others','right_enlarged_breast',
    'right_lumps','breast_right_others','resp_check','left_ronkhi','left_wheezing','resp_left_others','right_ronkhi',
    'right_wheezing','resp_right_others','abd_check','tenderness','abd_tender_details','hepatomegaly','splenomegaly',
    'increased_bowel_sounds','abd_others','spine_check','spine_details','genit_check','hernia','hernia_details',
    'hemorrhoid','inguinal_nodes','genit_others','neuro_section','neuro_check','motoric_system_abnormality','motoric_details',
    'sensory_system_abnormality','sensory_details','reflexes_abnormality','reflex_details','neuro_others'];
  const vft_fields = ['visual_check','visual_details'];
  const rt_fields = ['romberg_check','romberg_abnormal','romberg_others'];
  const tt_fields = ['tinnel_check','tinnel_details'];
  const pt_fields = ['phallen_check','phallen_details'];
  const rect_fields = ['rectal_check','rectal_hemorrhoid','enlarged_prostate','rectal_others'];
  //const dent_fields = ['extra_oral','intra_oral','dental_detail','other_dental'];
  const exam_list = 
    mcu_settings
    .filter(item => frm.doc.examination_item.filter(item => item.status === 'Finished').map(item => item.template).includes(item.value))
    .map(item => item.field)
    exam_list.forEach(exam=>{
      if (exam === 'physical_examination_name') pe_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      if (exam === 'visual_field_test_name') vft_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      if (exam === 'romberg_test_name') rt_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      if (exam === 'tinnel_test_name') tt_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      if (exam === 'phallen_test_name') pt_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      if (exam === 'rectal_test_name') rect_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
      //if (exam === 'dental_examination_name') dent_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
    })
};

// Use the common controller with custom before_submit function for Doctor Examination
const doctorExaminationController = kms.controller.createDocTypeController('Doctor Examination', {
  before_submit: customBeforeSubmit,
});
let mcu_settings = [];
let normal_values = true;
let ecg_doc_no = '';

// Attach the custom controller to the Doctor Examination doctype
frappe.ui.form.on('Doctor Examination', {
  ...doctorExaminationController,
  before_submit: function (frm) {
    doctorExaminationController.config.before_submit(frm);
  },

  before_load: function (frm) {
    const get_mcu_settings = () => {
      return new Promise((resolve) => {
        frappe.call({
          method: 'kms.api.healthcare.get_mcu_settings',
          callback: (r) => resolve(r.message || [])
        });
      });
    };
    const get_ecg = (exam_id) => {
      return new Promise((resolve) => {
        frappe.call({
          method: 'kms.api.healthcare.get_ecg',
          args: {exam_id: exam_id},
          callback: (r) => resolve(r.message || '')
        })
      })
    };
    promises = [get_mcu_settings()];
    promises.push(frm.doc.appointment ? get_ecg(frm.doc.appointment) : Promise.resolve(null));
    Promise.all(promises).then(([settings, ecg]) => {
      mcu_settings = settings;
      ecg_doc_no = ecg && ecg[0] ? ecg[0].parent : null;
    });
  },

  refresh: function (frm) {
    // Call the questionnaire utility
    if (frm.fields_dict.questionnaire_html && kms.utils && kms.utils.fetch_questionnaire_for_doctype) {
      kms.utils.fetch_questionnaire_for_doctype(frm, "appointment", null, "questionnaire_html"
    );
    } else {
      if (!frm.fields_dict.questionnaire_html) {
        console.warn("Doctor Examination form is missing 'questionnaire_html'. Questionnaire cannot be displayed.");
      }
      if (!kms.utils || !kms.utils.fetch_questionnaire_for_doctype) {
        console.warn("kms.utils.fetch_questionnaire_for_doctype is not available. Ensure questionnaire_helper.js is loaded.");
      }
    }
    doctorExaminationController.refresh(frm);
    frm.dirtyDentalOptions = frm.dirtyDentalOptions || {}; // Initialize or preserve dental options cache
    handleTabVisibility(frm);

    // Check if dental sections should be shown and handled
    if (shouldShowDentalSections(frm, mcu_settings)) {
      // Hide the questionnaire table when handling dental sections
      frm.set_df_property('questionnaire', 'hidden', 1);
      handleDentalSections(frm);
    } else {
      // Ensure questionnaire is visible if dental sections are not shown
      frm.set_df_property('questionnaire', 'hidden', 0);
    }

    addCustomButtons(frm);
    handleReadOnlyExams(frm);
    handleQuestionnaire(frm);
    if (frm.doc.non_selective_result) {
      frm.refresh_field('non_selective_result');
      frm.fields_dict['non_selective_result'].grid.grid_rows.forEach((row) =>{
        apply_cell_styling (frm, row.doc);
      })
    }
  },

  setup: function (frm) {
		if(frm.doc.docstatus === 0){
			if (frm.doc.result) {
				frm.refresh_field('result');
				$.each(frm.doc.result, (key, value) => {
					frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_check', value.name).options = value.result_options;
					frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_text', value.name).read_only = (value.result_check === value.normal_value) ? 1 : 0;
					frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_text', value.name).reqd = (value.result_check === value.mandatory_value) ? 1 : 0;
					if (value.is_finished) {
						frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_check', value.name).read_only = 1;
						frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_check', value.name).reqd = 0;
						frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_text', value.name).read_only = 1;
						frappe.meta.get_docfield('Doctor Examination Selective Result', 'result_text', value.name).reqd = 0;
					}
				});
			}
			if (frm.doc.non_selective_result) {
				frm.refresh_field('non_selective_result');
				$.each(frm.doc.non_selective_result, (key, value) => {
					if (value.is_finished) {
						frappe.meta.get_docfield('Doctor Examination Result', 'result_value', value.name).read_only = 1;
						frappe.meta.get_docfield('Doctor Examination Result', 'result_value', value.name).reqd = 0;
					}
				})
			}
    }
	},

  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Examination');
    frm._show_dialog_on_change = false;
		frm.doc.non_selective_result.forEach(row=>{
			row._original_result_value = row.result_value;
		})
		frm.fields_dict['conclusion'].grid.get_field('conclusion_code').get_query = function(doc, cdt, cdn) {
			let item_codes = (frm.doc.examination_item || []).map(row => row.item);
			return {
				filters: [
					['item', 'in', item_codes]
				]
			};
		};
  },

	before_save: function (frm) {
    if (frm.doc.docstatus === 0 ) {
      if (frm.continue_save) {
        frm.continue_save = false;
        return true
      }
      if (frm.doc.non_selective_result && frm.doc.non_selective_result.length > 0) {
        let has_out_of_range = false;
        frm.doc.non_selective_result.forEach(row => {
          if ((row.result_value < row.min_value || row.result_value > row.max_value) && row.min_value != 0 && row.max_value != 0 && row.result_value && row.result_value !== row._original_result_value) {
            has_out_of_range = true;
          }
        });
        if (has_out_of_range && frm._show_dialog_on_change) {
          frappe.validated = false;
          frappe.warn(
            'Results Outside Normal Range',
            'One or more results are outside the normal area. Do you want to continue?',
            () => {
              frm.continue_save = true;
              frappe.validated = true;
              frm.save();
            },
            () => {
              frappe.validated = false;
            }
          )
        }
      }
    }
	},

	after_save: function (frm) {
		frm.doc.non_selective_result.forEach(row=>{
			row._original_result_value = row.result_value;
		})
    frm._show_dialog_on_change = false;
	},
  eyes_check: function(frm){
    if(frm.doc.eyes_check){
      frm.set_value('left_anemic', 0);
      frm.set_value('left_icteric', 0);
      frm.set_value('el_others', 0);
      frm.set_value('right_anemic', 0);
      frm.set_value('right_icteric', 0);
      frm.set_value('er_others', 0);
      frm.set_value('eyes_left_others', '');
      frm.set_value('eyes_right_others', '');
    }
  },
  ear_check: function(frm){
    if(frm.doc.ear_check){
      frm.set_value('left_cerumen', 0);
      frm.set_value('left_cerumen_prop', 0);
      frm.set_value('left_tympanic', 0);
      frm.set_value('earl_others', 0);
      frm.set_value('right_cerumen', 0);
      frm.set_value('right_cerumen_prop', 0);
      frm.set_value('right_tympanic', 0);
      frm.set_value('earr_others', 0);
      frm.set_value('ear_left_others', '');
      frm.set_value('ear_right_others', '');  
    }
  },
  nose_check: function(frm){
    if(frm.doc.nose_check){
      frm.set_value('deviated', 0);
      frm.set_value('left_enlarged', 0);
      frm.set_value('left_hyperemic', 0);
      frm.set_value('left_polyp', 0);
      frm.set_value('nl_others', 0);
      frm.set_value('right_enlarged', 0);
      frm.set_value('right_hyperemic', 0);
      frm.set_value('right_polyp', 0);
      frm.set_value('nr_others', 0);
      frm.set_value('nose_left_others', '');
      frm.set_value('nose_right_others', '');
    }
  },
  throat_check: function(frm){
    if(frm.doc.throat_check){
      frm.set_value('enlarged_tonsil', 0);
      frm.set_value('hyperemic_pharynx', 0);
      frm.set_value('t_others', 0);
      frm.set_value('throat_others', '');  
    }
  },
  neck_check: function(frm){
    if(frm.doc.neck_check){
      frm.set_value('enlarged_thyroid', 0);
      frm.set_value('enlarged_lymph_node', 0);
      frm.set_value('enlarged_thyroid', 0);
      frm.set_value('enlarged_thyroid_details', '');
      frm.set_value('enlarged_lymph_node_details', '');
      frm.set_value('neck_others', '');  
    }
  },
  cardiac_check: function(frm) {
    if(frm.doc.cardiac_check){
      frm.set_value('regular_heart_sound', 0);
      frm.set_value('murmur', 0);
      frm.set_value('gallop', 0);
      frm.set_value('c_others', 0);
      frm.set_value('others', '');  
    }
  },
  breast_check: function(frm){
    if(frm.doc.breast_check){
      frm.set_value('left_enlarged_breast', 0);
      frm.set_value('left_lumps', 0);
      frm.set_value('bl_others', 0);
      frm.set_value('right_enlarged_breast', 0);
      frm.set_value('right_lumps', 0);
      frm.set_value('br_others', 0);
      frm.set_value('breast_left_others', '');
      frm.set_value('breast_right_others', '');
    }
  },
  resp_check: function(frm){
    if(frm.doc.resp_check){
      frm.set_value('left_ronkhi', 0);
      frm.set_value('left_wheezing', 0);
      frm.set_value('r_others', 0);
      frm.set_value('right_ronkhi', 0);
      frm.set_value('right_wheezing', 0);
      frm.set_value('rr_others', 0);
      frm.set_value('resp_left_others', '');
      frm.set_value('resp_right_others', '');
    }
  },
  abd_check: function(frm){
    if(frm.doc.abd_check){
      frm.set_value('tenderness', 0);
      frm.set_value('hepatomegaly', 0);
      frm.set_value('splenomegaly', 0);
      frm.set_value('increased_bowel_sounds', 0);
      frm.set_value('a_others', 0);
      frm.set_value('abd_tender_details', '');
      frm.set_value('abd_others', '');
    }
  },
  spine_check: function(frm){
    if(frm.doc.spine_check){
      frm.set_value('spine_details', '');    
    }
  },
  genit_check: function(frm){
    if(frm.doc.genit_check){
      frm.set_value('hernia', 0);
      frm.set_value('hemorrhoid', 0);
      frm.set_value('inguinal_nodes', 0);
      frm.set_value('g_others', 0);
      frm.set_value('hernia_details', '');
      frm.set_value('genit_others', '');
    }
  },
  neuro_check: function(frm){
    if(frm.doc.neuro_check){
      frm.set_value('motoric_system_abnormality', 0);
      frm.set_value('motoric_details', '');
      frm.set_value('sensory_system_abnormality', 0);
      frm.set_value('sensory_details', '');
      frm.set_value('reflexes_abnormality', 0);
      frm.set_value('reflex_details', '');
      frm.set_value('ne_others', 0);
      frm.set_value('neuro_others', '');
    }
  },
  skin_check: function(frm){
    if(frm.doc.skin_check){
      frm.set_value('skin_psoriasis', 0);
      frm.set_value('skin_tattoo', 0);
      frm.set_value('skin_tag', 0);
      frm.set_value('sk_others', 0);
      frm.set_value('skin_others', '');
      frm.set_value('skin_tattoo_location', '');
    }
  },
  visual_check: function(frm){
    if(frm.doc.visual_check){
      frm.set_value('visual_details', '');
    }
  },
  romberg_check: function(frm){
    if(frm.doc.romberg_check){
      frm.set_value('romberg_abnormal','');
      frm.set_value('romberg_others','');
    }
  },
  tinnel_check: function(frm){
    if(frm.doc.tinnel_check){
      frm.set_value('tinnel_details', '');
    }
  },
  rectal_check: function(frm){
    if(frm.doc.rectal_check){
      frm.set_value('re_others', 0);
      frm.set_value('enlarged_prostate', 0);
      frm.set_value('rectal_hemorrhoid', '');
      frm.set_value('rectal_hemorrhoid', '');
      frm.set_value('rectal_others', '');
    }
  }
});

frappe.ui.form.on('Doctor Examination Selective Result',{
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = (row.result_check === row.normal_value) ? 1 : 0;
    frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = (row.result_check === row.mandatory_value) ? 1 : 0;
		frm.refresh_field('result');
	}
})

frappe.ui.form.on('Other Dental',{
	other(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    frm.refresh_field('other_dental');
    setTimeout(()=>{
      frappe.db
      .get_value('Other Dental Option', row.other, 'selections')
      .then(opt=> {
        const options = opt.message.selections.split('\n');
        frappe.meta.get_docfield(cdt, 'selective_value', cdn).options = opt.message.selections.split('\n');
        frm.fields_dict['other_dental'].grid.update_docfield_property('selective_value', 'options', options);
        frm.refresh_field('other_dental');
      })
    }, 500)
	}
})

frappe.ui.form.on('Doctor Examination Result',{
	result_value(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
    apply_cell_styling (frm, row);
    frm._show_dialog_on_change = true;
	}
})

const apply_cell_styling = (frm, row) => {
  if (row.result_value && row.min_value && row.max_value) {
    let resultValue = parseFloat(row.result_value);
    let minValue = parseFloat(row.min_value);
    let maxValue = parseFloat(row.max_value);
    let $row = $(frm.fields_dict["non_selective_result"].grid.grid_rows_by_docname[row.name].row);
    if (resultValue < minValue || resultValue > maxValue) {
      $row.css({
        'font-weight': 'bold',
        'color': 'red'
      });
    } else {
      $row.css({
        'font-weight': 'normal',
        'color': 'black'
      });
    }
  }
}

const handleQuestionnaire = (frm) => {
  const grid = frm.fields_dict['questionnaire'].grid;
  const buttons = [
    {label: 'Create', class: 'btn-primary', statuses: 'Started', status: 'Completed', prompt: false},
    {label: 'Approve', class: 'btn-info', statuses: 'Completed,Pending', status: 'Approved', prompt: false},
    {label: 'Reject', class: 'btn-danger', statuses: 'Completed,Pending', status: 'Rejected', prompt: true},
    {label: 'Pending', class: 'btn-warning', statuses: 'Completed', status: 'Pending', prompt: false},
  ];
  grid.wrapper.find('.grid-footer').find('.btn-custom').hide();
  buttons.forEach(button=>{
    const customButton = grid.add_custom_button(__(button.label), function() {
      if (button.prompt){
        frappe.prompt({
          fieldname: 'reason',
          label: 'Reason',
          fieldtype: 'Small Text',
          reqd: 1
        }, (values) => {
          updateQChildStatus(frm, grid, button.status, values.reason);
        }, __('Provide a Reason'), __('Submit'))
      } else {
        updateQChildStatus(frm, grid, button.status, null);
      }
    }, 'btn-custom');
    customButton.removeClass("btn-default btn-secondary").addClass(`${button.class} btn-sm`).attr('data-statuses', button.statuses);
    customButton.hide();
  });
  setupQRowSelector(grid);
}

const updateQChildStatus = (frm, grid, newStatus, reason) => {
  const selectedRows = grid.get_selected();
  if (selectedRows.length !== 1) return;
  const child = locals[grid.doctype][selectedRows[0]];
  if (newStatus === 'Completed') {
    window.open(`https://kyomedic.vercel.app/questionnaire?template=${child.template}&appt=${frm.doc.appointment}`, '_blank');
  } else {
    frappe.call({
      method: 'kms.mcu_dispatcher.set_status_from_questionnaire',
      freeze: true,
      freeze_message: 'Getting Queue',
      args: { 
        name: child.questionnaire, 
        status: newStatus,
        doctype: frm.doctype,
        docname: frm.doc.name,
        reason: reason
       },
      callback: (r) => {
        frm.reload_doc()
      },
      error: (err) => { frappe.msgprint(err) }
    })
  }
};

const setupQRowSelector = (grid) => {
  grid.row_selector = function (e) {
    if (e.target.classList.contains('grid-row-check')) {
      const $row = $(e.target).closest('.grid-row');
      const docname = $row.attr('data-name');
      if (this.selected_row && this.selected_row === docname) {
        $row.removeClass('grid-row-selected');
        $row.find('.grid-row-check').prop('checked', false);
        this.selected_row = null;
      } else {
        this.$rows.removeClass('grid-row-selected');
        this.$rows.find('.grid-row-check').prop('checked', false);
        $row.addClass('grid-row-selected');
        $row.find('.grid-row-check').prop('checked', true);
        this.selected_row = docname;
      }
      this.refresh_remove_rows_button();
      updateQCustomButtonVisibility(grid);
    }
  };
  grid.wrapper.on('click', '.grid-row', function () {
    updateQCustomButtonVisibility(grid);
  });
};

const updateQCustomButtonVisibility = (grid) => {
  const selectedRows = grid.get_selected();
  const buttons = grid.wrapper.find('.grid-footer').find('.btn-custom');
  if (selectedRows && selectedRows.length === 1) {
    const child = locals[grid.doctype][selectedRows[0]];
    buttons.each((index, button) => {
      const $button = $(button);
      const buttonStatuses = $button.data('statuses');
      if (buttonStatuses) {
        const statuses = buttonStatuses.split(',');
        $button.toggle(statuses.includes(child.status));
      } else {
        $button.toggle(child.status === 'Started');
      }
    });
  } else {
    buttons.hide();
  }
}
