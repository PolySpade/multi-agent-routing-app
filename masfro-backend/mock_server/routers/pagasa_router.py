"""
PAGASA mock endpoints.

Serves HTML that matches the real PAGASA website structure so that
RiverScraperService (Selenium) and DamWaterScraperService (BS4 + pandas)
can scrape it with zero logic changes.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..data_store import get_data_store

router = APIRouter()


@router.get("/pagasa/water/map.do", response_class=HTMLResponse)
async def river_water_levels(request: Request):
    """
    Serves river level data as HTML table matching PAGASA structure.
    Selector: table.table-type1 tbody#tblList
    Used by: RiverScraperService (Selenium + pandas.read_html)
    """
    store = get_data_store()
    stations = store.get_river_stations()

    rows = ""
    for s in stations:
        wl = s.get("water_level_m", "")
        al = s.get("alert_level_m", "")
        am = s.get("alarm_level_m", "")
        cl = s.get("critical_level_m", "")
        rows += f"""<tr>
            <td>{s.get('station_name', '')}</td>
            <td>{wl}</td>
            <td>{al}</td>
            <td>{am}</td>
            <td>{cl}</td>
        </tr>\n"""

    html = f"""<!DOCTYPE html>
<html>
<head><title>PAGASA Flood Forecasting</title></head>
<body>
<table class="table-type1">
    <thead>
        <tr>
            <th>Station</th>
            <th>Current [EL.m]</th>
            <th>Alert [EL.m]</th>
            <th>Alarm [EL.m]</th>
            <th>Critical [EL.m]</th>
        </tr>
    </thead>
    <tbody id="tblList">
        {rows}
    </tbody>
</table>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/pagasa/flood", response_class=HTMLResponse)
async def dam_water_levels_and_advisories(request: Request):
    """
    Serves dam water level data as HTML table matching PAGASA structure.
    Selector: table.dam-table (with header=1 for pandas)
    Also includes advisory links for AdvisoryScraperService.discover_pagasa_advisories()
    Used by: DamWaterScraperService (requests + BS4 + pandas.read_html)
    """
    store = get_data_store()
    dams = store.get_dam_levels()
    advisories = store.get_advisories()

    # Build dam table rows - 4 rows per dam (Latest Time, Latest Date, Previous Time, Previous Date)
    dam_rows = ""
    for d in dams:
        dam_name = d.get("dam_name", "UNKNOWN")
        latest_rwl = d.get("latest_rwl", "")
        dev_nhwl = d.get("dev_nhwl", "")
        rule_curve = d.get("rule_curve", "")
        dev_rule_curve = d.get("dev_rule_curve", "")
        previous_rwl = d.get("previous_rwl", "")
        nhwl = d.get("nhwl", "")
        wl_dev_hr = d.get("wl_dev_hr", "")
        wl_dev_amt = d.get("wl_dev_amt", "")
        latest_time = d.get("latest_time", "06:00")
        latest_date = d.get("latest_date", "Feb 08, 2026")
        prev_time = d.get("previous_time", "18:00")
        prev_date = d.get("previous_date", "Feb 07, 2026")

        # Row 1: Latest Time
        dam_rows += f"""<tr>
            <td rowspan="4">{dam_name}</td>
            <td>{latest_time}</td>
            <td>{latest_rwl}</td>
            <td>{dev_nhwl}</td>
            <td>{rule_curve}</td>
            <td>{dev_rule_curve}</td>
            <td rowspan="4">{wl_dev_hr}</td>
            <td rowspan="4">{wl_dev_amt}</td>
            <td rowspan="4">{nhwl}</td>
        </tr>\n"""
        # Row 2: Latest Date
        dam_rows += f"""<tr>
            <td>{latest_date}</td>
            <td>{latest_rwl}</td>
            <td>{dev_nhwl}</td>
            <td>{rule_curve}</td>
            <td>{dev_rule_curve}</td>
        </tr>\n"""
        # Row 3: Previous Time
        dam_rows += f"""<tr>
            <td>{prev_time}</td>
            <td>{previous_rwl}</td>
            <td>{dev_nhwl}</td>
            <td>{rule_curve}</td>
            <td>{dev_rule_curve}</td>
        </tr>\n"""
        # Row 4: Previous Date
        dam_rows += f"""<tr>
            <td>{prev_date}</td>
            <td>{previous_rwl}</td>
            <td>{dev_nhwl}</td>
            <td>{rule_curve}</td>
            <td>{dev_rule_curve}</td>
        </tr>\n"""

    # Build advisory links
    advisory_links = ""
    for adv in advisories:
        title = adv.get("title", "Flood Advisory")
        link = adv.get("link", "#")
        advisory_links += f'<a href="{link}">{title}</a><br>\n'

    html = f"""<!DOCTYPE html>
<html>
<head><title>PAGASA Flood Monitoring</title></head>
<body>
<h2>Dam Water Levels</h2>
<table class="dam-table">
    <thead>
        <tr>
            <th rowspan="2">Dam Name</th>
            <th rowspan="2">Observation Time &amp; Date</th>
            <th colspan="4">Water Level Data</th>
            <th colspan="2">Water Level Deviation</th>
            <th rowspan="2">Normal High Water Level (NHWL) (m)</th>
        </tr>
        <tr>
            <th>Reservoir Water Level (RWL) (m)</th>
            <th>Deviation from NHWL (m)</th>
            <th>Rule Curve Elevation (m)</th>
            <th>Deviation from Rule Curve (m)</th>
            <th>Hr</th>
            <th>Amount</th>
        </tr>
    </thead>
    <tbody>
        {dam_rows}
    </tbody>
</table>

<h2>Active Advisories</h2>
<div class="advisory-links">
    {advisory_links}
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/pagasa/advisory/{advisory_id}", response_class=HTMLResponse)
async def advisory_detail(advisory_id: int):
    """
    Serves individual advisory content page.
    Used by: FloodAgent.collect_and_parse_advisories() -> _scrape_webpage()
    """
    store = get_data_store()
    advisories = store.get_advisories()

    advisory = None
    for adv in advisories:
        if adv.get("id") == advisory_id:
            advisory = adv
            break

    if not advisory:
        return HTMLResponse(content="<html><body><p>Advisory not found</p></body></html>", status_code=404)

    html = f"""<!DOCTYPE html>
<html>
<head><title>{advisory.get('title', 'Advisory')}</title></head>
<body>
<h1>{advisory.get('title', 'Advisory')}</h1>
<div class="advisory-content">
    <p>{advisory.get('text', '')}</p>
</div>
<p class="pub-date">Published: {advisory.get('pub_date', '')}</p>
</body>
</html>"""
    return HTMLResponse(content=html)
