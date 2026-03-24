frappe.ui.form.on("Gross Weight Table", {

    expected_rate: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    percentage: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    }
});

function calculate_row(frm, cdt, cdn) {

    let row = locals[cdt][cdn];

    let expected = parseFloat(row.expected_rate) || 0;
    let percentage = parseFloat(row.percentage) || 0;

    row.final_rate = expected * (percentage / 100);

    frm.refresh_field("table_dcbl");
}