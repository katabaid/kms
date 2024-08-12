const customBeforeSubmit = (frm) => {
  console.log('Custom before_submit logic for Doctor Examination');
  if (frm.doc.some_field === 'some_value') {
    frappe.throw('Cannot submit when some_field is some_value');
  } else {
    doctorExaminationController.utils.handleBeforeSubmit(frm);
  }
};

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
    //TODO: Add for Dental Section
    doctorExaminationController.refresh(frm);
    const sectionsToHide = [
      'eyes_section', 'ear_section', 'nose_section', 'throat_section', 'neck_section', 
      'cardiac_section', 'breast_section', 'resp_section', 'abd_section', 'spine_section', 
      'genit_section', 'neuro_section', 'visual_field_test_section', 'romberg_test_section', 'tinnel_test_section',
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
          console.log(item)
          if (item.field === 'physical_examination_name') sectionsToHide.slice(0, 12).forEach(section => frm.set_df_property(section, 'hidden', 0));
          if (item.field === 'visual_field_test_name') frm.set_df_property('visual_field_test_section', 'hidden', 0);
          if (item.field === 'romberg_test_name') frm.set_df_property('romberg_test_section', 'hidden', 0);
          if (item.field === 'tinnel_test_name') frm.set_df_property('tinnel_test_section', 'hidden', 0);
          if (item.field === 'phallen_test_name') frm.set_df_property('phallen_test_section', 'hidden', 0);
          if (item.field === 'rectal_test_name') frm.set_df_property('rectal_examination_section', 'hidden', 0);
        });
      }
    }
  }
});
