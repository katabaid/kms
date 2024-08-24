const customBeforeSubmit = (frm) => {
  console.log('Custom before_submit logic for Doctor Examination');
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
    'genit_section', 'neuro_section', 'dental_section', 'teeth_section', 
    'visual_field_test_section', 'romberg_test_section', 'tinnel_test_section',
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
        if (item.field === 'physical_examination_name') sectionsToHide.slice(0, 12).forEach(section => frm.set_df_property(section, 'hidden', 0));
        if (item.field === 'visual_field_test_name') frm.set_df_property('visual_field_test_section', 'hidden', 0);
        if (item.field === 'romberg_test_name') frm.set_df_property('romberg_test_section', 'hidden', 0);
        if (item.field === 'tinnel_test_name') frm.set_df_property('tinnel_test_section', 'hidden', 0);
        if (item.field === 'phallen_test_name') frm.set_df_property('phallen_test_section', 'hidden', 0);
        if (item.field === 'rectal_test_name') frm.set_df_property('rectal_examination_section', 'hidden', 0);
        if (item.field === 'dental_examination_name') sectionsToHide.slice(12, 14).forEach(section => frm.set_df_property(section, 'hidden', 0));
      });
    }
  }
}

const handleDentalSections = (frm) => {
  prepareDentalSections(frm);
  prepareStaticDental(frm);
  prepareOtherDentalOptions(frm);
}

const handleVitalSign = (frm) => {
  if (frm.doc.appointment) {
    frappe.call({
      method: 'kms.healthcare.get_vital_sign_for_doctor_examination',
      args: {
        docname: frm.doc.name
      },
      callback: (r) => {
        if (r.message) {
          const data = r.message.map(entry => [entry.label, entry.result]);
          const columns = [
            {
              name: "label",      id: "label",      content: `${__("Label")}`,
              editable: false,    sortable: false,  focusable: false,
              dropdown: false,    align: "left",    width: 200,
            },
            {
              name: "result",     id: "result",     content: `${__("Result")}`,
              editable: false,    sortable: false,  focusable: false,
              dropdown: false,    align: "right",   width: 350,
            },
          ];
          if (!frm.vital_sign_datatable) {
            const datatable_options = {
              columns,
              data,
              inlineFilters: false,
              noDataMessage: __("No Data"),
              disableReorderColumn: true
            }
            frm.vital_sign_datatable = new frappe.DataTable('#vital_sign_html', datatable_options);
          } else {
            frm.vital_sign_datatable.refresh(data, columns);
          }
        }
      }
    })
  }
}

const prepareDentalSections = (frm) => {
  const referenceArray = ['missing', 'filling', 'radix', 'abrasion', 'crown', 'veneer', 'persistent', 'abscess', 'impaction', 'caries', 'fracture', 'mob', 'bridge', 'rg', 'exfolia', 'fistula'];

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
  const $wrapper = frm.get_field('dental_detail_html').$wrapper;
  const detail_wrapper = $(`<div class="detail_wrapper">`).appendTo($wrapper);
  const newdata = transform(frm.doc.dental_detail);
  const data = reverseLastHalf(newdata);

  const columns = [
    {
      name: 'l_perm',
      id: 'l_perm',
      content: `${__("Pos")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 50,
    },
    {
      name: 'l_opt_perm',
      id: 'l_opt_perm',
      content: `${__("Opt")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 250,
      format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
    },
    {
      name: 'l_prim',
      id: 'l_prim',
      content: `${__("Pos")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 50,
    },
    {
      name: 'l_opt_prim',
      id: 'l_opt_prim',
      content: `${__("Opt")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 250,
      format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
    },
    {
      name: 'r_opt_prim',
      id: 'r_opt_prim',
      content: `${__("Opt")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 250,
      format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
    },
    {
      name: 'r_prim',
      id: 'r_prim',
      content: `${__("Pos")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 50,
    },
    {
      name: 'r_opt_perm',
      id: 'r_opt_perm',
      content: `${__("Opt")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 250,
      format: (value) => `<div style="white-space: normal; word-wrap: break-word; line-height: 1;">${value}</div>`
    },
    {
      name: 'r_perm',
      id: 'r_perm',
      content: `${__("Pos")}`,
      editable: false,
      sortable: false,
      focusable: false,
      dropdown: false,
      align: 'left',
      width: 50,
    },
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
  frm.fields_dict['other_dental'].grid.grid_rows.forEach(row => {
    if (row.doc.other) {
      frappe.db
      .get_doc('Other Dental Option', row.doc.other)
      .then(doc => {
        if (doc && doc.selections) {
          frappe.model.set_value(row.doctype, row.name, 'selective_value', '');
          frm.fields_dict['other_dental'].grid.update_docfield_property('selective_value', 'options', doc.selections.split('\n'));
          frm.fields_dict['other_dental'].grid.refresh();
          //row.fields_dict.selective_value.df.options = doc.selections.split('\n');
        }
      });
    } else {
      frappe.model.set_value(row.doctype, row.name, 'selective_value', '');
      frm.fields_dict['other_dental'].grid.update_docfield_property('selective_value', 'options', []);
      frm.fields_dict['other_dental'].grid.refresh();
    }
  });
}

// Use the common controller with custom before_submit function for Doctor Examination
const doctorExaminationController = kms.controller.createDocTypeController('Doctor Examination', {
  before_submit: customBeforeSubmit,
});
let mcu_settings = [];

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
    handleVitalSign(frm)
  },

  setup: function (frm) {
		if(frm.doc.result&&frm.doc.docstatus===0){
			frm.refresh_field('result');
      $.each(frm.doc.result, (key, value) => {
				frm.fields_dict.result.grid.grid_rows[key].docfields[3].options=frm.fields_dict.result.get_value()[key].result_options;
				if (value.result_check !== value.normal_value) {
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].read_only = 0;
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].reqd = 1;
				} else {
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].read_only = 1;
					frm.fields_dict.result.grid.grid_rows[key].docfields[4].reqd = 0;
				}
      });
      frm.refresh_field('result');
    }
	}
});

frappe.ui.form.on('Doctor Examination Selective Result',{
	result_check(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.result_check !== row.normal_value) {
			frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = 0;
			frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = 1;
		} else {
			frappe.meta.get_docfield(cdt, 'result_text', cdn).read_only = 1;
			frappe.meta.get_docfield(cdt, 'result_text', cdn).reqd = 0;
		}
		frm.refresh_field('result');
	}
})