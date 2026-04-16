import os
import pandas as pd
import numpy as np
import time
import math
from multipledispatch.core import dispatch
import matplotlib.pyplot as plt

from Trading.Trading import Trading
from MainData.ElectricityPriceData import ElectricityPriceData
from MainData.WeatherData import WeatherData
from MainData.ThermalPowerData import ThermalPowerData
from MainData.ResourceAvailabilityData import ResourceAvailabilityData
from MainData.OperationsData import OperationsData
from Mish.utils import calculate_rss_series, progressbar, get_rate
from P2P.main_ext import RunMain as P2P_RunMain

from inputs import (price_mean_modifier, price_std_modifier, price_minimum,
                    PPA, PPA_sales, storage_capacity, PROJECT_LIFETIME, YEAR_START,
                    rss_day_0, subsidy_per_mwh, tension_level,
                    electricity_price_forecasting, sample_period_days,
                    forecast_file, targets_file, forecast_column, settlement_column)
import inputs


class Operations(object):

    def __init__(self):

        ## Data object
        self._data_obj = OperationsData()
        self._ramp_rate_method = self._data_obj.ramp_rate_method
        self.rss_day_0 = rss_day_0
        self._project_life = PROJECT_LIFETIME
        self._project_year_start = YEAR_START
        ## get and initialize P2P system RunMain
        self._p2p_main_obj = P2P_RunMain()
        self._p2p_main_obj.run([],[],[],[],[],[],[])  ## initialise objects to estimate initial P2P data FIXME, find a better way to do this
        
        ## Get services cost
        self._fuel_cost = inputs.fuel_cost #€/MWh
        self._water_cost = inputs.water_cost # €/m3
        self._thermal_power_cost = inputs.thermal_power_cost
        self._resource_inlet_cost = inputs.resource_inlet_cost # €/unit

        ## Get Resource Consumption Subsystem:
        self._rcs_installed_power = self._p2p_main_obj.nominal_power_rcs
        self._opex_fix_rcs = self._p2p_main_obj.opex_fix_rcs
        self._opex_var_rcs = self._p2p_main_obj.opex_var_rcs
        self._resource_rate_rcs = self._p2p_main_obj.resource_rate_rcs
        self._fuel_consumption_rate_rcs = self._p2p_main_obj.fuel_consumption_rate_rcs
        self._water_consumption_rate_rcs = self._p2p_main_obj.water_consumption_rate_rcs
        self._thermal_power_consumption_rate_rcs = self._p2p_main_obj.thermal_power_consumption_rate_rcs
        self._rcs_total_variable_opex = self._opex_var_rcs + get_rate(self._fuel_consumption_rate_rcs, load_frac = 1, T = 15, RH = 0)*self._fuel_cost + self._water_consumption_rate_rcs*self._water_cost + self._thermal_power_consumption_rate_rcs*self._thermal_power_cost
        self._start_up_cost_rcs = inputs.start_up_cost_rcs
        
        ## Get Resource Production Subsystem:
        self._rps_installed_power = self._p2p_main_obj.nominal_power_rps
        self._opex_fix_rps = self._p2p_main_obj.opex_fix_rps
        self._opex_var_rps = self._p2p_main_obj.opex_var_rps
        self._resource_rate_rps = self._p2p_main_obj.resource_rate_rps
        self._fuel_consumption_rate_rps = self._p2p_main_obj.fuel_consumption_rate_rps
        self._water_consumption_rate_rps = self._p2p_main_obj.water_consumption_rate_rps
        self._thermal_power_consumption_rate_rps = self._p2p_main_obj.thermal_power_consumption_rate_rps
        self._rps_total_variable_opex = self._opex_var_rps + self._fuel_consumption_rate_rps*self._fuel_cost + self._water_consumption_rate_rps*self._water_cost + self._thermal_power_consumption_rate_rps*self._thermal_power_cost


        ## Get Bypass parameter:
        self._bypass_operation_enabled = self._p2p_main_obj.bypass_operation_enabled
        self._rcs_bypass_installed_power = self._p2p_main_obj.nominal_power_bypass_rcs
        self._opex_var_bypass_rcs = self._p2p_main_obj.opex_var_bypass_rcs
        self._resource_rate_bypass_rcs = self._p2p_main_obj.resource_rate_bypass_rcs
        self._fuel_consumption_rate_bypass_rcs = self._p2p_main_obj.fuel_consumption_rate_bypass_rcs
        self._water_consumption_rate_bypass_rcs = self._p2p_main_obj.water_consumption_rate_bypass_rcs
        self._thermal_power_consumption_rate_bypass_rcs = self._p2p_main_obj.thermal_power_consumption_rate_bypass_rcs
        self._rcs_bypass_total_variable_opex = self._opex_var_bypass_rcs + get_rate(self._fuel_consumption_rate_bypass_rcs, load_frac = 1, T = 15, RH = 0)*self._fuel_cost + self._water_consumption_rate_bypass_rcs*self._water_cost + self._thermal_power_consumption_rate_bypass_rcs*self._thermal_power_cost
        
        self._rps_bypass_installed_power = self._p2p_main_obj.nominal_power_bypass_rps
        self._opex_var_bypass_rps = self._p2p_main_obj.opex_var_bypass_rps
        self._resource_rate_bypass_rps = self._p2p_main_obj.resource_rate_bypass_rps
        self._fuel_consumption_rate_bypass_rps = self._p2p_main_obj.fuel_consumption_rate_bypass_rps
        self._water_consumption_rate_bypass_rps = self._p2p_main_obj.water_consumption_rate_bypass_rps
        self._thermal_power_consumption_rate_bypass_rps = self._p2p_main_obj.thermal_power_consumption_rate_bypass_rps
        self._rps_bypass_total_variable_opex = self._opex_var_bypass_rps + self._fuel_consumption_rate_bypass_rps*self._fuel_cost + self._water_consumption_rate_bypass_rps*self._water_cost + self._thermal_power_consumption_rate_bypass_rps*self._thermal_power_cost

        ## RCS Only:
        self._rcs_only_operation_enabled = self._p2p_main_obj.rcs_only_operation_enabled
        self._rcs_only_installed_power = self._p2p_main_obj.nominal_power_only_rcs
        self._opex_var_only_rcs = self._p2p_main_obj.opex_var_only_rcs
        self._fuel_consumption_rate_only_rcs = self._p2p_main_obj.fuel_consumption_rate_only_rcs
        self._water_consumption_rate_only_rcs = self._p2p_main_obj.water_consumption_rate_only_rcs
        self._thermal_power_consumption_rate_only_rcs = self._p2p_main_obj.thermal_power_consumption_rate_only_rcs
        self._rcs_only_total_variable_opex = self._opex_var_only_rcs + get_rate(self._fuel_consumption_rate_only_rcs, load_frac = 1, T = 15, RH = 0)*self._fuel_cost + self._water_consumption_rate_only_rcs*self._water_cost + self._thermal_power_consumption_rate_only_rcs*self._thermal_power_cost
        
            
            
        ## Get Resource Storage Subsystem:
        if inputs.resource_inlet_annual_distribution_file is not None:
            self._resource_inlet_flow_obj = ResourceAvailabilityData(inputs.resource_inlet_annual_distribution_file, self._project_year_start, self._project_life)
        
        ## Get Electricity Price data
        self._electricity_tax = inputs.electricity_tax #%
        self._margin_tradingcompany_power = inputs.margin_tradingcompany_power
        self._electricity_price_data_obj = ElectricityPriceData(self._project_life, price_mean_modifier, price_std_modifier, price_minimum , PPA, subsidy_per_mwh, PPA_sales)
        self._weather_data_obj = WeatherData( self._project_year_start, self._project_life)
        
        ## initialize trading and retrieve necessary data
        #TODO: definir bypass_variables
        self._rcs_bypass_total_variable_opex = self._rcs_bypass_total_variable_opex
        self._rps_bypass_installed_power = self._rps_bypass_installed_power
        self._rps_bypass_total_variable_opex = self._rps_bypass_total_variable_opex
        self._trading_obj = Trading(self._rcs_installed_power,
                                    self._rcs_total_variable_opex,
                                    self._rcs_bypass_total_variable_opex,
                                    self._rps_installed_power,
                                    self._bypass_operation_enabled,
                                    self._rps_bypass_installed_power,
                                    self._rps_total_variable_opex,
                                    self._rps_bypass_total_variable_opex,
                                    self._rcs_only_operation_enabled,
                                    self._rcs_only_total_variable_opex,
                                    rss_day_0,
                                    rss_capacity=storage_capacity)

        self._trading_data_dict = self._trading_obj.get_data_dict()

        ## Load forecast / targets data if forecasting is enabled
        if electricity_price_forecasting:
            self._forecast_df = self._load_forecast_data()
            self._targets_df  = self._load_targets_data()
            print(f"[Forecasting] Enabled — forecast: {forecast_file}, column: {forecast_column}")
            print(f"[Forecasting] Settlement file: {targets_file}, column: {settlement_column}")

        ## Perform Calculation
        self._number_years_to_calculate = inputs.number_years_to_calculate
        self._project_operations_df = self._calculate_project_operations_df()
        self._project_monthly_stats_df = self._calculate_project_monthly_stats_df()
        self._project_yearly_stats_df = self._calculate_project_yearly_stats_df()
        self.write_results_data()
        self._calculate_storage_histogram(self._project_operations_df)


    def get_total_capex(self, rss_level_max = storage_capacity):
        print(rss_level_max)
        land_cost_specific = inputs.land_cost ## E/ha
        installed_power = max(self._rps_installed_power, self._rcs_installed_power)
        electrical_subsystem_cost = inputs.electrical_subsystem_specific_cost*installed_power*1000 
        f_contingencies = inputs.contingencies_factor/100
        f_indirect = inputs.indirect_cost_factor/100
        f_owner_costs = inputs.owner_cost_factor/100
        total_cost = self._p2p_main_obj.get_capex_rcs()  + self._p2p_main_obj.get_capex_rps() + self._p2p_main_obj.get_capex_rss(rss_level_max) + inputs.other_direct_capex
        indirect_cost = total_cost*f_indirect
        EPC_cost = total_cost+indirect_cost
        footprint = self._p2p_main_obj.get_footprint(rss_level_max) #m2
        land_cost = land_cost_specific*footprint/10**5 ## €/m2 * ha
        total_capex = EPC_cost+EPC_cost*f_owner_costs+land_cost+electrical_subsystem_cost+EPC_cost*f_contingencies
        file_path = 'Results//capex_report.txt'
        with open(file_path, 'w') as file:
            file.write('Footprint:\t{} ha\n'.format(footprint/10**5))
            file.write('Cost RCS:\t{} M€\n'.format(self._p2p_main_obj.get_capex_rcs()/10**6))
            file.write('Cost RPS:\t{} M€\n'.format(self._p2p_main_obj.get_capex_rps()/10**6))
            file.write('Cost RSS:\t{} M€\n'.format(self._p2p_main_obj.get_capex_rss(rss_level_max)/10**6))
            file.write('Total Cost:\t{} Eur\n'.format(total_cost/10**6))
            file.write('Indirect Cost:\t{} M€\n'.format(total_cost*(f_indirect)/10**6))
            file.write('Owner Cost:\t{} M€\n'.format(EPC_cost*f_owner_costs/10**6))
            file.write('Land Cost:\t{} M€\n'.format(land_cost/10**6))
            file.write('Electrical subsystem Cost:\t{} M€\n'.format(electrical_subsystem_cost/10**6))
            file.write('Contingencies:\t{} M€\n'.format((EPC_cost*f_contingencies/10**6)))
            file.write('Total Capex:\t{} M€\n'.format(total_capex/10**6))
        
        return total_capex

    def get_project_operations_df(self):
        return self._project_operations_df

    def get_project_monthly_stats_df(self):
        return self._project_monthly_stats_df

    def get_project_yearly_stats_df(self):
        return self._project_yearly_stats_df
    

    def _calculate_project_operations_df(self):
        rss_start = self.rss_day_0
        project_operation_df = pd.DataFrame()

        ## initialise system efficiency/ conversion rates
        rps_efficiency = get_rate(self._resource_rate_rps)
        rcs_efficiency = get_rate(self._resource_rate_rcs, load_frac = 1, T = 15, RH = 0)
        rps_efficiency_bypass = get_rate(self._resource_rate_bypass_rps)
        rcs_efficiency_bypass = get_rate(self._resource_rate_bypass_rcs, load_frac = 1, T = 15, RH = 0)
        weather_data_df = self._weather_data_obj.get_weather_data_df()
        if inputs.resource_inlet_annual_distribution_file is not None:
            resource_input_flow_df = self._resource_inlet_flow_obj.get_resource_data_df()
        else:
            resource_input_flow_df = []
            
        if PPA is not None:
            self._electricity_price_data_obj.update_spot_price1_PPA_from_weather_df(PPA, weather_data_df)
        electricity_price_df = self._electricity_price_data_obj.get_electricity_price_df()
        
        #for year_count in range(self._project_life):
        for year_count in range(self._number_years_to_calculate):
            print('Computing year {}/{}. Total project lifetime of {} years.'.format(year_count+1, self._number_years_to_calculate, self._project_life))

            ## estimate system efficiency/ conversion rates if available, otherwise use latest available stored value
            rps_efficiency = self._p2p_main_obj.get_rps_efficiency() if self._p2p_main_obj.get_rps_efficiency() else rps_efficiency
            rcs_efficiency = self._p2p_main_obj.get_rcs_efficiency() if self._p2p_main_obj.get_rcs_efficiency() else rcs_efficiency

            ## get only the price data for the relevant year + the subsiquent year (this takes into account the transition at the end of each year)
            electricity_price_period_df = electricity_price_df[(electricity_price_df.Year ==self._project_year_start + year_count) | (electricity_price_df.Year == self._project_year_start + year_count + 1)].reset_index(drop=True)
            #weather_data_period_df = weather_data_df[(electricity_price_df.Year ==self._project_year_start + year_count) | (electricity_price_df.Year == self._project_year_start + year_count + 1)].reset_index(drop=True)
            weather_data_period_df = weather_data_df[(weather_data_df.Year == self._project_year_start + year_count) |     (weather_data_df.Year == self._project_year_start + year_count + 1)].reset_index(drop=True)
            if isinstance(resource_input_flow_df, list) and not resource_input_flow_df:
                resource_input_flow_period_df = []
            else:
                resource_input_flow_period_df = resource_input_flow_df[(resource_input_flow_df.Year == self._project_year_start + year_count) |     (resource_input_flow_df.Year == self._project_year_start + year_count + 1)].reset_index(drop=True)

            annual_operations_df = self._calculate_annual_operation_df(electricity_price_period_df, resource_input_flow_period_df, weather_data_period_df, rss_start, rps_efficiency, rcs_efficiency,rps_efficiency_bypass, rcs_efficiency_bypass)
            project_operation_df = pd.concat([project_operation_df, annual_operations_df]).reset_index(drop=True)
            rss_start = project_operation_df['rss'].iloc[-1]
            
        project_operation_df = self.extend_dataframe_project_life(project_operation_df, self._project_life)
        return project_operation_df


    def _calculate_annual_operation_df(self, electricity_price_df, resource_input_flow_df, weather_data_df, rss_year_day_0, rps_efficiency, rcs_efficiency,rps_efficiency_bypass, rcs_efficiency_bypass):
        annual_operation_df = pd.DataFrame()
        annual_consolidated_resource_inlet_flow_list = []
        annual_consolidated_resource_inlet_power_consumption_list = []
        
        rss_start = rss_year_day_0
        time1 = time.time()
        
        for day_count in progressbar(range(365), "Computing Daily operations: ", 36):
        ## for day_count in range(365):
            ## call Trading class
            
            start = day_count * 24
            end = day_count * 24 + sample_period_days * 24
            if isinstance(resource_input_flow_df, list) and not resource_input_flow_df:
                resource_input_flow_sample_df = []  # Lista de ceros con la misma longitud
            else:
                resource_input_flow_sample_df = resource_input_flow_df[(resource_input_flow_df.index >= start) & (resource_input_flow_df.index < end)]
            weather_data_sample_df = weather_data_df[(weather_data_df.index >= start) & (weather_data_df.index < end)]

            if electricity_price_forecasting:
                # Use forecast prices for trading decisions.
                # Actual (settlement) prices are applied after the annual loop via targets_file.
                actual_slice = electricity_price_df[(electricity_price_df.index >= start) & (electricity_price_df.index < end)]
                sim_date = electricity_price_df.iloc[start]['DateTime'].date()
                sample_period_df = self._get_forecast_prices_for_day(sim_date, actual_slice)
            else:
                sample_period_df = electricity_price_df[(electricity_price_df.index >= start) & (electricity_price_df.index < end)]

            #TODO: crear rcs_efficiency_bypass, rps_efficiency_bypass
            self._trading_obj.run(sample_period_df, resource_input_flow_sample_df, weather_data_sample_df, day_count, rss_start, rps_efficiency, rcs_efficiency, rps_efficiency_bypass, rcs_efficiency_bypass)
            #self._trading_obj.run(electricity_price_df, resource_input_flow_df, weather_data_df, day_count, rss_start, rps_efficiency, rcs_efficiency)
            consolidated_operation_df = self._trading_obj.get_consolidated_operation_df()
            consolidated_resource_inlet_flow_list = self._trading_obj.get_consolidated_resource_inlet_flow_list()
            consolidated_resource_inlet_power_consumption_list = self._trading_obj.get_consolidated_resource_inlet_power_consumption_list()

            annual_operation_df = pd.concat([annual_operation_df, consolidated_operation_df])
            annual_consolidated_resource_inlet_flow_list += consolidated_resource_inlet_flow_list
            annual_consolidated_resource_inlet_power_consumption_list += consolidated_resource_inlet_power_consumption_list
            ## Reset real rss level for the following iteration
            aggregated_operation_df = self._calculate_aggregated_operations_df(consolidated_operation_df.copy(), consolidated_resource_inlet_flow_list, consolidated_resource_inlet_power_consumption_list, weather_data_df, rss_start)
            rss_start = aggregated_operation_df['rss'].iloc[-1]
            rps_efficiency = self._p2p_main_obj.get_rps_efficiency() if self._p2p_main_obj.get_rps_efficiency() else rps_efficiency
            rcs_efficiency = self._p2p_main_obj.get_rcs_efficiency() if self._p2p_main_obj.get_rcs_efficiency() else rcs_efficiency
            rps_efficiency_bypass = self._p2p_main_obj.get_bypass_rps_efficiency() if self._p2p_main_obj.get_bypass_rps_efficiency() else rps_efficienc_bypass
            rcs_efficiency_bypass = self._p2p_main_obj.get_bypass_rcs_efficiency() if self._p2p_main_obj.get_bypass_rcs_efficiency() else rcs_efficiency_bypass

        time2 = time.time()
        print('Computing Daily operations completed in', time2-time1, 'seconds')

        print('Finalizing annual operations...',  end='\r')
        print(min(annual_consolidated_resource_inlet_flow_list))
        annual_operations_df = self._calculate_aggregated_operations_df(annual_operation_df.copy(), annual_consolidated_resource_inlet_flow_list, annual_consolidated_resource_inlet_power_consumption_list, weather_data_df, rss_year_day_0).join(electricity_price_df)

        # When forecasting is active, replace Spot_Price1/Spot_Price2 with actual settlement
        # prices from targets_file before computing cashflows.
        if electricity_price_forecasting:
            annual_operations_df = self._apply_settlement_prices(annual_operations_df)

        water_consumption_list_rcs = self._p2p_main_obj.get_water_consumption_from_rcs() #m3/h
        annual_operations_df["water_consumption_rcs"] = water_consumption_list_rcs
        fuel_consumption_list_rcs = self._p2p_main_obj.get_fuel_consumption_from_rcs() #MWh/h
        annual_operations_df["fuel_consumption_rcs"] = fuel_consumption_list_rcs
        water_consumption_list_rps = self._p2p_main_obj.get_water_consumption_from_rps() #m3/h
        annual_operations_df["water_consumption_rps"] = water_consumption_list_rps
        fuel_consumption_list_rps = self._p2p_main_obj.get_fuel_consumption_from_rps() #MWh/h
        annual_operations_df["fuel_consumption_rps"] = fuel_consumption_list_rps

        thermal_power_consumption_list = self._p2p_main_obj.get_thermal_power_consumption() #MWht/h
        annual_operations_df["thermal_power_consumption"] = thermal_power_consumption_list
        resource_inlet_list = self._p2p_main_obj.get_actual_resource_inlet_flow_list() #unit/h
        annual_operations_df["resource_inlet"] = resource_inlet_list
        rss_max_level = annual_operations_df['rss'].max()
        annual_operations_df = self._calculate_cashflow(annual_operations_df, weather_data_df, rss_max_level)

        time3 = time.time()
        print('Finalizing annual operations completed in', time3-time2, 'seconds', '\n')
        return annual_operations_df

    # ------------------------------------------------------------------
    # Forecasting helpers
    # ------------------------------------------------------------------

    def _load_forecast_data(self):
        """Load the forecast CSV (168h or 24h model) from MainData/."""
        path = os.path.join("MainData", forecast_file)
        df = pd.read_csv(path, parse_dates=['time', 'window_start'])
        # Normalise window_start to date-only Timestamps for reliable lookup
        df['window_start'] = df['window_start'].dt.normalize()
        return df

    def _load_targets_data(self):
        """Load the targets CSV (actual market prices) from MainData/ for settlement."""
        path = os.path.join("MainData", targets_file)
        # targets.csv datetime format is M/D/YYYY H:MM  (e.g. 1/1/2024 0:00)
        df = pd.read_csv(path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df

    def _get_forecast_prices_for_day(self, sim_date, actual_price_slice):
        """
        Build a sample_period_df using forecast prices for trading decisions.

        For each simulation day the matching forecast window is found by
        window_start == sim_date.  Spot_Price2 (raw sell price) is replaced by
        the forecast column value; Spot_Price1 (buy price) is adjusted
        proportionally to preserve any toll/tax premium baked into the
        original electricity_price_df slice.

        Falls back to actual prices with a warning when no window is found.

        Args:
            sim_date  : datetime.date — calendar date of the simulation day
            actual_price_slice : DataFrame slice from electricity_price_df
        Returns:
            DataFrame with same index/columns as actual_price_slice
        """
        date_key = pd.Timestamp(sim_date)
        window_df = self._forecast_df[self._forecast_df['window_start'] == date_key]

        if window_df.empty:
            print(f"[Forecasting] WARNING: no forecast window for {sim_date}; using actual prices.")
            return actual_price_slice

        n_hours = sample_period_days * 24
        forecast_prices = window_df.head(n_hours)[forecast_column].values

        if len(forecast_prices) < len(actual_price_slice):
            print(f"[Forecasting] WARNING: forecast for {sim_date} has only "
                  f"{len(forecast_prices)} hours (needed {n_hours}); using actual prices.")
            return actual_price_slice

        sample_df = actual_price_slice.copy()
        n_rows = len(sample_df)

        # Preserve the buy-price premium (tolls / taxes) from the original data
        orig_sp2 = actual_price_slice['Spot_Price2'].values
        orig_sp1 = actual_price_slice['Spot_Price1'].values
        buy_premium = orig_sp1 - orig_sp2

        sample_df['Spot_Price2'] = forecast_prices[:n_rows]
        sample_df['Spot_Price1'] = forecast_prices[:n_rows] + buy_premium
        return sample_df

    def _apply_settlement_prices(self, annual_operations_df):
        """
        Replace Spot_Price1/Spot_Price2 in annual_operations_df with actual
        settlement prices from targets_file.  Called after operations are
        computed, before cashflow calculation.

        Spot_Price2 (raw sell price) is set to settlement_column from targets.
        Spot_Price1 (buy price) is updated by the same additive delta so the
        toll/tax premium is preserved.

        Rows whose datetime is not found in targets fall back to the existing
        (electricity_price_df) values silently.
        """
        df = annual_operations_df.copy()

        # Rebuild datetime from Year/Month/Day/Hour (added via join with electricity_price_df)
        dt_col = pd.to_datetime({
            'year':  df['Year'].astype(int),
            'month': df['Month'].astype(int),
            'day':   df['Day'].astype(int),
            'hour':  df['Hour'].astype(int),
        })

        targets_map = self._targets_df.set_index('datetime')[settlement_column]
        settlement_prices = pd.Series(
            [targets_map.get(dt, np.nan) for dt in dt_col],
            index=df.index,
            dtype=float,
        )

        valid_mask = settlement_prices.notna()
        if valid_mask.any():
            buy_premium = df['Spot_Price1'] - df['Spot_Price2']
            df.loc[valid_mask, 'Spot_Price2'] = settlement_prices[valid_mask].values
            df.loc[valid_mask, 'Spot_Price1'] = (
                df.loc[valid_mask, 'Spot_Price2'] + buy_premium[valid_mask]
            )
            n_matched = valid_mask.sum()
            print(f"[Forecasting] Settlement prices applied to {n_matched}/{len(df)} hours "
                  f"from '{settlement_column}' column.")
        else:
            print("[Forecasting] WARNING: no settlement prices matched from targets file; "
                  "cashflow will use forecast prices.")

        return df

    # ------------------------------------------------------------------

    def _calculate_aggregated_operations_df(self, origin_operation_df, resource_input_flow, resource_inlet_power_consumption_list,  weather_data_df, rss_start):
        ## calculate production/consuption per minute (before correction by factor of 60)  Note: ~24s
        origin_operation_df['temp_key'] = pd.to_datetime(origin_operation_df[['Year', 'Month', 'Day', 'Hour']])
        weather_data_df['temp_key'] = pd.to_datetime(weather_data_df[['Year', 'Month', 'Day', 'Hour']])
        #resource_input_flow_df['temp_key'] = pd.to_datetime(resource_input_flow_df[['Year','Month','Day','Hour']])
        # Realizar un merge para filtrar datos basado en la coincidencia de la clave temporal
        filtered_weather_data_df = pd.merge(
            weather_data_df,
            origin_operation_df['temp_key'],
            on='temp_key',
            how='inner'
        )
        # filtered_resource_input_flow_df = pd.merge(
        #     resource_input_flow_df,
        #     origin_operation_df['temp_key'],
        #     on='temp_key',
        #     how='inner'
        # )
        # Extraer las listas necesarias
        #resource_input_flow = filtered_resource_input_flow_df["Resource_Available"].tolist()
        temperature = filtered_weather_data_df["Temperature"].tolist()
        relative_humidity = filtered_weather_data_df["Relative Humidity"].tolist()
        
        # Opcional: limpiar y eliminar las columnas temporales si fueron creadas en el DataFrame original
        origin_operation_df.drop('temp_key', axis=1, inplace=True)
        weather_data_df.drop('temp_key', axis=1, inplace=True)
        #resource_input_flow_df.drop('temp_key', axis=1, inplace=True)
        real_resource_consumption_extended_list, buy_list, sell_list, real_electricity_supplied_list, real_electricity_consumption_list = self._calculate_real_resource_consumption_list(origin_operation_df, resource_input_flow, resource_inlet_power_consumption_list, temperature, relative_humidity, rss_start)

        ## aggregate minute into hours and perform corrections
        new_dict = {}
        index_start = origin_operation_df.index.values[0]

        # for i in range(0, len(real_resource_consumption_extended_list), 60):
        #     new_dict[int((index_start*60+i)/60)] = {
        #         'energy': sum(buy_list[i:i + 60]) / 60 - sum(sell_list[i:i + 60]) / 60,
        #         'resource_delta': sum(real_resource_consumption_extended_list[i:i + 60]) / 60,
        #         'action': origin_operation_df.loc[int((index_start*60+i)/60), 'action']
        #     }
            
        for i in range(0, len(real_resource_consumption_extended_list)):
            new_dict[i] = {
                #'energy': buy_list[i] - sell_list[i],
                'energy': real_electricity_consumption_list[i] - real_electricity_supplied_list[i],
                'resource_delta': real_resource_consumption_extended_list[i],
                #'action': origin_operation_df.loc[index_start+i, 'action']
                'action_charging': origin_operation_df.loc[index_start+i,'action_charging'],
                'action_discharging': origin_operation_df.loc[index_start+i,'action_discharging'],
            }
            #print(f"net_resource_consumption: {real_resource_consumption_extended_list[i]}")
        ## create final dataframe
        aggregated_df = pd.DataFrame.from_dict(new_dict, orient='index')
        aggregated_df = aggregated_df.join(origin_operation_df[['Temperature', 'Relative_Humidity', 'marginal_cost_buy','marginal_cost_accept','marginal_cost_buy_bypass','marginal_cost_rcs_only']])
        aggregated_df = aggregated_df.join(calculate_rss_series(aggregated_df['resource_delta'].copy(), rss_start), how='left')
        return aggregated_df

    def _calculate_real_resource_consumption_list(self, operation_df, resource_input_flow,resource_inlet_power_consumption_list, temperature, relative_humidity, rss_start):

        ## get the format requirred by the P2P software
        #buy_series = operation_df.loc[:, "energy"].copy()
        buy_series = operation_df.loc[:, "energy_purchased"].copy()
        mask = buy_series < 0
        buy_series.loc[mask] = 0
        #buy_list = self._calculate_extended_operation_list(buy_series, machine='ely')
        buy_list = buy_series.tolist()
        #sell_series = operation_df.loc[:, "energy"].copy()
        sell_series = operation_df.loc[:, "energy_sold"].copy()
        mask = sell_series >= 0
        sell_series.loc[mask] = 0
        sell_list = [-sell if sell < 0 else 0 for sell in sell_series.tolist()]
        ## call P2P class
        p2p_obj_instance = self._p2p_main_obj
        p2p_obj_instance.run(buy_list, sell_list, resource_input_flow,resource_inlet_power_consumption_list, [], temperature, relative_humidity, rss_start)
        
        return p2p_obj_instance.get_net_resource_list(), buy_list, sell_list, p2p_obj_instance.get_electricity_supplied_list(), p2p_obj_instance.get_electricity_consumption_list()

    def _calculate_extended_operation_list(self, origin_operation_series, machine):
        if self._ramp_rate_method == '1':
            return self._extend_operation_list_method_1(origin_operation_series, machine)
        elif self._ramp_rate_method == '2':
            return self._extend_operation_list_method_2(origin_operation_series, machine)

    def _extend_operation_list_method_1(self, origin_operation_series, machine):
        new_list = []
        index_start = origin_operation_series.index.values[0]
        index_stop = origin_operation_series.index.values[-1]

        ramp_up, ramp_down = self._retrieve_ramp_rates(machine)

        for i in range(index_start, index_stop, 1):
            gap = origin_operation_series[i + 1] - origin_operation_series[i]

            if gap / min(ramp_up, abs(ramp_down)) > 30:
                raise Exception

            # first 30' of the first day
            if i <= origin_operation_series.index.start:
                new_list += [origin_operation_series[i]] * 30

            if 0 <= gap < ramp_up or ramp_down < gap < 0:
                new_list += [origin_operation_series[i]] * 30 + [origin_operation_series[i + 1]] * 30
            elif gap > 0 and gap > ramp_up:
                new_list += ([origin_operation_series[i]] * (30 - round(gap / ramp_up / 2)) +
                             [origin_operation_series[i] + ramp_up * j for j in range(math.ceil(gap / ramp_up))] +
                             [origin_operation_series[i + 1]] * (30 - math.ceil(gap / ramp_up / 2)))
            elif gap < 0 and gap < ramp_down:
                new_list += ([origin_operation_series[i]] * (30 - round(gap / ramp_down / 2)) +
                             [origin_operation_series[i] + ramp_down * j for j in range(math.ceil(gap / ramp_down))] +
                             [origin_operation_series[i + 1]] * (30 - math.ceil(gap / ramp_down / 2)))
            else:
                raise Exception
            # last 30' of the last day
            if i == index_stop - 1:
                new_list += [origin_operation_series[i + 1]] * 30

        # return pd.DataFrame(new_list,  columns=['energy'])
        return new_list

    def _extend_operation_list_method_2(self, origin_operation_series, machine):
        new_list = []
        index_start = origin_operation_series.index.values[0]
        index_stop = origin_operation_series.index.values[-1]

        ramp_up, ramp_down = self._retrieve_ramp_rates(machine)

        for i in range(index_start, index_stop, 1):
            gap = origin_operation_series[i + 1] - origin_operation_series[i]

            if gap / min(ramp_up, abs(ramp_down)) > 30:
                raise Exception('ERROR: Operations._extend_operation_list_method_2 cannot be performed,'
                                ' gap / min(ramp_up, abs(ramp_down)) > 30min \n'
                                ' gap: {}, gap / min(ramp_up, abs(ramp_down)): '.format(
                    gap, gap / min(ramp_up, abs(ramp_down))))

            # first 30' of the first day
            if i <= index_start:
                new_list += [origin_operation_series[i]] * 30

            if 0 <= gap < ramp_up or ramp_down < gap < 0:
                new_list += [origin_operation_series[i]] * 30 + [origin_operation_series[i + 1]] * 30
            elif gap > 0 and gap > ramp_up:
                new_list += ([origin_operation_series[i]] * (30 - round(gap / ramp_up)) +
                             [origin_operation_series[i] + ramp_up * j for j in range(math.ceil(gap / ramp_up))] +
                             [origin_operation_series[i + 1]] * 30)
            elif gap < 0 and gap < ramp_down:
                new_list += ([origin_operation_series[i]] * 30 +
                             [origin_operation_series[i] + ramp_down * j for j in range(math.ceil(gap / ramp_down))] +
                             [origin_operation_series[i + 1]] * (30 - math.ceil(gap / ramp_down)))
            else:
                raise Exception
            # last 30' of the last day
            if i == index_stop - 1:
                new_list += [origin_operation_series[i + 1]] * 30

        # return pd.DataFrame(new_list, columns=['energy'])
        return new_list

    
    def _calculate_cashflow(self, operations_df, weather_data_df, rss_level_max = storage_capacity):
        ## Trading Cashflow
        buy_tax = 1 + self._trading_data_dict['buy_taxes_perc']
        feed_mult = self._trading_data_dict['feed_in_multiplier']
        feed_supp = self._trading_data_dict['feed_in_supplement']
        
        energy_sold = operations_df['energy'].apply(lambda x: x if x < 0 else 0)
        energy_purchased = operations_df['energy'].apply(lambda x: x if x > 0 else 0)
        incomes = -energy_sold * (operations_df['Spot_Price2'] * feed_mult + feed_supp)
        sales =  energy_purchased * (operations_df['Spot_Price1'] * buy_tax)
        
        operations_df['Trading_Cashflow'] = incomes - sales

        operations_df['Electricity_sold_earnings'] = operations_df['Trading_Cashflow'].apply(lambda x: x if x > 0 else 0)
        operations_df['Electricity_purchased_cost'] = operations_df['Trading_Cashflow'].apply(lambda x: x if x < 0 else 0)
        # Calcula los ingresos de venta y los costes de compra basados en el signo de 'energy'
        operations_df['Electricity_sold_earnings'] = operations_df.apply(lambda x: x['Trading_Cashflow'] if x['energy'] < 0 else 0, axis=1)
        operations_df['Electricity_purchased_cost'] = operations_df.apply(lambda x: x['Trading_Cashflow'] if x['energy'] > 0 else 0, axis=1)

        ## Opex Cashflow
        rcs_variable_opex_series = operations_df.energy.apply(lambda x: (-self._opex_var_rcs*x if x<0 else 0))
        rcs_fuel_consumption_series = operations_df.fuel_consumption_rcs.apply(lambda x: self._fuel_cost*x)
        rcs_water_consumption_series = operations_df.water_consumption_rcs.apply(lambda x: self._water_cost*x)
        rcs_startup_cost_series = self._calculate_operational_data_stats_df(operations_df)['rcs_startups'] * self._start_up_cost_rcs 
        operations_df['RCS_OpEx_Cashflow'] = -rcs_variable_opex_series -self._opex_fix_rcs/365/24 - rcs_fuel_consumption_series - rcs_water_consumption_series - rcs_startup_cost_series

        rps_variable_opex_series = operations_df.energy.apply(lambda x: (self._opex_var_rps*x if x>0 else 0))
        rps_fuel_consumption_series = operations_df.fuel_consumption_rps.apply(lambda x: self._fuel_cost*x)
        rps_water_consumption_series = operations_df.water_consumption_rps.apply(lambda x: self._water_cost*x)
        operations_df['RPS_OpEx_Cashflow'] = -rps_variable_opex_series + -self._opex_fix_rps/365/24 - rps_water_consumption_series - rps_fuel_consumption_series
        
        rss_resource_inlet_consumption_series = operations_df.resource_inlet.apply(lambda x: self._resource_inlet_cost*x)
        operations_df['RSS_Cashflow'] = - self._p2p_main_obj.get_opex_fix_rss(rss_level_max)/365/24 - rss_resource_inlet_consumption_series
        if PPA == None:
            fixed_toll = self._calculate_power_term_grid_toll(operations_df.copy())
        else:
            fixed_toll = self._calculate_power_term_grid_toll_with_PPA(operations_df.copy(), weather_data_df.copy())
        #fixed_toll = self._calculate_power_term_grid_toll(operations_df.copy()) 
        operations_df['Grid_Toll_Cashflow'] = -fixed_toll/365/25
        

        operations_df['EBITDA'] = operations_df['Trading_Cashflow']+operations_df['RCS_OpEx_Cashflow']+operations_df['RPS_OpEx_Cashflow']+operations_df['RSS_Cashflow']+operations_df['Grid_Toll_Cashflow']
        return operations_df

    def _calculate_cashflow_old(self, operations_df, weather_data_df, rss_level_max = storage_capacity):
        ## Trading Cashflow
        operations_df['energy'] = operations_df['energy_purchased'] - operations_df['energy_sold']
        temp_mult_series = operations_df.action_charging.apply(lambda x: (1+self._trading_data_dict['buy_taxes_perc'] if 'buy' in x else self._trading_data_dict['feed_in_multiplier']))
        temp_add_series = operations_df.action_discharging.apply(lambda x: (self._trading_data_dict['feed_in_supplement'] if 'sell' in x else 0))
        temp_spot_price = operations_df.apply(lambda x: x['Spot_Price1'] if 'buy' in x['action'] else x['Spot_Price2'], axis=1)
        operations_df['Trading_Cashflow'] = -operations_df.energy * (temp_mult_series * temp_spot_price + temp_add_series)
        operations_df['Electricity_sold_earnings'] = operations_df['Trading_Cashflow'].apply(lambda x: x if x > 0 else 0)
        operations_df['Electricity_purchased_cost'] = operations_df['Trading_Cashflow'].apply(lambda x: x if x < 0 else 0)
        # Calcula los ingresos de venta y los costes de compra basados en el signo de 'energy'
        operations_df['Electricity_sold_earnings'] = operations_df.apply(lambda x: x['Trading_Cashflow'] if x['energy'] < 0 else 0, axis=1)
        operations_df['Electricity_purchased_cost'] = operations_df.apply(lambda x: x['Trading_Cashflow'] if x['energy'] > 0 else 0, axis=1)
    
        ## Opex Cashflow
        rcs_variable_opex_series = operations_df.energy.apply(lambda x: (-self._opex_var_rcs*x if x<0 else 0))
        rcs_fuel_consumption_series = operations_df.fuel_consumption_rcs.apply(lambda x: self._fuel_cost*x)
        rcs_water_consumption_series = operations_df.water_consumption_rcs.apply(lambda x: self._water_cost*x)
        rcs_startup_cost_series = self._calculate_operational_data_stats_df(operations_df)['rcs_startups'] * self._start_up_cost_rcs 
        operations_df['RCS_OpEx_Cashflow'] = -rcs_variable_opex_series -self._opex_fix_rcs/365/24 - rcs_fuel_consumption_series - rcs_water_consumption_series - rcs_startup_cost_series
    
        rps_variable_opex_series = operations_df.energy.apply(lambda x: (self._opex_var_rps*x if x>0 else 0))
        rps_fuel_consumption_series = operations_df.fuel_consumption_rps.apply(lambda x: self._fuel_cost*x)
        rps_water_consumption_series = operations_df.water_consumption_rps.apply(lambda x: self._water_cost*x)
        operations_df['RPS_OpEx_Cashflow'] = -rps_variable_opex_series + -self._opex_fix_rps/365/24 - rps_water_consumption_series - rps_fuel_consumption_series
        
        rss_resource_inlet_consumption_series = operations_df.resource_inlet.apply(lambda x: self._resource_inlet_cost*x)
        operations_df['RSS_Cashflow'] = - self._p2p_main_obj.get_opex_fix_rss(rss_level_max)/365/24 - rss_resource_inlet_consumption_series
        if PPA == None:
            fixed_toll = self._calculate_power_term_grid_toll(operations_df.copy())
        else:
            fixed_toll = self._calculate_power_term_grid_toll_with_PPA(operations_df.copy(), weather_data_df.copy())
        #fixed_toll = self._calculate_power_term_grid_toll(operations_df.copy()) 
        operations_df['Grid_Toll_Cashflow'] = -fixed_toll/365/25
        
    
        operations_df['EBITDA'] = operations_df['Trading_Cashflow']+operations_df['RCS_OpEx_Cashflow']+operations_df['RPS_OpEx_Cashflow']+operations_df['RSS_Cashflow']+operations_df['Grid_Toll_Cashflow']
        return operations_df


    def _calculate_operational_data_stats_df(self, project_operations_df, zero_tol=0.0):
        # Vectorized detection of startups (returns per-row dataframe aligned to input index)
        e = project_operations_df['energy'].astype(float)
        if zero_tol and zero_tol > 0.0:
            e_proc = e.where(e.abs() > zero_tol, 0.0)
        else:
            e_proc = e
        prev = e_proc.shift(1, fill_value=0.0)
        rps_start = ((e_proc > 0.0) & (prev <= 0.0)).astype('int8')
        rcs_start = ((e_proc < 0.0) & (prev >= 0.0)).astype('int8')
        return pd.DataFrame({'rcs_startups': rcs_start, 'rps_startups': rps_start}, index=project_operations_df.index)
    
    
    def _calculate_project_monthly_stats_df(self):
        df = self._project_operations_df
    
        # If you don't want to modify the original DF (safer) keep copy; remove if memory is tight.
        df_local = df.copy()
    
        # Energy in / out columns (vectorized)
        df_local['Energy_In']  = df_local['energy'].where(df_local['energy'] > 0.0, 0.0)
        df_local['Energy_Out'] = df_local['energy'].where(df_local['energy'] < 0.0, 0.0)
    
        # Operational stats per-row (vectorized startup detection)
        op_stats_df = self._calculate_operational_data_stats_df(df_local)
        if op_stats_df is not None and not op_stats_df.empty:
            # join by index (fast)
            df_local = df_local.join(op_stats_df)
    
        # Agg dict: single-groupby pass
        agg_dict = {
            'Trading_Cashflow': 'sum',
            'Electricity_sold_earnings': 'sum',
            'Electricity_purchased_cost': 'sum',
            'RCS_OpEx_Cashflow': 'sum',
            'RPS_OpEx_Cashflow': 'sum',
            'RSS_Cashflow': 'sum',
            'Grid_Toll_Cashflow': 'sum',
            'EBITDA': 'sum',
            'Energy_In': 'sum',
            'Energy_Out': 'sum',
            # include startup counts if present
            'rps_startups': 'sum',
            'rcs_startups': 'sum',
        }
    
        monthly = df_local.groupby(['Year', 'Month'], sort=False).agg(agg_dict)
    
        # Derived columns with safe division
        denom_in  = monthly['Energy_In'].to_numpy()
        numer_in  = (-monthly['Electricity_purchased_cost']).to_numpy()
        monthly['avr_elec_price_purchase'] = np.divide(numer_in, denom_in, out=np.zeros_like(numer_in, dtype=float), where=denom_in != 0.0)
    
        denom_out = monthly['Energy_Out'].to_numpy()
        numer_out = (-monthly['Electricity_sold_earnings']).to_numpy()
        monthly['avr_elec_price_sell'] = np.divide(numer_out, denom_out, out=np.zeros_like(numer_out, dtype=float), where=denom_out != 0.0)
    
        monthly['aoh_rps (Est)'] = monthly['Energy_In'] / float(self._rps_installed_power)
        monthly['aoh_rcs (Est)'] = -monthly['Energy_Out'] / float(self._rcs_installed_power)
    
        return monthly
    
    
    def _calculate_project_yearly_stats_df(self):
        monthly_df = self._project_monthly_stats_df
        annual = monthly_df.groupby(level='Year', sort=False).sum()
    
        denom_in  = annual['Energy_In'].to_numpy()
        numer_in  = (-annual['Electricity_purchased_cost']).to_numpy()
        annual['avr_elec_price_purchase'] = np.divide(numer_in, denom_in, out=np.zeros_like(numer_in, dtype=float), where=denom_in != 0.0)
    
        denom_out = annual['Energy_Out'].to_numpy()
        numer_out = (-annual['Electricity_sold_earnings']).to_numpy()
        annual['avr_elec_price_sell'] = np.divide(numer_out, denom_out, out=np.zeros_like(numer_out, dtype=float), where=denom_out != 0.0)
    
        return annual




    def _calculate_project_monthly_stats_df_2(self):
        new_df = self._project_operations_df[['Month', 'Year', 'Trading_Cashflow','Electricity_sold_earnings','Electricity_purchased_cost', 'RCS_OpEx_Cashflow', 'RPS_OpEx_Cashflow', 'RSS_Cashflow', 'Grid_Toll_Cashflow','EBITDA']]
        energy_in_df = self._project_operations_df[self._project_operations_df.energy > 0]['energy'].rename('Energy_In')
        energy_out_df = self._project_operations_df[self._project_operations_df.energy < 0]['energy'].rename('Energy_Out')

        new_df = new_df.join(energy_in_df).fillna(0)
        new_df = new_df.join(energy_out_df).fillna(0)

        new_df = new_df.join(self._calculate_operational_data_stats_df(self._project_operations_df))

        new_df = new_df.groupby(['Year', 'Month']).sum()
        new_df['avr_elec_price_purchase'] = -new_df['Electricity_purchased_cost'] / new_df['Energy_In']
        new_df['avr_elec_price_sell'] = -new_df['Electricity_sold_earnings'] / new_df['Energy_Out']
        aoh_rps = new_df['Energy_In'] / self._rps_installed_power
        aoh_rcs = -new_df['Energy_Out'] / self._rcs_installed_power

        return new_df.join(aoh_rps.rename('aoh_rps (Est)')).join(aoh_rcs.rename('aoh_rcs (Est)'))

    def _calculate_project_yearly_stats_df_2(self):
        monthly_df = self._project_monthly_stats_df 
        annual_df = monthly_df.groupby('Year').sum()
        
        # Calculando el precio medio anual de compra y venta basado en las sumas mensuales
        annual_df['avr_elec_price_purchase'] = -annual_df['Electricity_purchased_cost'] / annual_df['Energy_In']
        annual_df['avr_elec_price_sell'] = annual_df['Electricity_sold_earnings'] / -annual_df['Energy_Out']
        
        return annual_df

    def _calculate_operational_data_stats_df_2(self, project_operations_df):

        rcs_startups_list = {}
        rps_startups_list = {}

        power_rcs_temp = 0
        power_rps_temp = 0

        for index, value in project_operations_df.iterrows():
            if value['energy'] > 0 and power_rps_temp == 0:
                rps_startups_list[index] = 1
                rcs_startups_list[index] = 0
                power_rcs_temp = 0
                power_rps_temp = value['energy']
            elif value['energy'] < 0 and power_rcs_temp == 0:
                rps_startups_list[index] = 0
                rcs_startups_list[index] = 1
                power_rcs_temp = value['energy']
                power_rps_temp = 0
            elif value['energy'] > 0 and power_rps_temp > 0:
                rps_startups_list[index] = 0
                rcs_startups_list[index] = 0
                power_rcs_temp = 0
                power_rps_temp = value['energy']
            elif value['energy'] < 0 and power_rcs_temp < 0:
                rps_startups_list[index] = 0
                rcs_startups_list[index] = 0
                power_rcs_temp = value['energy']
                power_rps_temp = 0
            else:
                rps_startups_list[index] = 0
                rcs_startups_list[index] = 0
                power_rcs_temp = 0
                power_rps_temp = 0

        return pd.DataFrame.from_dict({'rcs_startups': rcs_startups_list, 'rps_startups': rps_startups_list})



    def calculate_maximum_storage_capacity(self):
        return self._project_operations_df["rss"].max()

    def write_results_data(self):
        self._project_operations_df.to_csv('Results//daily_operation_df.csv')
        self._project_monthly_stats_df.to_csv('Results//monthly_operation_df.csv')
        self._project_yearly_stats_df.to_csv('Results//yearly_operation_df.csv')

    def plot_operations(self):
        #plt.figure()
        self._project_operations_df.plot(y='rss')
        plt.figure()
        self._project_operations_df['Trading_Cashflow'].cumsum().plot(y='cashflow')
        plt.show()


    def extend_dataframe_project_life(self, df, project_life, year_column="Year"):
        """
        Extiende un DataFrame replicando sus datos para cubrir un número total de años especificado.
        
        Parameters:
        - df (pd.DataFrame): DataFrame original que puede contener múltiples años.
        - year_column (str): Nombre de la columna que contiene el año en el DataFrame.
        - project_life (int): Total de años que el DataFrame final debería cubrir.
        
        Returns:
        - pd.DataFrame: DataFrame extendido.
        """
        # Determinar el rango inicial de años en el DataFrame
        initial_year = df[year_column].min()
        last_year = df[year_column].max()
        original_span = last_year - initial_year + 1
    
        # Crear una copia del DataFrame original para evitar modificarlo directamente
        extended_df = df.copy()
        
        # Calcular cuántas veces necesitamos repetir el bloque de años para alcanzar el project_life
        num_repeats = (project_life - 1) // original_span + 1
        
        # Repetir los años necesarios
        for n in range(1, num_repeats):
            temp_df = df.copy()
            increment = n * original_span
            temp_df[year_column] += increment
            extended_df = pd.concat([extended_df, temp_df], ignore_index=True)
    
        # Recortar el DataFrame extendido si excede el project_life
        extended_df = extended_df[extended_df[year_column] <= initial_year + project_life - 1]
        
        return extended_df
    
    def _calculate_storage_histogram(self, df):
        plt.figure(figsize=(10, 6))  # Ajusta el tamaño de la figura
        plt.hist(df['rss'], bins=50, color='blue', alpha=0.7)  # bins define la cantidad de intervalos
        plt.title('Histogram: resource storage usage')
        plt.xlabel('Resource unit')
        plt.ylabel('Frequency')
        plt.grid(True)
                
        # Guardar la figura con alta calidad
        plt.savefig('Results//histogram_storage_resource.png', format='png', dpi=300, bbox_inches='tight')
        #plt.show()
        #plt.close()
        
        percentil_100 = df['rss'].quantile(1)
        percentil_95 = df['rss'].quantile(0.95)
        percentil_90 = df['rss'].quantile(0.9)
        percentil_85 = df['rss'].quantile(0.85)
        percentil_80 = df['rss'].quantile(0.8)
        percentil_75 = df['rss'].quantile(0.75)
        percentil_70 = df['rss'].quantile(0.7)
        percentil_50 = df['rss'].quantile(0.5)
        
        with open('Results//Storage.txt', 'w') as file:
            file.write(f"The 100th percentile of the storage is: {percentil_100} unit\n")
            file.write(f"The 95th percentile of the storage is: {percentil_95} unit\n")
            file.write(f"The 90th percentile of the storage is: {percentil_90} unit\n")
            file.write(f"The 85th percentile of the storage is: {percentil_85} unit\n")
            file.write(f"The 80th percentile of the storage is: {percentil_80} unit\n")
            file.write(f"The 75th percentile of the storage is: {percentil_75} unit\n")
            file.write(f"The 70th percentile of the storage is: {percentil_70} unit\n")
            file.write(f"The 50th percentile of the storage is: {percentil_50} unit\n")

            
    def _calculate_power_term_grid_toll(self, df):
        if inputs.is_cost_driven == True:
            return 0
        else:
            filtered_df = df[df['energy'] > 0]
            
            self.termino_potencia_peajes = {## EUR/kW/year, P1, P2, P3, P4, P5, P6
                "2.0 TD": [22.401746, 0.776564, None, None, None, None],
                "3.0 TD": [11.997830, 7.687805, 3.307437, 2.791786, 0.934435, 0.934435],
                "6.1 TD": [20.557850, 12.762884, 9.926251, 7.848380, 0.325141, 0.325141],
                "6.2 TD": [13.138413, 8.751207, 5.615670, 4.671118, 0.238475, 0.238475],
                "6.3 TD": [10.474293, 6.510420, 5.241724, 4.138835, 0.341465, 0.341465],
                "6.4 TD": [7.310560, 4.116430, 3.161822, 2.877385, 0.194493, 0.194493],
                "Exempted": [0,0,0,0,0,0]
            }       
            self.termino_potencia_cargos = {## EUR/kW/year, P1, P2, P3, P4, P5, P6
                "2.0 TD": [2.989915, 0.192288, None, None, None, None],
                "3.0 TD": [3.715217, 1.859231, 1.350774, 1.350774, 1.350774, 0.619203],
                "6.1 TD": [3.856557, 1.930027, 1.402384, 1.402384, 1.402384, 0.642759],
                "6.2 TD": [2.264702, 1.133557, 0.823528, 0.823528, 0.823528, 0.377450],
                "6.3 TD": [1.813304, 0.907425, 0.659281, 0.659281, 0.659281, 0.302217],
                "6.4 TD": [0.887008, 0.443874, 0.322548, 0.322548, 0.322548, 0.147835],
                "Exempted": [0,0,0,0,0,0]
            }
            
            
            # Contar los valores de cada tipo en la columna 'TariffPeriod' del DataFrame filtrado
            conteo_periodos = filtered_df['TariffPeriod'].value_counts()
            periods = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
            conteo_periodos = conteo_periodos.reindex(periods, fill_value=0)
            total_power_toll = 0
            for i, period in enumerate(periods):
                if conteo_periodos[period]>0:
                    total_power_toll += self.termino_potencia_peajes[tension_level][i] + self.termino_potencia_cargos[tension_level][i]
            total_power_toll += self._margin_tradingcompany_power
            
            installed_power = self._rps_installed_power
            return total_power_toll*installed_power*1000*(1+self._electricity_tax/100)
    
    def _calculate_power_term_grid_toll_with_PPA(self, df, weather_data_df):
        weather_data_df = weather_data_df.iloc[:8760]
        filtered_df = df[(df['energy'] > 0) & (weather_data_df['GHI'] < 0)]

        self.termino_potencia_peajes = {## EUR/kW/year, P1, P2, P3, P4, P5, P6
            "2.0 TD": [22.401746, 0.776564, None, None, None, None],
            "3.0 TD": [11.997830, 7.687805, 3.307437, 2.791786, 0.934435, 0.934435],
            "6.1 TD": [20.557850, 12.762884, 9.926251, 7.848380, 0.325141, 0.325141],
            "6.2 TD": [13.138413, 8.751207, 5.615670, 4.671118, 0.238475, 0.238475],
            "6.3 TD": [10.474293, 6.510420, 5.241724, 4.138835, 0.341465, 0.341465],
            "6.4 TD": [7.310560, 4.116430, 3.161822, 2.877385, 0.194493, 0.194493]
        }       
        self.termino_potencia_cargos = {## EUR/kW/year, P1, P2, P3, P4, P5, P6
            "1": [2.989915, 0.192288, None, None, None, None],
            "2": [3.715217, 1.859231, 1.350774, 1.350774, 1.350774, 0.619203],
            "3": [3.856557, 1.930027, 1.402384, 1.402384, 1.402384, 0.642759],
            "4": [2.264702, 1.133557, 0.823528, 0.823528, 0.823528, 0.377450],
            "5": [1.813304, 0.907425, 0.659281, 0.659281, 0.659281, 0.302217],
            "6": [0.887008, 0.443874, 0.322548, 0.322548, 0.322548, 0.147835]
        }
        
        
        # Contar los valores de cada tipo en la columna 'TariffPeriod' del DataFrame filtrado
        conteo_periodos = filtered_df['TariffPeriod'].value_counts()
        periods = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
        conteo_periodos = conteo_periodos.reindex(periods, fill_value=0)
        total_power_toll = 0
        for i, period in enumerate(periods):
            if conteo_periodos[period]>0:
                total_power_toll += self.termino_potencia_peajes["6.3 TD"][i] + self.termino_potencia_cargos["5"][i]
        total_power_toll += self._margin_tradingcompany_power
        
        installed_power = self._rps_installed_power
        return total_power_toll*installed_power*1000*(1+self._electricity_tax/100)
    
# def test_extended_operations():
#     start_time = time.time()
#     path = 'test.csv'
#     operation_obj = Operations(path)
#     print(operation_obj.get_extended_operation_df())
#     end_time = time.time()
#     plt.plot(operation_obj.get_extended_operation_df())
#     plt.show()
#     print('Execution time:', end_time-start_time, 'seconds')


if __name__ == '__main__':
    pass
    # test_extended_operations()
