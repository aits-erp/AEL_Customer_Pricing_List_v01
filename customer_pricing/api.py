import frappe


# ============================================================
# MAIN BACKEND PRICING (Runs on Sales Order Save)
# ============================================================

def apply_customer_pricing(doc, method):

    if not doc.customer:
        return

    # Manual mode (header level)
    if doc.custom_ignore_gross_weight_pricing and doc.custom_ignore_customer_pricing:
        return

    selected_country = doc.custom_countrypl
    total_cbm = doc.custom_totals_in_cbm or 0
    gross_weight = doc.custom_gross_weight or 0

    # --------------------------------------------------------
    # GET GROSS WEIGHT RATES
    # --------------------------------------------------------
    gross_rates = {}

    if not doc.custom_ignore_gross_weight_pricing and gross_weight:

        gross_docs = frappe.get_all(
            "Gross Weight",
            filters={"customer": doc.customer},
            fields=["name"]
        )

        if gross_docs:

            for g in gross_docs:   # ✅ loop all entries

                gross_doc = frappe.get_doc("Gross Weight", g.name)

                for row in gross_doc.table_dcbl:

                    if float(row.gross_weight or 0) == float(gross_weight):
                        gross_rates[row.item] = row.final_rate or 0

    # --------------------------------------------------------
    # GET CUSTOMER PRICE LIST
    # --------------------------------------------------------
    pricing_data = []

    if not doc.custom_ignore_customer_pricing and selected_country:

        masters = frappe.get_all(
            "Customer Pricing List",
            filters={"customer": doc.customer},
            fields=["name"]
        )

        for master in masters:

            master_doc = frappe.get_doc(
                "Customer Pricing List",
                master.name
            )

            for row in master_doc.price_details:

                if row.country == selected_country:
                    pricing_data.append(row)

    # --------------------------------------------------------
    # APPLY PRICING
    # --------------------------------------------------------
    for item_row in doc.items:

        if not item_row.item_code:
            continue

        # 🔴 ITEM LEVEL MANUAL MODE
        if item_row.custom_ignore_pricing:
            continue

        found = False
        rate = item_row.rate   # keep manual rate

        # 1️⃣ Gross Weight
        if item_row.item_code in gross_rates:

            rate = gross_rates[item_row.item_code]
            found = True

        # 2️⃣ Customer Price List
        else:

            for price_row in pricing_data:

                if price_row.item == item_row.item_code:

                    if price_row.calculation_type == "Fixed":
                        rate = price_row.fixed_rate or 0

                    elif price_row.calculation_type == "Per CBM":

                        if total_cbm <= 1:
                            rate = price_row.usd_min_cbm or 0
                        else:
                            rate = (
                                (price_row.usd_per_cbm or 0) * total_cbm
                            )

                    found = True
                    break

        # Only overwrite if rule found
        if found:
            item_row.custom_custom_rate = rate
            item_row.rate = rate

    doc.calculate_taxes_and_totals()


# ============================================================
# REAL-TIME CUSTOMER PRICE LIST (Frontend)
# ============================================================

@frappe.whitelist()
def get_pricing_data(customer, country):

    masters = frappe.get_all(
        "Customer Pricing List",
        filters={"customer": customer},
        fields=["name"]
    )

    result = []

    for master in masters:

        master_doc = frappe.get_doc(
            "Customer Pricing List",
            master.name
        )

        for row in master_doc.price_details:

            if row.country == country:

                result.append({
                    "item": row.item,
                    "calculation_type": row.calculation_type,
                    "fixed_rate": row.fixed_rate,
                    "usd_per_cbm": row.usd_per_cbm,
                    "usd_min_cbm": row.usd_min_cbm
                })

    return result


# ============================================================
# REAL-TIME GROSS WEIGHT (Frontend)
# ============================================================

@frappe.whitelist()
def get_gross_weight_rates(customer, gross_weight):

    if not customer:
        return {}

    try:
        gross_weight = float(gross_weight)
    except:
        return {}

    gross_docs = frappe.get_all(
        "Gross Weight",
        filters={"customer": customer},
        fields=["name"],
        limit=1
    )

    if not gross_docs:
        return {}

    gross_doc = frappe.get_doc(
        "Gross Weight",
        gross_docs[0].name
    )

    result = {}

    for row in gross_doc.table_dcbl:

        if float(row.gross_weight or 0) == gross_weight:
            result[row.item] = row.final_rate or 0

    return result