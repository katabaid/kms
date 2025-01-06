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
    'teeth_section', 'visual_field_test_section', 'romberg_test_section', 'tinnel_test_section',
    'phallen_test_section', 'rectal_examination_section'
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
        if (item.field === 'dental_examination_name') sectionsToHide.slice(14, 16).forEach(section => frm.set_df_property(section, 'hidden', 0));
      });
    }
  }
}

const handleDentalSections = (frm) => {
  prepareDentalSections(frm);
  prepareStaticDental(frm);
  prepareOtherDentalOptions(frm);
}

const prepareDentalSections = (frm) => {
  const referenceArray = [
    'missing', 'filling', 'radix', 'abrasion', 'crown', 'veneer', 'persistent', 'abscess', 'impaction', 
    'caries', 'fracture', 'mob', 'bridge', 'rg', 'exfolia', 'fistula'
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
          return selected_array.map((option) => {
            return {
              label: option.key === 'rg' ? 'Regressive Gingivitis' : option.key.toLowerCase().replace(/\b\w/g, s => s.toUpperCase()),
              value: option.key,
              checked: option.value,
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
      $.each (frm.doc.other_dental, (key, value) => {
        frappe.db
        .get_value('Other Dental Option', value.other, 'selections')
        .then(opt=> {
          frappe.meta.get_docfield('Other Dental', 'selective_value', value.name).options = opt.message.selections.split('\n')
        })
      })
    }
  }
}

const addSidebarUserAction = (frm) => {
  frm.add_custom_button(
    __('Patient Result'),
    () => {
      frappe.route_options = { exam_id: frm.doc.appointment };
      frappe.set_route('query-report', 'Result per Appointment');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('Vital Sign'),
    () => {
      frappe.route_options = { exam_id: frm.doc.appointment };
      frappe.set_route('query-report', 'Vital SIgn and Anthropometry');
    },
    __('Reports')
  ),
  frm.add_custom_button(
    __('History'),
    () => {
      frappe.route_options = { exam_id: frm.doc.appointment, room: frm.doc.service_unit };
      frappe.set_route('query-report', 'Doctor Examination History');
    },
    __('Reports')
  )
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
  const dent_fields = ['extra_oral','intra_oral','dental_detail','other_dental'];
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
      if (exam === 'dental_examination_name') dent_fields.forEach(section => frm.set_df_property(section, 'read_only', 1));
    })
};

// Use the common controller with custom before_submit function for Doctor Examination
const doctorExaminationController = kms.controller.createDocTypeController('Doctor Examination', {
  before_submit: customBeforeSubmit,
});
let mcu_settings = [];
let normal_values = true;

// Attach the custom controller to the Doctor Examination doctype
frappe.ui.form.on('Doctor Examination', {
  ...doctorExaminationController,
  before_submit: function (frm) {
    doctorExaminationController.config.before_submit(frm);
  },

  before_load: function (frm) {
    frappe.call({
      method: 'kms.healthcare.get_mcu_settings',
      callback: (r) => { if (r.message) mcu_settings = r.message; }
    })
  },

  refresh: function (frm) {
    doctorExaminationController.refresh(frm);
    handleTabVisibility(frm);
    handleDentalSections(frm);
    addSidebarUserAction(frm);
    handleReadOnlyExams(frm);
		if (frm.doc.non_selective_result) {
			frm.refresh_field('non_selective_result');
			frm.fields_dict['non_selective_result'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc);
			})
		}
    frm.sidebar
      .add_user_action(__('All Questionnaires'))
      .attr('href', `/app/questionnaire?patient_appointment=${frm.doc.appointment}`)
      .attr('target', '_blank');
    if (frm.doc.questionnaire) {
			frm.refresh_field('questionnaire');
			$.each(frm.doc.questionnaire, (key, value) => {
				if (!value.is_completed) {
					const link = `https://kmsregis.netlify.app/questionnaire?template=${value.template}&appointment_id=${frm.doc.appointment}`;
					frm.sidebar.add_user_action(__(value.template)).attr('href', link).attr('target', '_blank');
				}
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
    frappe.db
    .get_value('Other Dental Option', row.other, 'selections')
    .then(opt=> {
      frappe.meta.get_docfield(cdt, 'selective_value', cdn).options = opt.message.selections.split('\n')
      frm.refresh_field('other_dental');
    })
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