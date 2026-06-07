def build_summary(rows):
    print("-> Tinh KPI summary...")
    from collections import defaultdict

    by_month   = defaultdict(lambda: {"revenue":0,"listed":0,"discount":0,"orders":set(),"partners":set()})
    by_partner_month = defaultdict(lambda: defaultdict(lambda: {"revenue":0,"listed":0,"orders":set()}))
    by_group   = defaultdict(lambda: {"revenue":0,"listed":0,"count":0})
    by_lab     = defaultdict(lambda: {"revenue":0,"listed":0})

    for r in rows:
        try:
            rev  = float(r.get("revenue_actual") or 0)
            lst  = float(r.get("price") or 0)
            disc = float(r.get("discount_amount") or 0)
            mo   = str(r.get("source_month",""))
            pid  = str(r.get("partnerId",""))
            pname= str(r.get("partnerCode",""))
            oid  = str(r.get("orderId",""))
            grp  = str(r.get("orderTypeGroupName","Khac"))
            lab  = str(r.get("labName","")) or str(r.get("labId",""))

            by_month[mo]["revenue"]  += rev
            by_month[mo]["listed"]   += lst
            by_month[mo]["discount"] += disc
            by_month[mo]["orders"].add(oid)
            by_month[mo]["partners"].add(pid)

            by_partner_month[pid][mo]["revenue"] += rev
            by_partner_month[pid][mo]["listed"]  += lst
            by_partner_month[pid][mo]["orders"].add(oid)
            if not by_partner_month[pid].get("code"):
                by_partner_month[pid]["code"] = pname

            by_group[grp]["revenue"] += rev
            by_group[grp]["listed"]  += lst
            by_group[grp]["count"]   += 1

            by_lab[lab]["revenue"]   += rev
            by_lab[lab]["listed"]    += lst
        except:
            pass

    monthly = []
    sorted_months = sorted(by_month.keys())
    for mo in sorted_months:
        d = by_month[mo]
        monthly.append({
            "month"          : mo,
            "revenue_actual" : round(d["revenue"]),
            "revenue_listed" : round(d["listed"]),
            "discount"       : round(d["discount"]),
            "discount_pct"   : round(d["discount"]/d["listed"]*100,1) if d["listed"] else 0,
            "order_count"    : len(d["orders"]),
            "active_partners": len(d["partners"]),
        })

    mom = None
    if len(monthly) >= 2:
        curr = monthly[-1]["revenue_actual"]
        prev = monthly[-2]["revenue_actual"]
        mom  = round((curr - prev) / prev * 100, 1) if prev else None

    # Top partners theo tháng hiện tại
    cur_month = sorted_months[-1] if sorted_months else ""
    top_partners = []
    for pid, mdata in by_partner_month.items():
        if cur_month in mdata and isinstance(mdata[cur_month], dict):
            d = mdata[cur_month]
            top_partners.append({
                "partnerId"  : pid,
                "partnerCode": mdata.get("code",""),
                "revenue"    : round(d["revenue"]),
                "listed"     : round(d["listed"]),
                "orders"     : len(d["orders"]),
            })
    top_partners = sorted(top_partners, key=lambda x: -x["revenue"])[:20]

    service_mix = sorted(
        [{"group":k,"revenue":round(v["revenue"]),"listed":round(v["listed"]),"count":v["count"]}
         for k,v in by_group.items()],
        key=lambda x: -x["revenue"]
    )

    lab_breakdown = sorted(
        [{"lab":k if k else "Không xác định","revenue":round(v["revenue"]),"listed":round(v["listed"])}
         for k,v in by_lab.items()],
        key=lambda x: -x["revenue"]
    )

    cur = monthly[-1] if monthly else {}
    return {
        "updated_at"       : datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_vn"    : datetime.utcnow().strftime("%H:%M %d/%m/%Y") + " UTC",
        "current_month"    : cur_month,
        "total_revenue"    : cur.get("revenue_actual", 0),
        "total_listed"     : cur.get("revenue_listed", 0),
        "total_discount"   : cur.get("discount", 0),
        "discount_pct"     : cur.get("discount_pct", 0),
        "total_orders"     : cur.get("order_count", 0),
        "active_partners"  : cur.get("active_partners", 0),
        "mom_growth_pct"   : mom,
        "monthly"          : monthly,
        "top_partners"     : top_partners,
        "service_mix"      : service_mix,
        "lab_breakdown"    : lab_breakdown,
    }
