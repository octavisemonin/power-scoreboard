import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title='The Power Scoreboard',
    page_icon='⚡️', # This is an emoji shortcode. Could be a URL too.
    layout='wide'
)

st.title("⚡️ The Power Scoreboard")
st.write(
    "A handy energy scoreboard for the United States."
)

@st.cache_data(ttl='1d', show_spinner='Getting EIA data...')
def get_eia_data(eia860m):

    o = pd.read_excel(eia860m, sheet_name='Operating', skiprows=2, skipfooter=2)
    o['Nameplate Capacity (MW)'] = pd.to_numeric(o['Nameplate Capacity (MW)'], errors='coerce')

    # Format as YYYY-MM
    o['Year'] = o['Operating Year']
    o['Month'] = o['Operating Month'].astype(int).astype(str).str.zfill(2)
    o['Year-Month'] = o['Year'].astype(int).astype(str) + '-' + o['Month']

    p = pd.read_excel(eia860m, sheet_name='Planned', skiprows=2, skipfooter=2)
    p['Nameplate Capacity (MW)'] = pd.to_numeric(p['Nameplate Capacity (MW)'], errors='coerce')

    # Format as YYYY-MM
    p['Year'] = p['Planned Operation Year']
    p['Month'] = p['Planned Operation Month'].astype(int).astype(str).str.zfill(2)
    p['Year-Month'] = p['Year'].astype(int).astype(str) + '-' + p['Month']

    # p = p.loc[p['Planned Operation Year'] < 2035].copy()

    plants = pd.concat([o,p])

    return o, p, plants

month = 'july'
year = '2025'

eia860m = f'https://www.eia.gov/electricity/data/eia860m/archive/xls/{month}_generator{year}.xlsx'
eia860m = f'https://www.eia.gov/electricity/data/eia860m/xls/{month}_generator{year}.xlsx'

o, p, plants = get_eia_data(eia860m)
plants['Reporting Period'] = f"{year}-{month.capitalize()}"
# st.dataframe(plants)

# techs = plants['Technology'].unique()
# n_techs = st.slider('Only plot the top N power technologies', 
#                     min_value=4, 
#                     max_value=len(techs), 
#                     value=16)
# top_technologies = mw.sort_values().tail(n_techs)

'### Built and Planned Capacity by Year and Month'
top_only_ym = st.toggle('Only plot the top 16 power technologies', True)
mw = plants.groupby('Technology')['Nameplate Capacity (MW)'].sum()
top_technologies = mw.sort_values().tail(16)

mw = plants.groupby(['Year-Month','Technology'])['Nameplate Capacity (MW)'].sum()
mw = mw.loc[:, top_technologies.index] if top_only_ym else mw
# if top_only_ym:
#     mw = mw.loc[mw['Technology'].isin(top_technologies.index)]

mw_month_bar = px.bar(
    mw.reset_index(), 
    x="Year-Month", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

mw_month_bar.update_xaxes(range=["2023-01", f"{int(year)+5}-08"])
mw_month_bar.add_vline(x="2025-07", line_width=1, line_dash="dot")
mw_month_bar.add_annotation(x="2025-07", xanchor='left',
                            y=1.01, yref='paper', 
                            text="Planned", showarrow=False)    
mw_month_bar.add_annotation(x="2025-07", xanchor='right',
                            y=1.01, yref='paper', 
                            text="Built", showarrow=False)    

st.plotly_chart(mw_month_bar)

mw_month_line = px.line(
    mw.reset_index(), 
    x="Year-Month", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4,
    height=800,
    # color="Reporting Year", 
)

mw_month_line.update_xaxes(range=["2023-01", f"{int(year)+5}-08"])
mw_month_line.update_yaxes(range=[0, max(mw) * 1.1])
mw_month_line.add_vline(x="2025-07", line_width=1, line_dash="dot")
mw_month_line.for_each_annotation(lambda a: a.update(text=a.text.replace("Technology=", "")))
# mw_month_line.update_yaxes(matches=None)
st.plotly_chart(mw_month_line)

'### Operating and Planned Capacity by Year'

# start_year = st.slider('Start year', 
#                        min_value=min(plants['Year']), 
#                        max_value=max(plants['Year']), 
#                        value=1945)
start_year = 1945

top_only_y = st.toggle('Plot just the top 16 power technologies', True)
mw = plants.groupby('Technology')['Nameplate Capacity (MW)'].sum()
top_technologies = mw.sort_values().tail(16)

mw = plants.groupby(['Year','Technology'])['Nameplate Capacity (MW)'].sum()
mw = mw.loc[:, top_technologies.index] if top_only_y else mw

mw_bar = px.bar(
    mw.reset_index(), 
    x="Year", 
    y="Nameplate Capacity (MW)", 
    color="Technology", 
    barmode='stack'
)

mw_bar.update_xaxes(range=[start_year, None])
mw_bar.add_vline(x="2025", line_width=1, line_dash="dot")
st.plotly_chart(mw_bar)

mw_line = px.line(
    mw.reset_index(), 
    x="Year", 
    y="Nameplate Capacity (MW)", 
    facet_col="Technology",
    facet_col_wrap=4,
    height=800,
    # color="Reporting Year", 
)

mw_line.update_xaxes(range=[start_year, None])
mw_line.add_vline(x="2025", line_width=1, line_dash="dot")
mw_line.for_each_annotation(lambda a: a.update(text=a.text.replace("Technology=", "")))
st.plotly_chart(mw_line)

'_Sources: [Form EIA-860](https://www.eia.gov/electricity/data/eia860/) and [Form EIA-860M](https://www.eia.gov/electricity/data/eia860m/)_'

# '### Operating'
# # By Year-Month
# mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
# top_15 = mw_operating.sum().sort_values().tail(15)

# mw_operating = o.groupby(['Year-Month','Technology'])['Nameplate Capacity (MW)'].sum()
# mw_operating_month_bar = px.bar(
#     mw_operating.reset_index(), 
#     x="Year-Month", 
#     y="Nameplate Capacity (MW)", 
#     color="Technology", 
#     barmode='stack'
# )

# mw_operating_month_bar.update_xaxes(range=["2023-01", f"{year}-08"])
# st.plotly_chart(mw_operating_month_bar)

# # By Year
# mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
# top_15 = mw_operating.sum().sort_values().tail(15)

# mw_operating = o.groupby(['Operating Year','Technology'])['Nameplate Capacity (MW)'].sum()
# mw_operating_bar = px.bar(
#     mw_operating.reset_index(), 
#     x="Operating Year", 
#     y="Nameplate Capacity (MW)", 
#     color="Technology", 
#     barmode='stack'
# )

# mw_operating_bar.update_xaxes(range=[1950, None])
# st.plotly_chart(mw_operating_bar)
# # st.dataframe(mw_operating)

# mw_operating_line = px.line(
#     mw_operating.reset_index(), 
#     x="Operating Year", 
#     y="Nameplate Capacity (MW)", 
#     facet_col="Technology",
#     facet_col_wrap=4
#     # color="Reporting Year", 
# )

# st.plotly_chart(mw_operating_line)

# '### Planned'

# # By Year-Month
# mw_planned = p.groupby(['Year-Month','Technology'])['Nameplate Capacity (MW)'].sum()
# mw_planned_month_bar = px.bar(
#     mw_planned.reset_index(), 
#     x="Year-Month", 
#     y="Nameplate Capacity (MW)", 
#     color="Technology", 
#     barmode='stack'
# )

# mw_planned_month_bar.update_xaxes(range=[f"{year}-06", f"{int(year)+5}-01"])

# st.plotly_chart(mw_planned_month_bar)

# # By Year
# mw_planned = p.groupby(['Planned Operation Year','Technology'])['Nameplate Capacity (MW)'].sum().unstack()
# top_15 = mw_planned.sum().sort_values().tail(15)

# mw_planned = p.groupby(['Planned Operation Year','Technology'])['Nameplate Capacity (MW)'].sum()
# mw_planned_bar = px.bar(
#     mw_planned.reset_index(), 
#     x="Planned Operation Year", 
#     y="Nameplate Capacity (MW)", 
#     color="Technology", 
#     barmode='stack'
# )

# st.plotly_chart(mw_planned_bar)
# # st.dataframe(mw_planned)

# mw_planned_line = px.line(
#     mw_planned.reset_index(), 
#     x="Planned Operation Year", 
#     y="Nameplate Capacity (MW)", 
#     facet_col="Technology",
#     facet_col_wrap=4
#     # color="Reporting Year", 
# )

# st.plotly_chart(mw_planned_line)