frappe.ui.form.on("Sales Order", {

    customer: function(frm) {
        update_rates(frm);
    },

    custom_gross_weight: function(frm) {
        update_rates(frm);
    },

    custom_countrypl: function(frm) {
        update_rates(frm);
    },

    custom_totals_in_cbm: function(frm) {
        update_rates(frm);
    },

    custom_ignore_gross_weight_pricing: function(frm) {
        update_rates(frm);
    },

    custom_ignore_customer_pricing: function(frm) {
        update_rates(frm);
    }
});


frappe.ui.form.on("Sales Order Item", {

    item_code: function(frm) {
        update_rates(frm);
    },

    qty: function(frm) {
        frm.trigger("calculate_taxes_and_totals");
    },

    custom_ignore_pricing: function(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        // If unchecked → recalc
        if (!row.custom_ignore_pricing) {
            update_rates(frm);
        }
    }
});


function update_rates(frm) {

    if (!frm.doc.customer) {
        return;
    }

    // Header manual mode
    if (frm.doc.custom_ignore_gross_weight_pricing &&
        frm.doc.custom_ignore_customer_pricing) {
        return;
    }

    let gross_weight = parseFloat(frm.doc.custom_gross_weight) || 0;
    let total_cbm = frm.doc.custom_totals_in_cbm || 0;

    let gross_promise = Promise.resolve({message: {}});
    let pricing_promise = Promise.resolve({message: []});

    // Gross API
    if (!frm.doc.custom_ignore_gross_weight_pricing && gross_weight) {
        gross_promise = frappe.call({
            method: "customer_pricing.api.get_gross_weight_rates",
            args: {
                customer: frm.doc.customer,
                gross_weight: gross_weight
            }
        });
    }

    // Customer Pricing API
    if (!frm.doc.custom_ignore_customer_pricing &&
        frm.doc.custom_countrypl) {

        pricing_promise = frappe.call({
            method: "customer_pricing.api.get_pricing_data",
            args: {
                customer: frm.doc.customer,
                country: frm.doc.custom_countrypl
            }
        });
    }

    Promise.all([gross_promise, pricing_promise])
    .then(function(results) {

        let gross_rates = results[0].message || {};
        let pricing = results[1].message || [];

        frm.doc.items.forEach(function(row) {

            // 🔴 ITEM LEVEL MANUAL MODE
            if (row.custom_ignore_pricing) {
                return;
            }

            let found = false;
            let rate = row.rate;

            // Gross Weight
            if (!frm.doc.custom_ignore_gross_weight_pricing &&
                gross_rates[row.item_code]) {

                rate = gross_rates[row.item_code];
                found = true;
            }

            // Customer Pricing
            else if (!frm.doc.custom_ignore_customer_pricing) {

                pricing.forEach(function(price_row) {

                    if (price_row.item === row.item_code) {

                        found = true;

                        if (price_row.calculation_type === "Fixed") {
                            rate = price_row.fixed_rate || 0;
                        }

                        else if (price_row.calculation_type === "Per CBM") {

                            if (total_cbm <= 1) {
                                rate = price_row.usd_min_cbm || 0;
                            } else {
                                rate = (price_row.usd_per_cbm || 0) * total_cbm;
                            }
                        }
                    }
                });
            }

            if (found) {

                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    "rate",
                    rate
                );
            }
        });

        frm.trigger("calculate_taxes_and_totals");
    });
}