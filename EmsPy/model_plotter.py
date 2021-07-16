import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
import datetime as dt

df_file = 'default_dfs'

df = pd.read_csv('A:\Files\PycharmProjects\RL-BCA\EmsPy\\' + df_file )

# trim to ignore Design Days, truncate for faster dev
dd_index = 0
dd_span = 10000
df = df.truncate(before=dd_index, after=dd_index + dd_span)

# replace year with same leap-year (IF NEEDED), https://www.timeanddate.com/date/weekday.html
timex = df['Datetime'].str.slice_replace(stop=5, repl='2000-')  # fix inconsistent years of weather file

# timex = df['Datetime']
# transform str back into datetime obj
# timex = list(map(datetime.strptime, timex, len(timex)*['%m-%d %H:%M:%S']))
timex = list(map(datetime.strptime, timex, len(timex)*['%Y-%m-%d %H:%M:%S']))

# timex = range(df.shape[0])


fig, (ax1, ax2) = plt.subplots(2)
fig.suptitle('Temperature and Humidity Zone Control')

# temp dates
ax1.set_xlabel('')
formatter = mdates.DateFormatter("%m-%d")
ax1.xaxis.set_major_formatter(formatter)
locator = mdates.DayLocator()
ax1.xaxis.set_major_locator(locator)
# do above ^ just to get proper tick spacing
ax1.set_xticklabels([])  # share x-axis, hide x-axis
ax1.grid()
fig.subplots_adjust(hspace=0.1)
# humidity dates
ax2.set_xlabel('Date')
formatter = mdates.DateFormatter("%m-%d")
ax2.xaxis.set_major_formatter(formatter)
locator = mdates.DayLocator()
ax2.xaxis.set_major_locator(locator)
ax2.grid()

# xlims
ax1.set_xlim([datetime(2000, 1, 1,0,0,0), datetime(2000,1,15,0,0,0)])
ax2.set_xlim([datetime(2000, 1, 1,0,0,0), datetime(2000,1,15,0,0,0)])


# line plot params
outdoor_linewidth = 2
outdoor_color = 'k'

# zone temps
ax1.set_ylabel('Temp (c)')
ax1.plot(timex, df['z2_temp'].values, label='Z2 Temp')
ax1.plot(timex, df['z3_temp'].values, label='Z3 Temp')
ax1.plot(timex, df['z4_temp'].values, label='Z4 Temp')
ax1.plot(timex, df['z1_temp'].values, label='Z1 Temp')
ax1.plot(timex, df['z0_temp'].values, label='Z0 Temp')
# outdoor
ax1.plot(timex, df['oa_db_temp'].values, outdoor_color, label='Outdoor DB Temp', linewidth=outdoor_linewidth)
ax1.legend()

# zone humidity
ax2.set_ylabel('Relative Humidity (%)')
ax2.plot(timex, df['z0_rh'].values, label='Z0 %RH')
ax2.plot(timex, df['z1_rh'].values, label='Z1 %RH')
ax2.plot(timex, df['z2_rh'].values, label='Z2 %RH')
ax2.plot(timex, df['z3_rh'].values, label='Z3 %RH')
ax2.plot(timex, df['z4_rh'].values, label='Z4 %RH')
# outdoor
ax2.plot(timex, df['oa_rh'].values, outdoor_color, label='Outdoor %RH', linewidth=outdoor_linewidth)
ax2.legend()

# control # TODO match control line type to its zone line type
# RGBA color picker https://www.w3schools.com/css/css_colors_rgb.asp
# only shows on 1 monitor
ax1.fill_between(timex, df['zone0_cool_sp'].values, df['zone0_heat_sp'].values, color=(240/255, 240/255, 240/255, 1))

plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)


plt.show()
