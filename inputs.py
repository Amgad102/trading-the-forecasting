from Mish.utils import get_rate
import numpy as np

## PROJECT PARAMETERS:
electricity_price_file = None
YEAR_START = 2024
PROJECT_LIFETIME = 30
price_mean_modifier = 1
price_std_modifier = 1
negative_prices_correction = None
positive_prices_correction = False
price_minimum = 0
PPA = None
PPA_sales = None
location = "Seville"
subsidy_per_mwh = 0
forbidden_tariff_periods = []
generation_restrictions_file = None
tension_level = "Exempted"
electricity_tax = 5.113 ## %
margin_tradingcompany_energy = 0 ##EUR/kwh
margin_tradingcompany_power = 0 ##EUR/kw/year
sample_period_days  = 3
rcs_maximum_idle_time = 4 #hours
rps_maximum_idle_time = 0 #hours
number_years_to_calculate = 1
is_cost_driven = False
electricity_price_forecasting = False

## SYSTEM GENERAL SPECIFICATIONS:
unit = "kg O2"
resource_consumption_power = 361.2 ## MWhe
charge_to_discharge_ratio = 1  ## Resource production rate / Resource consumption rate
rss_day_0 = 0
storage_capacity = -1  ## units (e.g., kg H2)
resource_consumption_TES_capacity = 0 ## MWh_thermal


## RESOURCE CONSUMPTION SUBSYSTEM (RCS):
load_factor_rcs = 1
resource_rate_rcs = 0.0017168 # MWhe/kgO2
fuel_consumption_rate_rcs = 1.8434
min_power_rcs = 0.4
water_consumption_rate_rcs = 1.4602 ## m3 water / MWhe
thermal_power_consumption_rate_rcs = 0 ## MWht/MWhe
thermal_power_production_rate_rcs = 0 ## MWht/MWhe

specific_footprint_rcs = 0 ## m2/MWhe
rcs_maintenance_costs = {
    450: 0
}
rcs_maintenance_cost_annual_reduction = 0  # [%/year]
specific_capex_rcs = 494.3 ## €/kWe
specific_opex_fix_rcs = specific_capex_rcs*0.03/PROJECT_LIFETIME ## €/kWe/year
opex_var_rcs = 0 ## €/MWhe

# BYPASS:
bypass_operation_enabled = False
load_factor_bypass_rcs = load_factor_rcs  
resource_rate_bypass_rcs = resource_rate_rcs
fuel_consumption_rate_bypass_rcs = 1.78803987
water_consumption_rate_bypass_rcs = water_consumption_rate_rcs ## m3 water / MWhe #REVISAR
thermal_power_consumption_rate_bypass_rcs = 0 ## MWht/MWhe
thermal_power_production_rate_bypass_rcs = 0 ## MWht/MWhe
opex_var_bypass_rcs = 0 ## €/MWhe

# No resource (RCS ONLY):
rcs_only_operation_enabled = True
load_factor_only_rcs = 300/361.2
fuel_consumption_rate_only_rcs = fuel_consumption_rate_bypass_rcs*361.2/300
water_consumption_rate_only_rcs = (1.4602*361.2 + 1.3419*61.2)/300## m3 water / MWhe #REVISAR
thermal_power_consumption_rate_only_rcs = 0 ## MWht/MWhe
thermal_power_production_rate_only_rcs = 0 ## MWht/MWhe
opex_var_only_rcs = 0 ## €/MWhe


## RESOURCE PRODUCTION SUBSYSTEM (RPS):

resource_rate_rps = 0.7657*3600 ## unit/MWhe
min_power_rps = 0.2
fuel_consumption_rate_rps = 0 ## MWh fuel / MWhe
water_consumption_rate_rps = 1.3419 ## m3 water / MWhe
thermal_power_consumption_rate_rps = 0 ## MWht/MWhe
thermal_power_production_rate_rps = 0 ## MWht/MWhe
specific_footprint_rps = 0 ## m2/MWhe
specific_capex_rps = 2200.4
specific_opex_fix_rps = specific_capex_rps*0.015/PROJECT_LIFETIME ## €/kWe/year
opex_var_rps = 0 ## €/MWhe
start_up_cost_rps = 0 ## €/start_up

# BYPASS:
resource_rate_bypass_rps = 0.7657*3600*76.325/61.2## kgO2/MWhe
fuel_consumption_rate_bypass_rps = 0 ## MWh fuel / MWhe
water_consumption_rate_bypass_rps = water_consumption_rate_rps ## m3 water / MWhe
thermal_power_consumption_rate_bypass_rps = 0 ## MWht/MWhe
thermal_power_production_rate_bypass_rps = 0 ## MWht/MWhe
opex_var_bypass_rps = 0 ## €/MWhe

## RESOURCE STORAGE SUBSYSTEM (RSS):
min_capacity_fraction_rss = 0
specific_capex_rss = 1.4393 ## €/unit
specific_opex_fix_rss = specific_capex_rss*0.015/PROJECT_LIFETIME ## €/unit/year
specific_footprint_rss = 0 ## m2/unit
resource_losses_rss = 0 ## unit/hour
resource_inlet_annual_distribution_file = None
resource_inlet_power_consumption_rate = 0 # MWe / unit accepted

## AUXILIARIES:
fuel_cost = 45.2 # €/MWh
start_up_cost_rcs = 0
water_cost = 3 # €/m3
thermal_power_cost = 0 # €/MWht
resource_inlet_cost = 0 #€/unit
land_cost = 0 ## €/ha
electrical_subsystem_specific_cost = 35 ### €/kWe
contingencies_factor = 5 ## %
indirect_cost_factor = 5 ## %
owner_cost_factor = 3 ## %
other_direct_capex = 0 #€

## FINANCIAL:
equity_debt_ratio = 30/70
tax_rate = 25 #%
DEBT_LIFETIME = 30
interest_rate = 7 #%
RROE = 12 #%
amortization_method = 'Straight_Line'
salvage_value = 0 #% of total_capex
inflation_rate = 2.1 #%