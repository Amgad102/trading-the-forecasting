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
tension_level = "6.3 TD"
electricity_tax = 5.113 ## %
margin_tradingcompany_energy = 0 ##EUR/kwh
margin_tradingcompany_power = 0 ##EUR/kw/year
sample_period_days  = 1  ## days; for 168h forecast model use 1–7, for 24h model use 1
number_years_to_calculate = 1
is_cost_driven = False
electricity_price_forecasting = False
## Forecasting settings (used when electricity_price_forecasting = True):
forecast_file = "G_T_all_hourly_forecasts_168h_model_no_feb29.csv"  ## path relative to MainData/
targets_file = "targets.csv"                                          ## path relative to MainData/
forecast_column = "T1"      ## column in forecast_file used for trading decisions (e.g. "T1", "G1", "G4", "DA_forecast")
settlement_column = "DA"    ## column in targets_file used for settlement (actual price)

## SYSTEM GENERAL SPECIFICATIONS:
unit = "kg H2"
resource_consumption_power = 59.1 ## MWhe
charge_to_discharge_ratio = 1 ## MWhe(consumption)/MWHe(production)
rss_day_0 = 0.0
storage_capacity = -1
resource_consumption_TES_capacity = 0 ## MWh_thermal

## RESOURCE PRODUCTION SUBSYSTEM (RPS):

min_power_rps = 0
specific_capex_rps = 1092 ## €/kWe
specific_opex_fix_rps = 6.75 ## €/kWe/year
opex_var_rps = 0 ## €/MWhe
start_up_cost_rps = 0 ## €/start_up
resource_rate_rps = 16.94 ## unit/MWhe
fuel_consumption_rate_rps = 0 ## MWh fuel / MWhe
water_consumption_rate_rps = 0.1525 ## m3 water / MWhe
thermal_power_consumption_rate_rps = 0 ## MWht/MWhe
thermal_power_production_rate_rps = 0 ## MWht/MWhe
specific_footprint_rps = 38.63 ## m2/MWhe

## RESOURCE CONSUMPTION SUBSYSTEM (RCS):
min_power_rcs = 0
specific_capex_rcs = 1591 ## €/kWe
specific_opex_fix_rcs = 25.38 ## €/kWe/year
opex_var_rcs = 0 ## €/MWhe
start_up_cost_rcs = 0 ## €/start_up
resource_rate_rcs = 1/56.818 ## unit/MWhe
fuel_consumption_rate_rcs = 0 ## MWh fuel / MWhe
water_consumption_rate_rcs = 0 ## m3 water / MWhe
thermal_power_consumption_rate_rcs = 0 ## MWht/MWhe
thermal_power_production_rate_rcs = 0 ## MWht/MWhe
specific_footprint_rcs = 48.37 ## m2/MWhe

## RESOURCE STORAGE SUBSYSTEM (RSS):
min_capacity_fraction_rss = 0
specific_capex_rss = 465.51 ## €/unit
specific_opex_fix_rss = 4.655 ## €/unit/year
specific_footprint_rss = 0.05773 ## m2/unit
resource_losses_rss = 0 ## unit/hour
resource_inlet_annual_distribution_file = None

## AUXILIARIES:
fuel_cost = 55 # €/MWh
water_cost = 5 # €/m3
thermal_power_cost = 0 # €/MWht
resource_inlet_cost = 0 #€/unit
land_cost = 10000 ## €/ha
electrical_subsystem_specific_cost = 35 ### €/kWe
contingencies_factor = 5 ## %
indirect_cost_factor = 5 ## %
owner_cost_factor = 3 ## %

## FINANCIAL:
equity_debt_ratio = 30/70
tax_rate = 25 #%
DEBT_LIFETIME = 30
interest_rate = 7 #%
RROE = 12 #%
amortization_method = 'Straight_Line'
salvage_value = 5 #% of total_capex
inflation_rate = 2.5 #%