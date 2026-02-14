import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re
from datetime import datetime

MONTH_NAMES = [
    'january','february','march','april','may','june',
    'july','august','september','october','november','december',
]

st.set_page_config(
    page_title='The Power Scoreboard',
    page_icon='⚡️', 
    layout='wide',
    menu_items={"About":"This scoreboard was built by Octavi Semonin, all mistakes are his own. You can email him at octavi@gmail.com to complain.",
                "Report a bug":'mailto:octavi@gmail.com'}
)

st.title("⚡️ The Power Scoreboard")
st.write(
    "A handy electricity scoreboard for the United States."
)

@st.cache_data(ttl='1d', show_spinner='Discovering available data...')
def get_available_months():
    """Scrape the EIA-860M page and validate which files actually exist.

    The EIA page lists links for all 12 months of every year, including
    future months that haven't been published yet. Non-existent files
    return text/html instead of a spreadsheet content type, so we probe
    from newest to oldest to find the most recent real file, then include
    everything from that point back.
    """
    base = 'https://www.eia.gov/electricity/data/eia860m/'
    resp = requests.get(base)
    resp.raise_for_status()

    # Match links like xls/december_generator2025.xlsx or archive/xls/january_generator2024.xlsx
    pattern = r'((?:archive/)?xls/(\w+)_generator(\d{4})\.xlsx)'
    matches = re.findall(pattern, resp.text)

    all_entries = []
    seen = set()
    for path, month_name, yr in matches:
        month_name = month_name.lower()
        if month_name not in MONTH_NAMES:
            continue
        month_num = MONTH_NAMES.index(month_name) + 1
        sort_key = f"{yr}-{month_num:02d}"
        if sort_key in seen:
            continue
        seen.add(sort_key)
        all_entries.append({
            'year': yr,
            'month': month_name,
            'month_num': month_num,
            'label': f"{yr}-{month_name.capitalize()}",
            'sort_key': sort_key,
            'url': base + path,
        })

    all_entries.sort(key=lambda x: x['sort_key'], reverse=True)

    # Pre-filter: skip months after the current calendar month (can't exist yet)
    today = datetime.now()
    cutoff = f"{today.year}-{today.month:02d}"
    candidates = [e for e in all_entries if e['sort_key'] <= cutoff]

    # Probe from newest to find the first file that actually exists.
    # Non-existent files on the EIA site return 200 with text/html;
    # real files return a spreadsheet content type.
    validated = []
    found_latest = False
    for entry in candidates:
        if found_latest:
            # Once we've found the latest real file, assume all older ones exist
            validated.append(entry)
            continue
        try:
            r = requests.get(entry['url'], stream=True, timeout=8)
            ct = r.headers.get('Content-Type', '')
            r.close()
            if 'spreadsheet' in ct or 'excel' in ct:
                found_latest = True
                validated.append(entry)
        except requests.RequestException:
            continue

    return validated

@st.cache_data(ttl='1d', show_spinner='Getting EIA data...')
def get_eia_data(eia860m):

    # Load Operating data
    o = pd.read_excel(eia860m, sheet_name='Operating', skiprows=2, skipfooter=2)
    o['Nameplate Capacity (MW)'] = pd.to_numeric(o['Nameplate Capacity (MW)'], errors='coerce')
    o['simple_status'] = 'Operating'

    # Format as YYYY-MM
    o['Year'] = o['Operating Year']
    o['Month'] = o['Operating Month'].astype(int).astype(str).str.zfill(2)
    o['Year-Month'] = o['Year'].astype(int).astype(str) + '-' + o['Month']

    # Load Planned data
    p = pd.read_excel(eia860m, sheet_name='Planned', skiprows=2, skipfooter=2)
    p['Nameplate Capacity (MW)'] = pd.to_numeric(p['Nameplate Capacity (MW)'], errors='coerce')
    p['simple_status'] = 'Planned'

    # Format as YYYY-MM
    p['Year'] = p['Planned Operation Year']
    p['Month'] = p['Planned Operation Month'].astype(int).astype(str).str.zfill(2)
    p['Year-Month'] = p['Year'].astype(int).astype(str) + '-' + p['Month']

    plants = pd.concat([o,p])

    return o, p, plants

available_months = get_available_months()
labels = [m['label'] for m in available_months]

# Default selections: latest month + same month in 2 preceding years
latest = available_months[0]
default_labels = [latest['label']]
prior_years = [m for m in available_months
               if m['month'] == latest['month'] and m['year'] < latest['year']]
prior_years.sort(key=lambda x: x['year'], reverse=True)
for entry in prior_years[:2]:
    default_labels.append(entry['label'])

# Multi-select for reporting periods
selected_labels = st.multiselect('Reporting periods', labels, default=default_labels)
if not selected_labels:
    st.warning('Please select at least one reporting period.')
    st.stop()

# Sort selected periods by date (newest first)
selected_entries = [m for m in available_months if m['label'] in selected_labels]
selected_entries.sort(key=lambda x: x['sort_key'], reverse=True)

# Load data for all selected periods
plants = pd.DataFrame()
for entry in selected_entries:
    _, _, plants_temp = get_eia_data(entry['url'])
    plants_temp['Reporting Period'] = entry['label']
    plants = pd.concat([plants, plants_temp])

# The most recent selected period drives metrics, bar charts, and vline
primary = selected_entries[0]
year = primary['year']
month = primary['month']
month_num = primary['month_num']
ym_num = f"{year}-{month_num:02d}"
year_month = primary['label']

status_options = ['Planned','Operating','Both']
status = st.radio(
    'Construction status', 
    status_options, 
    index=2,
    horizontal=True)
statuses = [status] if status != 'Both' else status_options[0:2]
mask = plants['simple_status'].isin(statuses) & (plants['Reporting Period'] == year_month)
mw = plants.loc[mask].groupby('Technology')['Nameplate Capacity (MW)'].sum()
top_technologies = mw.sort_values(ascending=False).head(16)

cols = st.columns(8)
for col in cols:
    tech = top_technologies.index[cols.index(col)]
    tech = tech.replace('Natural Gas Fired', 'NG')
    tech = tech.replace('Natural Gas', 'NG')
    tech_GW = top_technologies.iloc[cols.index(col)] / 1E3
    col.metric(tech, f"{tech_GW:.0f} GW") 

# st.dataframe(plants)

# Determine chart x-axis range from all selected periods
all_years = [int(e['year']) for e in selected_entries]
chart_start = f"{min(all_years)}-01"
chart_end = f"{max(all_years)+5}-08"

# st.dataframe(plants)

# techs = plants['Technology'].unique()
# n_techs = st.slider('Only plot the top N power technologies', 
#                     min_value=4, 
#                     max_value=len(techs), 
#                     value=16)
# top_technologies = mw.sort_values().tail(n_techs)

'### Built and Planned Capacity by Year and Month'
top_only_ym = st.toggle('Only plot the top 16 power technologies', True)
gb = plants.groupby(['Reporting Period','Year-Month','Technology'])
mw = gb['Nameplate Capacity (MW)'].sum()
mw = mw.loc[:, :, top_technologies.index] if top_only_ym else mw
mw = mw.reset_index()

mask = plants['Reporting Period']==year_month
mask = mask & plants['Technology'].isin(top_technologies.index) if top_only_ym else mask

mw_month_bar = px.bar(
    plants.loc[mask],
    # mw.loc[year_month], 
    x="Year-Month", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    category_orders={"Technology": list(top_technologies.index)}, # [::-1]
    hover_data=["Plant Name","County","Entity Name","Status",],
    barmode='stack'
)

mw_month_bar.update_xaxes(range=["2023-01", f"{int(year)+5}-08"])
mw_month_bar.add_vline(x=ym_num, line_width=1, line_dash="dot")
mw_month_bar.add_annotation(x=ym_num, xanchor='left',
                            y=1.01, yref='paper', 
                            text="Planned", showarrow=False)    
mw_month_bar.add_annotation(x=ym_num, xanchor='right',
                            y=1.01, yref='paper', 
                            text="Built", showarrow=False)    

st.plotly_chart(mw_month_bar)

mw_month_line = px.line(
    mw, 
    x="Year-Month", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4,
    height=800,
    color="Reporting Period", 
)

mw_month_line.update_xaxes(range=["2023-01", f"{int(year)+5}-08"])
mw_month_line.update_yaxes(range=[0, max(mw['Nameplate Capacity (MW)']) * 1.1])
mw_month_line.add_vline(x=ym_num, line_width=1, line_dash="dot")
mw_month_line.for_each_annotation(lambda a: a.update(text=a.text.replace("Technology=", "")))
# mw_month_line.update_yaxes(matches=None)
st.plotly_chart(mw_month_line)

'### Operating and Planned Capacity by Year'

start_year = 1945

top_only_y = st.toggle('Plot just the top 16 power technologies', True)
gb = plants.groupby(['Reporting Period','Year','Technology'])
mw = gb['Nameplate Capacity (MW)'].sum()
mw = mw.loc[:, :, top_technologies.index] if top_only_y else mw

mw_bar = px.bar(
    mw.loc[year_month, :, :].reset_index(), 
    x="Year", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

mw_bar.update_xaxes(range=[start_year, None])
mw_bar.add_vline(x=year_month[0:4], line_width=1, line_dash="dot")
mw_bar.add_annotation(x=year_month[0:4], xanchor='left',
                      y=1.01, yref='paper', 
                      text="Planned", showarrow=False)    
mw_bar.add_annotation(x=year_month[0:4], xanchor='right',
                      y=1.01, yref='paper', 
                      text="Built", showarrow=False)    
st.plotly_chart(mw_bar)

mw_line = px.line(
    mw.reset_index(), 
    x="Year", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4,
    height=800,
    color="Reporting Period", 
)

mw_line.update_xaxes(range=[start_year, None])
mw_line.add_vline(x=year_month[0:4], line_width=1, line_dash="dot")
mw_line.for_each_annotation(lambda a: a.update(text=a.text.replace("Technology=", "")))
st.plotly_chart(mw_line)

# plant_map = px.scatter_geo(
#     plants.loc[mask & (plants['Nameplate Capacity (MW)'] > 50)],
#     lat='Latitude',
#     lon='Longitude',
#     color='Technology',
#     hover_name='Plant Name',
#     hover_data=['Entity Name','County','Status','Nameplate Capacity (MW)'],
#     size='Nameplate Capacity (MW)',
#     projection='natural earth',
#     category_orders={"Technology": list(top_technologies.index)}, # [::-1]
#     title=f'Power Plants in the US as of {year_month}',
# )
# st.plotly_chart(plant_map)

'_Sources: [Form EIA-860](https://www.eia.gov/electricity/data/eia860/) and [Form EIA-860M](https://www.eia.gov/electricity/data/eia860m/)_'