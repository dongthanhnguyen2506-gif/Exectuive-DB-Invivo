import os, json, requests, time
from datetime import datetime
from collections import defaultdict
import msal

TENANT_ID     = os.environ["TENANT_ID"]
DATASET_ID    = os.environ["DATASET_ID"]
CLIENT_ID     = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
VERCEL_TOKEN  = os.environ.get("VERCEL_TOKEN", "")
BLOB_RW_TOKEN = os.environ.get("BLOB_RW_TOKEN", "")

TABLES = ["2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04"]

def get_token():
    print("-> Lay Access Token...")
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(
        scopes=["https://analysis.windows.net/powerbi/api/.default"]
    )
    if "access_token" in result:
        print("  OK Token")
        return result["access_token"]
    raise Exception(result.get("error_description"))

def run_dax(token, dax):
    r = requests.post(
        f"https://api.powerbi.com/v1.0/myorg/groups/4d3d0ce8-09e0-4b64-ba8a-feb7f688e8e3/datasets/{DATASET_ID}/executeQueries",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    )
    r.raise_for_status()
    return r.json()["results"][0]["tables"][0]["rows"]

def clean_row(row):
    return {k.split("[")[-1].rstrip("]"): v for k, v in row.items()}

def export_tables(token):
    print("-> Export data...")
    all_rows = []
    for tbl in TABLES:
        try:
            rows = run_dax(token, f"""
                EVALUATE
                ADDCOLUMNS(
                    '{tbl}',
                    "source_month", "{tbl}",
                    "revenue_actual", '{tbl}'[price] * (1 - '{tbl}'[discountPercent] / 100),
                    "discount_amount", '{tbl}'[price] * ('{tbl}'[discountPercent] / 100)
                )
            """)
            all_rows.extend([clean_row(r) for r in rows])
            print(f"  OK {tbl}: {len(rows)} dong")
        except Exception as e:
            print(f"  LOI {tbl}: {e}")
    return all_rows

def build_summary(rows):
    by_month   = defaultdict(lambda: {"revenue":0,"listed":0,"discount":0,"orders":set(),"partners":set()})
    by_partner = defaultdict(lambda: {"revenue":0,"listed":0,"orders":set(),"name":""})
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
            lab  = str(r.get("labName",""))
            by_month[mo]["revenue"]  += rev
            by_month[mo]["listed"]   += lst
            by_month[mo]["discount"] += disc
            by_month[mo]["orders"].add(oid)
            by_month[mo]["partners"].add(pid)
            by_partner[pid]["revenue"] += rev
            by_partner[pid]["listed"]  += lst
            by_partner[pid]["orders"].add(oid)
            by_partner[pid]["name"]     = pname
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
            "month": mo,
            "revenue_actual": round(d["revenue"]),
            "revenue_listed": round(d["listed"]),
            "discount": round(d["discount"]),
            "order_count": len(d["orders"]),
            "active_partners": len(d["partners"]),
        })

    mom = None
    if len(monthly) >= 2:
        curr = monthly[-1]["revenue_actual"]
        prev = monthly[-2]["revenue_actual"]
        mom = round((curr - prev) / prev * 100, 1) if prev else None

    top_partners = sorted(
        [{"partnerId":k,"partnerCode":v["name"],"revenue":round(v["revenue"]),
          "listed":round(v["listed"]),"orders":len(v["orders"])}
         for k,v in by_partner.items()],
        key=lambda x: -x["revenue"]
    )[:20]

    service_mix = sorted(
        [{"group":k,"revenue":round(v["revenue"]),"listed":round(v["listed"]),"count":v["count"]}
         for k,v in by_group.items()],
        key=lambda x: -x["revenue"]
    )

    lab_breakdown = sorted(
        [{"lab":k,"revenue":round(v["revenue"]),"listed":round(v["listed"])}
         for k,v in by_lab.items()],
        key=lambda x: -x["revenue"]
    )

    cur = monthly[-1] if monthly else {}
    return {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_vn": datetime.utcnow().strftime("%H:%M %d/%m/%Y") + " UTC",
        "current_month": sorted_months[-1] if sorted_months else "",
        "total_revenue": cur.get("revenue_actual", 0),
        "total_listed": cur.get("revenue_listed", 0),
        "total_discount": cur.get("discount", 0),
        "total_orders": cur.get("order_count", 0),
        "active_partners": cur.get("active_partners", 0),
        "mom_growth_pct": mom,
        "monthly": monthly,
        "top_partners": top_partners,
        "service_mix": service_mix,
        "lab_breakdown": lab_breakdown,
    }

def save_files(summary):
    os.makedirs("public", exist_ok=True)
    with open("public/summary_latest.json","w",encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("  OK Saved public/summary_latest.json")

def push_vercel(summary):
    if not VERCEL_TOKEN:
        return
    r = requests.put(
        "https://blob.vercel-storage.com/invivo/summary_latest.json",
        headers={
            "Authorization": f"Bearer {VERCEL_TOKEN}",
            "x-vercel-blob-rw-token": BLOB_RW_TOKEN,
            "Content-Type": "application/json",
        },
        data=json.dumps(summary, ensure_ascii=False)
    )
    if r.status_code in (200, 201):
        print(f"  OK Vercel Blob")
    else:
        print(f"  LOI Vercel {r.status_code}: {r.text[:200]}")

def main():
    t0 = time.time()
    print("="*50)
    print(f"InVivo Export - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*50)
    token   = get_token()
    rows    = export_tables(token)
    summary = build_summary(rows)
    save_files(summary)
    push_vercel(summary)
    print(f"DONE trong {round(time.time()-t0,1)}s")
    print(f"DT thang {summary['current_month']}: {summary['total_revenue']:,.0f} VND")
    print(f"MoM: {summary['mom_growth_pct']}%")

if __name__ == "__main__":
    main()
