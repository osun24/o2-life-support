import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider

# --- Simulation Parameters ---
POTATO_YIELD_PER_SQ_METER_PER_CYCLE = 5.0
CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE = 0.1
POTATO_HARVEST_CYCLE_DAYS = 100
CHLORELLA_CYCLE_DAYS = 7

AVG_DAILY_POTATO_YIELD_PER_M2 = POTATO_YIELD_PER_SQ_METER_PER_CYCLE / POTATO_HARVEST_CYCLE_DAYS
AVG_DAILY_CHLORELLA_YIELD_PER_M2 = CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE / CHLORELLA_CYCLE_DAYS

KCAL_PER_KG_POTATO = 770
KCAL_PER_KG_CHLORELLA = 3500
KCAL_PER_PERSON_PER_DAY = 2000

# --- Initial Plotting and Slider Range Parameters ---
INITIAL_MAX_DAYS = 100
INITIAL_POTATO_SPACE_M2 = 150.0
INITIAL_CHLORELLA_SPACE_M2 = 50.0
INITIAL_NUM_PEOPLE = 4

plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 8.5))
plt.subplots_adjust(left=0.1, bottom=0.42, right=0.75, top=0.82)

days_range_initial = np.array([0, INITIAL_MAX_DAYS])

initial_daily_potato_kcal_total = INITIAL_POTATO_SPACE_M2 * AVG_DAILY_POTATO_YIELD_PER_M2 * KCAL_PER_KG_POTATO
initial_daily_chlorella_kcal_total = INITIAL_CHLORELLA_SPACE_M2 * AVG_DAILY_CHLORELLA_YIELD_PER_M2 * KCAL_PER_KG_CHLORELLA
initial_daily_demand_kcal_total = INITIAL_NUM_PEOPLE * KCAL_PER_PERSON_PER_DAY
initial_total_daily_supply_kcal = initial_daily_potato_kcal_total + initial_daily_chlorella_kcal_total
initial_net_daily_kcal_balance = initial_total_daily_supply_kcal - initial_daily_demand_kcal_total

line_daily_potato_kcal, = ax.plot(days_range_initial, [initial_daily_potato_kcal_total, initial_daily_potato_kcal_total], label='Daily Potato Calories', color='saddlebrown', linewidth=2)
line_daily_chlorella_kcal, = ax.plot(days_range_initial, [initial_daily_chlorella_kcal_total, initial_daily_chlorella_kcal_total], label='Daily Chlorella Calories', color='forestgreen', linewidth=2)
line_daily_demand_kcal, = ax.plot(days_range_initial, [initial_daily_demand_kcal_total, initial_daily_demand_kcal_total], label='Daily People Demand', color='crimson', linestyle='--', linewidth=2)
line_net_daily_calories, = ax.plot(days_range_initial, [initial_net_daily_kcal_balance, initial_net_daily_kcal_balance], label='Net Daily Calories', color='blue', linestyle=':', linewidth=2.5)
# ax_hline_zero = ax.axhline(0, color='grey', linestyle='-', linewidth=0.75, alpha=0.7, label='Break-even Daily') # This line is now removed

text_box_props = dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.95, ec='silver')
status_text_props_good = dict(boxstyle='round,pad=0.4', fc='honeydew', alpha=0.95, ec='darkgreen')
status_text_props_bad = dict(boxstyle='round,pad=0.4', fc='mistyrose', alpha=0.95, ec='darkred')

y_text_row1 = 0.95
y_text_row2 = 0.90
y_text_row3 = 0.85

x_text_col1 = 0.08
x_text_col2 = 0.60
x_text_col3 = 0.80

text_potato_kcal = fig.text(x_text_col1, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_chlorella_kcal = fig.text(x_text_col1, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_space_info = fig.text(x_text_col1, y_text_row3, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_demand_kcal = fig.text(x_text_col2, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_people_count_info = fig.text(x_text_col2, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_net_daily_kcal = fig.text(x_text_col2, y_text_row3, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_overall_status = fig.text(x_text_col3, y_text_row1, '', fontsize=10, fontweight='bold', verticalalignment='top')

ax.set_xlabel('Time (Days)', fontsize=14)
ax.set_ylabel('Daily Calories (kcal/day)', fontsize=14, color='black')
ax.tick_params(axis='y', labelcolor='black')
ax.set_title('Daily Caloric Production vs. Demand', fontsize=16, y=1.03)
ax.grid(True, which='major', linestyle='--', linewidth=0.5)

slider_left = 0.15
slider_width = 0.7
slider_height = 0.03
slider_y_start = 0.29
slider_y_spacing = 0.07

ax_potato_space_slider = plt.axes([slider_left, slider_y_start, slider_width, slider_height], facecolor='lightgoldenrodyellow')
potato_space_slider = Slider(ax=ax_potato_space_slider, label='Potato Space (m²)', valmin=0, valmax=5000, valinit=INITIAL_POTATO_SPACE_M2, valstep=10, color="peru")
ax_chlorella_space_slider = plt.axes([slider_left, slider_y_start - slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
chlorella_space_slider = Slider(ax=ax_chlorella_space_slider, label='Chlorella Space (m²)', valmin=0, valmax=5000, valinit=INITIAL_CHLORELLA_SPACE_M2, valstep=10, color="mediumseagreen")
ax_people_slider = plt.axes([slider_left, slider_y_start - 2*slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
people_slider = Slider(ax=ax_people_slider, label='Number of People', valmin=1, valmax=50, valinit=INITIAL_NUM_PEOPLE, valstep=1, color="skyblue")

def update_daily_rate_plot(val):
    potato_m2 = potato_space_slider.val
    chlorella_m2 = chlorella_space_slider.val
    num_people = people_slider.val
    current_max_days = int(730)

    ax.set_xlim([0, current_max_days])
    days_data_for_lines = np.array([0, current_max_days])

    daily_potato_kcal = potato_m2 * AVG_DAILY_POTATO_YIELD_PER_M2 * KCAL_PER_KG_POTATO
    daily_chlorella_kcal = chlorella_m2 * AVG_DAILY_CHLORELLA_YIELD_PER_M2 * KCAL_PER_KG_CHLORELLA
    daily_demand_total_kcal = num_people * KCAL_PER_PERSON_PER_DAY
    
    total_daily_supply_kcal = daily_potato_kcal + daily_chlorella_kcal
    net_daily_kcal_balance = total_daily_supply_kcal - daily_demand_total_kcal

    line_daily_potato_kcal.set_data(days_data_for_lines, [daily_potato_kcal, daily_potato_kcal])
    line_daily_chlorella_kcal.set_data(days_data_for_lines, [daily_chlorella_kcal, daily_chlorella_kcal])
    line_daily_demand_kcal.set_data(days_data_for_lines, [daily_demand_total_kcal, daily_demand_total_kcal])
    line_net_daily_calories.set_data(days_data_for_lines, [net_daily_kcal_balance, net_daily_kcal_balance])

    all_y_values = [daily_potato_kcal, daily_chlorella_kcal, daily_demand_total_kcal, net_daily_kcal_balance, 0]
    min_y = min(all_y_values) if all_y_values else 0
    max_y = max(all_y_values) if all_y_values else 100
    
    padding_y_upper = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else max_y * 0.2 + 100
    padding_y_lower = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else 100
    final_min_y = min(min_y - padding_y_lower, -padding_y_lower if min_y > -padding_y_lower else min_y - padding_y_lower * 0.1)
    final_max_y = max_y + padding_y_upper
    if abs(final_max_y - final_min_y) < 500:
        center = (final_max_y + final_min_y) / 2
        span_needed = 500
        if min_y < 0 or net_daily_kcal_balance < 0 :
             span_needed = max(500, abs(net_daily_kcal_balance)*2.2, abs(min_y)*2.2)
             center = 0 if abs(center) < span_needed/4 else center
        final_min_y = center - span_needed / 2
        final_max_y = center + span_needed / 2
    ax.set_ylim([final_min_y, final_max_y])

    text_potato_kcal.set_text(f'Potato Supply: {daily_potato_kcal:,.0f} kcal/day')
    text_chlorella_kcal.set_text(f'Chlorella Supply: {daily_chlorella_kcal:,.0f} kcal/day')
    text_space_info.set_text(f'Potato: {potato_m2:.0f} m² | Chlorella: {chlorella_m2:.0f} m²')
    text_demand_kcal.set_text(f'People Demand: {daily_demand_total_kcal:,.0f} kcal/day')
    text_people_count_info.set_text(f'{num_people} People')
    text_net_daily_kcal.set_text(f'Net Balance: {net_daily_kcal_balance:,.0f} kcal/day')

    if net_daily_kcal_balance >= 0:
        text_overall_status.set_text('Overall System:\nSustainable')
        text_overall_status.set_color('darkgreen')
        text_overall_status.set_bbox(status_text_props_good)
    else:
        text_overall_status.set_text('Overall System:\nUnsustainable')
        text_overall_status.set_color('darkred')
        text_overall_status.set_bbox(status_text_props_bad)
        
    fig.canvas.draw_idle()

handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.77, 0.80), ncol=1, fontsize=9, title="Daily Rates", title_fontsize=10)

potato_space_slider.on_changed(update_daily_rate_plot)
chlorella_space_slider.on_changed(update_daily_rate_plot)
people_slider.on_changed(update_daily_rate_plot)

update_daily_rate_plot(None)
plt.show()

# --- Simulation Parameters ---
POTATO_YIELD_PER_SQ_METER_PER_CYCLE = 5.0
CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE = 0.1
POTATO_HARVEST_CYCLE_DAYS = 100
CHLORELLA_CYCLE_DAYS = 7

AVG_DAILY_POTATO_YIELD_PER_M2 = POTATO_YIELD_PER_SQ_METER_PER_CYCLE / POTATO_HARVEST_CYCLE_DAYS
AVG_DAILY_CHLORELLA_YIELD_PER_M2 = CHLORELLA_YIELD_PER_SQ_METER_PER_CYCLE / CHLORELLA_CYCLE_DAYS

KCAL_PER_KG_POTATO = 770
KCAL_PER_KG_CHLORELLA = 3500
KCAL_PER_PERSON_PER_DAY = 2000

# --- Initial Plotting and Slider Range Parameters ---
INITIAL_MAX_DAYS = 100
INITIAL_POTATO_SPACE_M2 = 150.0
INITIAL_CHLORELLA_SPACE_M2 = 50.0
INITIAL_NUM_PEOPLE = 4

plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 8.5))
plt.subplots_adjust(left=0.1, bottom=0.42, right=0.75, top=0.82)

days_range_initial = np.array([0, INITIAL_MAX_DAYS])

initial_daily_potato_kcal_total = INITIAL_POTATO_SPACE_M2 * AVG_DAILY_POTATO_YIELD_PER_M2 * KCAL_PER_KG_POTATO
initial_daily_chlorella_kcal_total = INITIAL_CHLORELLA_SPACE_M2 * AVG_DAILY_CHLORELLA_YIELD_PER_M2 * KCAL_PER_KG_CHLORELLA
initial_daily_demand_kcal_total = INITIAL_NUM_PEOPLE * KCAL_PER_PERSON_PER_DAY
initial_total_daily_supply_kcal = initial_daily_potato_kcal_total + initial_daily_chlorella_kcal_total
initial_net_daily_kcal_balance = initial_total_daily_supply_kcal - initial_daily_demand_kcal_total

line_daily_potato_kcal, = ax.plot(days_range_initial, [initial_daily_potato_kcal_total, initial_daily_potato_kcal_total], label='Daily Potato Calories', color='saddlebrown', linewidth=2)
line_daily_chlorella_kcal, = ax.plot(days_range_initial, [initial_daily_chlorella_kcal_total, initial_daily_chlorella_kcal_total], label='Daily Chlorella Calories', color='forestgreen', linewidth=2)
line_daily_demand_kcal, = ax.plot(days_range_initial, [initial_daily_demand_kcal_total, initial_daily_demand_kcal_total], label='Daily People Demand', color='crimson', linestyle='--', linewidth=2)
line_net_daily_calories, = ax.plot(days_range_initial, [initial_net_daily_kcal_balance, initial_net_daily_kcal_balance], label='Net Daily Calories', color='blue', linestyle=':', linewidth=2.5)
# ax_hline_zero = ax.axhline(0, color='grey', linestyle='-', linewidth=0.75, alpha=0.7, label='Break-even Daily') # This line is now removed

text_box_props = dict(boxstyle='round,pad=0.3', fc='aliceblue', alpha=0.95, ec='silver')
status_text_props_good = dict(boxstyle='round,pad=0.4', fc='honeydew', alpha=0.95, ec='darkgreen')
status_text_props_bad = dict(boxstyle='round,pad=0.4', fc='mistyrose', alpha=0.95, ec='darkred')

y_text_row1 = 0.95
y_text_row2 = 0.90
y_text_row3 = 0.85

x_text_col1 = 0.08
x_text_col2 = 0.60
x_text_col3 = 0.80

text_potato_kcal = fig.text(x_text_col1, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_chlorella_kcal = fig.text(x_text_col1, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_space_info = fig.text(x_text_col1, y_text_row3, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_demand_kcal = fig.text(x_text_col2, y_text_row1, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_people_count_info = fig.text(x_text_col2, y_text_row2, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_net_daily_kcal = fig.text(x_text_col2, y_text_row3, '', fontsize=9, verticalalignment='top', bbox=text_box_props)
text_overall_status = fig.text(x_text_col3, y_text_row1, '', fontsize=10, fontweight='bold', verticalalignment='top')

ax.set_xlabel('Time (Days)', fontsize=14)
ax.set_ylabel('Daily Calories (kcal/day)', fontsize=14, color='black')
ax.tick_params(axis='y', labelcolor='black')
ax.set_title('Daily Caloric Production vs. Demand', fontsize=16, y=1.03)
ax.grid(True, which='major', linestyle='--', linewidth=0.5)

slider_left = 0.15
slider_width = 0.7
slider_height = 0.03
slider_y_start = 0.29
slider_y_spacing = 0.07

ax_potato_space_slider = plt.axes([slider_left, slider_y_start, slider_width, slider_height], facecolor='lightgoldenrodyellow')
potato_space_slider = Slider(ax=ax_potato_space_slider, label='Potato Space (m²)', valmin=0, valmax=5000, valinit=INITIAL_POTATO_SPACE_M2, valstep=10, color="peru")
ax_chlorella_space_slider = plt.axes([slider_left, slider_y_start - slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
chlorella_space_slider = Slider(ax=ax_chlorella_space_slider, label='Chlorella Space (m²)', valmin=0, valmax=5000, valinit=INITIAL_CHLORELLA_SPACE_M2, valstep=10, color="mediumseagreen")
ax_people_slider = plt.axes([slider_left, slider_y_start - 2*slider_y_spacing, slider_width, slider_height], facecolor='lightgoldenrodyellow')
people_slider = Slider(ax=ax_people_slider, label='Number of People', valmin=1, valmax=50, valinit=INITIAL_NUM_PEOPLE, valstep=1, color="skyblue")

def update_daily_rate_plot(val):
    potato_m2 = potato_space_slider.val
    chlorella_m2 = chlorella_space_slider.val
    num_people = people_slider.val
    current_max_days = int(730)

    ax.set_xlim([0, current_max_days])
    days_data_for_lines = np.array([0, current_max_days])

    daily_potato_kcal = potato_m2 * AVG_DAILY_POTATO_YIELD_PER_M2 * KCAL_PER_KG_POTATO
    daily_chlorella_kcal = chlorella_m2 * AVG_DAILY_CHLORELLA_YIELD_PER_M2 * KCAL_PER_KG_CHLORELLA
    daily_demand_total_kcal = num_people * KCAL_PER_PERSON_PER_DAY
    
    total_daily_supply_kcal = daily_potato_kcal + daily_chlorella_kcal
    net_daily_kcal_balance = total_daily_supply_kcal - daily_demand_total_kcal

    line_daily_potato_kcal.set_data(days_data_for_lines, [daily_potato_kcal, daily_potato_kcal])
    line_daily_chlorella_kcal.set_data(days_data_for_lines, [daily_chlorella_kcal, daily_chlorella_kcal])
    line_daily_demand_kcal.set_data(days_data_for_lines, [daily_demand_total_kcal, daily_demand_total_kcal])
    line_net_daily_calories.set_data(days_data_for_lines, [net_daily_kcal_balance, net_daily_kcal_balance])

    all_y_values = [daily_potato_kcal, daily_chlorella_kcal, daily_demand_total_kcal, net_daily_kcal_balance, 0]
    min_y = min(all_y_values) if all_y_values else 0
    max_y = max(all_y_values) if all_y_values else 100
    
    padding_y_upper = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else max_y * 0.2 + 100
    padding_y_lower = (max_y - min_y) * 0.15 if (max_y - min_y) > 0 else 100
    final_min_y = min(min_y - padding_y_lower, -padding_y_lower if min_y > -padding_y_lower else min_y - padding_y_lower * 0.1)
    final_max_y = max_y + padding_y_upper
    if abs(final_max_y - final_min_y) < 500:
        center = (final_max_y + final_min_y) / 2
        span_needed = 500
        if min_y < 0 or net_daily_kcal_balance < 0 :
             span_needed = max(500, abs(net_daily_kcal_balance)*2.2, abs(min_y)*2.2)
             center = 0 if abs(center) < span_needed/4 else center
        final_min_y = center - span_needed / 2
        final_max_y = center + span_needed / 2
    ax.set_ylim([final_min_y, final_max_y])

    text_potato_kcal.set_text(f'Potato Supply: {daily_potato_kcal:,.0f} kcal/day')
    text_chlorella_kcal.set_text(f'Chlorella Supply: {daily_chlorella_kcal:,.0f} kcal/day')
    text_space_info.set_text(f'Potato: {potato_m2:.0f} m² | Chlorella: {chlorella_m2:.0f} m²')
    text_demand_kcal.set_text(f'People Demand: {daily_demand_total_kcal:,.0f} kcal/day')
    text_people_count_info.set_text(f'{num_people} People')
    text_net_daily_kcal.set_text(f'Net Balance: {net_daily_kcal_balance:,.0f} kcal/day')

    if net_daily_kcal_balance >= 0:
        text_overall_status.set_text('Overall System:\nSustainable')
        text_overall_status.set_color('darkgreen')
        text_overall_status.set_bbox(status_text_props_good)
    else:
        text_overall_status.set_text('Overall System:\nUnsustainable')
        text_overall_status.set_color('darkred')
        text_overall_status.set_bbox(status_text_props_bad)
        
    fig.canvas.draw_idle()

handles, labels = ax.get_legend_handles_labels()
fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(0.77, 0.80), ncol=1, fontsize=9, title="Daily Rates", title_fontsize=10)

potato_space_slider.on_changed(update_daily_rate_plot)
chlorella_space_slider.on_changed(update_daily_rate_plot)
people_slider.on_changed(update_daily_rate_plot)

update_daily_rate_plot(None)
plt.show()