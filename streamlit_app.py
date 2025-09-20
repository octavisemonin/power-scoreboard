import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.title("⚡️ The Power Scoreboard")
st.write(
    "A handy energy scoreboard."
)

month = 'july'
year = '2025'

eia860m = f'https://www.eia.gov/electricity/data/eia860m/archive/xls/{month}_generator{year}.xlsx'
eia860m = f'https://www.eia.gov/electricity/data/eia860m/xls/{month}_generator{year}.xlsx'

'### Operating'
@st.cache_data(ttl='1d', show_spinner='Getting operating plant data...')
def get_operating_data():
    o = pd.read_excel(eia860m, sheet_name='Operating', skiprows=2, skipfooter=2)
    o['Nameplate Capacity (MW)'] = pd.to_numeric(o['Nameplate Capacity (MW)'], errors='coerce')

    # Format as YYYY-MM
    o['month'] = o['Operating Month'].astype(int).astype(str).str.zfill(2)
    o['Operating Year-Month'] = o['Operating Year'].astype(int).astype(str) + '-' + o['month']

    return o

o = get_operating_data()

# By Year-Month
mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
top_15 = mw_operating.sum().sort_values().tail(15)

mw_operating = o.groupby(['Operating Year-Month','Technology'])['Nameplate Capacity (MW)'].sum()
mw_operating_month_bar = px.bar(
    mw_operating.reset_index(), 
    x="Operating Year-Month", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

mw_operating_month_bar.update_xaxes(range=["2023-01", f"{year}-08"])

st.plotly_chart(mw_operating_month_bar)

# By Year
mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
top_15 = mw_operating.sum().sort_values().tail(15)

mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum()
mw_operating_bar = px.bar(
    mw_operating.reset_index(), 
    x="Operating Year", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

st.plotly_chart(mw_operating_bar)
# st.dataframe(mw_operating)

mw_operating_line = px.line(
    mw_operating.reset_index(), 
    x="Operating Year", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4
    # color="Reporting Year", 
)

st.plotly_chart(mw_operating_line)

'### Planned'
@st.cache_data(ttl='1d', show_spinner='Getting planned plant data...')
def get_planned_data():
    p = pd.read_excel(eia860m, sheet_name='Planned', skiprows=2, skipfooter=2)
    p['Nameplate Capacity (MW)'] = pd.to_numeric(p['Nameplate Capacity (MW)'], errors='coerce')

    # Format as YYYY-MM
    p['month'] = p['Planned Operation Month'].astype(int).astype(str).str.zfill(2)
    p['Year-Month'] = p['Planned Operation Year'].astype(int).astype(str) + '-' + p['month']

    return p.loc[p['Planned Operation Year'] < 2035]

p = get_planned_data()

# By Year-Month
mw_planned = p.groupby(['Year-Month','Technology'])['Nameplate Capacity (MW)'].sum()
mw_planned_month_bar = px.bar(
    mw_planned.reset_index(), 
    x="Year-Month", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

mw_planned_month_bar.update_xaxes(range=[f"{year}-06", f"{int(year)+5}-01"])

st.plotly_chart(mw_planned_month_bar)

# By Year
mw_planned = p.groupby(['Planned Operation Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
top_15 = mw_planned.sum().sort_values().tail(15)

mw_planned = p.groupby(['Planned Operation Year','Technology'])['Nameplate Capacity (MW)'].sum()
mw_planned_bar = px.bar(
    mw_planned.reset_index(), 
    x="Planned Operation Year", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

st.plotly_chart(mw_planned_bar)
# st.dataframe(mw_planned)

mw_planned_line = px.line(
    mw_planned.reset_index(), 
    x="Planned Operation Year", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4
    # color="Reporting Year", 
)

st.plotly_chart(mw_planned_line)