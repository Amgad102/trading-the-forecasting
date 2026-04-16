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
tension_level = "6.3 TD"
electricity_tax = 5.113 ## %
margin_tradingcompany_energy = 0 ##EUR/kwh
margin_tradingcompany_power = 0 ##EUR/kw/year
sample_period_days  = 7
rcs_maximum_idle_time = 0 #hours
number_years_to_calculate = 1
is_cost_driven = False
electricity_price_forecasting = False

## FORECASTING SETTINGS (used when electricity_price_forecasting = True):
# Default files: 168h DA forecast and targets.
# The forecast_file should be placed in the MainData/ folder.
# forecast_column: column in forecast_file used for trading decisions (e.g. "G1", "G4", "T")
# target_column:   column in targets_file used for settlement (actual price, e.g. "T")
# sample_period_days: how many days ahead the trader looks per window (1–7 for 168h file; 1 for 24h file)
forecast_file = "G_T_all_hourly_forecasts_168h_model_no_feb29.csv"
targets_file = "targets.csv"
forecast_column = "G1"   ## column from forecast_file for decisions
target_column = "T"      ## column from targets_file for settlement
## Note: override sample_period_days = 1 (default for forecasting, 1–7 valid for 168h file)

## SYSTEM GENERAL SPECIFICATIONS:
unit = "kg H2"
resource_consumption_power = 59.1 ## MWhe
charge_to_discharge_ratio = 0.97 ## Resource production rate / Resource consumption rate
rss_day_0 = 0.0
storage_capacity = 150000
resource_consumption_TES_capacity = 0 ## MWh_thermal


## RESOURCE CONSUMPTION SUBSYSTEM (RCS):
from inputs_projects.MHI.CombinedCycleData import CombinedCycleData

ccgt_model = CombinedCycleData()

def resource_rate_rcs(load_frac, T, RH):
    LHV = 120 #MJ/kg
    if load_frac > 0.6:
        correction = ccgt_model.gt_dictionary_part_load_correction_factors['heat_rate'](load_frac * 100, T, RH)
        heat_rate_MJ_MWh = correction * (ccgt_model.gt_dictionary_iso['Heat Rate'])  # [kJ_fuel / kWh_elec]
        return LHV/heat_rate_MJ_MWh
    else:
        return np.inf
    
def fuel_consumption_rate_rcs(load_frac, T, RH):
    LHV = 49.717 #MJ/kg
    if load_frac == 0.6:
        correction = ccgt_model.gt_dictionary_part_load_correction_factors['heat_rate'](load_frac * 100, T, RH)
        fuel_heat_rate_MJ_MWh = correction * (ccgt_model.gt_dictionary_iso['Heat Rate'])  # [kJ_fuel / kWh_elec]
        return fuel_heat_rate_MJ_MWh/3600
    else:
        return 0
    
    
min_power_rcs = 0.6
water_consumption_rate_rcs = 0 ## m3 water / MWhe
thermal_power_consumption_rate_rcs = 0 ## MWht/MWhe
thermal_power_production_rate_rcs = 0 ## MWht/MWhe

specific_footprint_rcs = 48.37 ## m2/MWhe
rcs_maintenance_costs = {
    450: 1_983_333,
    900: 4_833_333,
    1350: 1_983_333,
    1800: 7_000_000
}
rcs_maintenance_cost_annual_reduction = 0  # [%/year]
specific_capex_rcs = 422.2*1E6*(resource_consumption_power/650)**0.63/(resource_consumption_power*1000) ## €/kWe
specific_opex_fix_rcs = 1.5*10**6 / (resource_consumption_power*1000) ## €/kWe/year
opex_var_rcs = 0 ## €/MWhe
start_up_cost_rcs = 567.17 ## €/start_up

## RESOURCE PRODUCTION SUBSYSTEM (RPS):

min_power_rps = 0
resource_rate_rps = 16.88 ## unit/MWhe
fuel_consumption_rate_rps = 0 ## MWh fuel / MWhe
water_consumption_rate_rps = 0.1508 ## m3 water / MWhe
thermal_power_consumption_rate_rps = 0 ## MWht/MWhe
thermal_power_production_rate_rps = 0 ## MWht/MWhe
specific_footprint_rps = 38.63 ## m2/MWhe
specific_capex_rps = 112.7 + 220*1E6*(resource_consumption_power * charge_to_discharge_ratio / (get_rate(resource_rate_rcs, load_frac=1, T=15, RH=0) * resource_rate_rps)/220)**0.85/(resource_consumption_power * charge_to_discharge_ratio / (get_rate(resource_rate_rcs, load_frac=1, T=15, RH=0) * resource_rate_rps)*1000) ## €/kWe
specific_opex_fix_rps = specific_capex_rps*0.005 ## €/kWe/year
opex_var_rps = 0 ## €/MWhe
start_up_cost_rps = 0 ## €/start_up


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