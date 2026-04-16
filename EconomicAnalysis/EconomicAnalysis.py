from inputs import YEAR_START, PROJECT_LIFETIME, DEBT_LIFETIME
import numpy_financial as npf
import numpy as np
import inputs

class EconomicAnalysis(object):

    def __init__(self, project_yearly_stats_df, total_capex):
        self._project_yearly_stats_df = project_yearly_stats_df
        

        # Retrieve Data Object and its data
        self._salvage_value= inputs.salvage_value
        self._RROE = inputs.RROE
        self._interest_rate = inputs.interest_rate
        self._equity_debt_ratio = inputs.equity_debt_ratio
        self._amortization_method = inputs.amortization_method
        self._tax_rate = inputs.tax_rate
        self._inflation_rate = inputs.inflation_rate
        self._capex = total_capex-total_capex/(1+self._equity_debt_ratio)
        #self._discount_rate = self._calculate_WACC(self._equity_debt_ratio, self._RROE, self._interest_rate, self._tax_rate)
        self._discount_rate = self._RROE
        
        self._rcs_maintenance_costs = inputs.rcs_maintenance_costs
        self._rcs_maintenance_cost_annual_reduction = inputs.rcs_maintenance_cost_annual_reduction
        
        self._cashflow_df = self._calculate_cashflows_after_taxes(project_yearly_stats_df.copy(), total_capex, self._interest_rate, self._equity_debt_ratio, self._amortization_method, self._tax_rate, self._inflation_rate, self._salvage_value, write_to_csv = True)
        self._discounted_cashflow_df = self._calculate_discounted_cashflow_df(self._cashflow_df.copy(), self._discount_rate)
        self._spbp = self._calculate_spbp()
        self._dpbp = self._calculate_dpbp()
        self._npv = self._calculate_npv(self._discounted_cashflow_df)
        self._irr = self._calculate_irr()
        self._mirr = self._calculate_mirr()
        self._LCOE = self._calculate_LCOE(project_yearly_stats_df.copy(), total_capex, self._interest_rate, self._equity_debt_ratio, self._amortization_method, self._tax_rate, self._inflation_rate, self._salvage_value)
        self._subsidy_MWh, self._subsidy_MEuro_year = self._calculate_subsidy(self._LCOE, self._cashflow_df['avr_elec_price_sell'].mean(), -self._cashflow_df['Energy_Out'].mean())
        
    def _calculate_WACC(self, equity_debt_ratio, RROE, interest_rate, tax_rate):
        debt_fraction = 1/(1+equity_debt_ratio)
        WACC = (1-debt_fraction)*RROE/100+debt_fraction*interest_rate/100*(1-tax_rate/100)
        return WACC*100 #%
    
    def _calculate_discounted_cashflow_df(self, df, discount_rate):
        #df = self._cashflow_df.copy()
        discount = df.index.map(lambda x: (1 + discount_rate/100)**(x-YEAR_START+1))
        #df['Discounted_cashflow'] = (df['Trading_Cashflow'] + df['GT_OpEx_Cashflow'] + df['Ely_OpEx_Cashflow'])/discount
        df['Discounted_cashflow'] = df['Cashflow']/discount
        return df

    def _calculate_spbp(self):
        df = self._cashflow_df
        #average_cashflow = (df['Trading_Cashflow'] + df['GT_OpEx_Cashflow'] + df['Ely_OpEx_Cashflow'])/PROJECT_LIFETIME
        average_cashflow = df['Cashflow'].sum()/PROJECT_LIFETIME
        return self._capex/average_cashflow
        # if average_cashflow.sum() > 0:
        #     return self._capex/average_cashflow.sum()
        # else:
        #     return -1

    def _calculate_dpbp(self):
        cashflow = -self._capex
        dpbp = -1
        for index, value in self._discounted_cashflow_df.iterrows():
            cashflow += value['Discounted_cashflow']
            if cashflow > 0:
                dpbp = index
                break
        return dpbp-YEAR_START

    def _calculate_irr(self):
        ### Compute IRR using bisection numerical method

        ## Initialize parameters
        irr_a = -90
        irr_b = 90
        irr_c = 0
        npv = 10
        toll = 10 ** (-5)
        k = 0
        k_max = 100

        if self._dpbp >= PROJECT_LIFETIME:
            ## if the discounted PBP is greater than the project time it makes no sense to compute the IRR
            return - 1
        else:
            ## Bisection Method
            while abs(npv) > toll and k < k_max:
                ## initialise IRR guess
                irr_c = irr_a / 2.0 + irr_b / 2.0

                ## calculate the NPV
                discounted_cashflow_df = self._calculate_discounted_cashflow_df(self._cashflow_df.copy(), irr_c)
                npv = self._calculate_npv(discounted_cashflow_df)

                ## Update IRR Guesses
                if npv < 0:
                    irr_b = irr_c
                else:
                    irr_a = irr_c
                k += 1
        cashflows = [-self._capex] + self._cashflow_df["Cashflow"].tolist()
        irr_d = npf.irr(cashflows)
        return irr_d

    def _calculate_LCOE(self, cashflow_df, total_capex, interest_rate, equity_debt_ratio, amortization_method, tax_rate, inflation_rate, salvage_value_percent):
        LCOE_min = 0
        LCOE_max = 100000
        tolerance = 1  # Define un umbral de tolerancia para la búsqueda, puede ajustarse a un valor más pequeño si se necesita más precisión
    
        def update_EBITDA(LCOE, cashflow_df):
            # Corregí la referencia a self.update_EBITDA a update_EBITDA ya que es una función interna
            cashflow_df['EBITDA'] = cashflow_df['EBITDA'] - cashflow_df['Energy_Out'] * LCOE - cashflow_df['Electricity_sold_earnings']
            return cashflow_df
    
        def calculate_npv(LCOE, cashflow_df, total_capex, interest_rate, equity_debt_ratio, amortization_method, tax_rate, inflation_rate, salvage_value_percent):
            cashflow_df_updated = update_EBITDA(LCOE, cashflow_df.copy())
            cashflow_df_updated = self._calculate_cashflows_after_taxes(cashflow_df_updated.copy(), total_capex, interest_rate, equity_debt_ratio, amortization_method, tax_rate, inflation_rate, salvage_value_percent)
            discounted_cashflow_df = self._calculate_discounted_cashflow_df(cashflow_df_updated, self._discount_rate)
            return self._calculate_npv(discounted_cashflow_df)
    
        # Bucle de bisección para encontrar el LCOE que hace que el NPV sea cero
        while LCOE_max - LCOE_min > tolerance:
            LCOE_mid = (LCOE_max + LCOE_min) / 2
            npv = calculate_npv(LCOE_mid, cashflow_df, total_capex, interest_rate, equity_debt_ratio, amortization_method, tax_rate, inflation_rate, salvage_value_percent)
            if npv > 0:
                LCOE_max = LCOE_mid
            else:
                LCOE_min = LCOE_mid
    
        return (LCOE_max + LCOE_min) / 2

    def _calculate_subsidy(self, LCOE, avr_elec_price_sell, total_energy_sold):
        
        subsidy_MWH = LCOE - avr_elec_price_sell
        subsidy_MEuro_year = subsidy_MWH * total_energy_sold/10**6
        
        return subsidy_MWH, subsidy_MEuro_year


    def _calculate_mirr(self):
        cash_flows = [-self._capex] + self._cashflow_df["Cashflow"].tolist()
        finance_rate = self._discount_rate #WACC
        reinvestment_rate = self._RROE 
        mirr_value = npf.mirr(cash_flows, finance_rate/100, reinvestment_rate/100)
        return mirr_value*100
        
    def _calculate_npv(self, discounted_cashflow_df):
        #npv = npf.npv(0, [-self._capex]+ discounted_cashflow_df['Discounted_cashflow'].tolist())
        return -self._capex + discounted_cashflow_df['Discounted_cashflow'].sum()

    def _update_EBITDA_inflation(self, cashflow_df, inflation_rate):
        df = cashflow_df.copy()
        inflation = df.index.map(lambda x: (1 + inflation_rate/100)**(x-YEAR_START+1))
        cashflow_df['EBITDA_nominal'] = cashflow_df['EBITDA']*inflation
        return cashflow_df
        
    def _add_salvage_value(self,cashflow_df, salvage_value):
        cashflow_df.loc[YEAR_START+PROJECT_LIFETIME-1,'EBITDA_nominal'] += salvage_value
        return cashflow_df
    
    def _calculate_bank_loan(self, cashflow_df, total_capex, interest_rate, equity_debt_ratio):
        debt_principal = total_capex/(1+equity_debt_ratio)
        IR = interest_rate/100
        levelised_debt_payment = debt_principal*(IR*(1+IR)**DEBT_LIFETIME)/((1+IR)**DEBT_LIFETIME-1)
        cashflow_df['Debt_payment'] = 0.0
        cashflow_df['Interest_payment'] = 0.0
        cashflow_df['Debt_remaining'] = 0.0
        for i in range(YEAR_START,YEAR_START+DEBT_LIFETIME):
            interest_payment = debt_principal * interest_rate / 100
            cashflow_df.loc[i, 'Interest_payment'] = interest_payment
            cashflow_df.loc[i, 'Debt_payment'] = levelised_debt_payment
            debt_principal = debt_principal -(levelised_debt_payment - interest_payment)
            cashflow_df.loc[i,'Debt_remaining'] = debt_principal
        return cashflow_df

    def _calculate_capex_amortization(self, cashflow_df, total_capex, salvage_value_percent, amortization_method):
        ## Depreciation factors
        if amortization_method == 'MACRS-10':
            DF = [10,18,14.4,11.52,9.22,7.37,6.55,6.55,6.55,6.55,3.29]
            DF.extend([0] * (PROJECT_LIFETIME-len(DF)))
        elif amortization_method == 'MACRS-15':
            DF = [5, 9.5, 8.55, 7.7, 6.93, 6.23, 5.9, 5.9, 5.91, 5.9, 5.91,5.9, 5.91,5.9,5.91, 2.95]
            DF.extend([0] * (PROJECT_LIFETIME-len(DF)))
        elif amortization_method == 'Straight_Line':
            DF = [100/PROJECT_LIFETIME]*PROJECT_LIFETIME
        elif amortization_method == 'Without_Amortization':
            DF = [0] * PROJECT_LIFETIME
        cashflow_df['Amortization'] = 0.0
        for index, year in enumerate(range(YEAR_START,YEAR_START+PROJECT_LIFETIME)):
            cashflow_df.loc[year,'Amortization'] = (1-salvage_value_percent/100)*total_capex*DF[index]/100
            
        return cashflow_df
    
    def _calculate_BAI(self, cashflow_df, tax_rate):
        cashflow_df['EBT'] = cashflow_df['EBITDA_nominal'] - cashflow_df['Amortization'] - cashflow_df['Interest_payment']
        
        # Inicializar columnas para cálculos
        cashflow_df['Taxes'] = 0.0
        cashflow_df['Cumulative_Loss'] = 0.0
        #cashflow_df['Loss_Carried_Forward'] = 0.0
        
        # Inicializar el carry forward de pérdidas
        carry_forward = 0.0
    
        # Iterar a través del DataFrame para ajustar el carry forward correctamente
        for year in cashflow_df.index:
            current_ebt = cashflow_df.loc[year, 'EBT']
            if current_ebt < 0:
                carry_forward += -current_ebt  # Acumula la pérdida
            else:
                taxable_income = max(0, current_ebt - carry_forward)
                cashflow_df.loc[year, 'Taxes'] = taxable_income * tax_rate / 100
                carry_forward = max(0, carry_forward - current_ebt)  # Reduce el carry forward por la cantidad de EBT positivo
            
            cashflow_df.loc[year, 'Cumulative_Loss'] = carry_forward
            cashflow_df.loc[year, 'BAI'] = current_ebt - cashflow_df.loc[year, 'Taxes']
        return cashflow_df

    
    def _add_rcs_maintenance_plan(self, cashflow_df, startups, maintenance_costs, maintenance_cost_annual_reduction):
        def _calculate_maintenance_costs(startups_array):
            maintenance_types = sorted(maintenance_costs.keys())
            maintenance_plan = np.zeros_like(startups_array)
            accumulated_startups = 0
            
            for year in range(len(startups_array)):
                accumulated_startups += startups_array[year]
                for maintenance in maintenance_types:
                    if accumulated_startups >= maintenance and (accumulated_startups - startups_array[year]) < maintenance:
                        maintenance_plan[year] += maintenance_costs[maintenance] * (1 - maintenance_cost_annual_reduction / 100) ** (year + 1)
                # Reset accumulated count after reaching max maintenance
                accumulated_startups %= maintenance_types[-1]
            return maintenance_plan
    
        rcs_maintenance_plan = _calculate_maintenance_costs(startups)
        cashflow_df['rcs_maintenance'] = -rcs_maintenance_plan
        cashflow_df['EBITDA_nominal'] -= rcs_maintenance_plan
        return cashflow_df


    
    def _calculate_cashflows_after_taxes(self, cashflow_df, total_capex, interest_rate, equity_debt_ratio, amortization_method, tax_rate, inflation_rate, salvage_value_percent, write_to_csv = False):
        cashflow_df = self._update_EBITDA_inflation(cashflow_df.copy(), inflation_rate)
        cashflow_df = self. _add_rcs_maintenance_plan(cashflow_df.copy(), cashflow_df['rcs_startups'].values, self._rcs_maintenance_costs, self._rcs_maintenance_cost_annual_reduction)
        cashflow_df = self._add_salvage_value(cashflow_df.copy(), salvage_value_percent/100*total_capex)
        cashflow_df = self._calculate_bank_loan(cashflow_df.copy(), total_capex, interest_rate, equity_debt_ratio)
        cashflow_df = self._calculate_capex_amortization(cashflow_df.copy(), total_capex, salvage_value_percent, amortization_method)
        cashflow_df = self._calculate_BAI(cashflow_df.copy(), tax_rate)
        cashflow_df['Cashflow'] = cashflow_df['EBITDA_nominal'] - cashflow_df['Debt_payment'] - cashflow_df['Taxes']
        if write_to_csv:
            cashflow_df.to_csv('Results//yearly_cashflow_df.csv') 
        return cashflow_df

    
    def print_report(self):
        print('EconomicAnalysis Report:')
        print('Investment year 0 (Equity):\t{} Eur'.format(self._capex))
        print('Simple Payback Period:\t{}'.format(self._spbp))
        print('Discounted Payback Period:\t{}'.format(self._dpbp))
        print('Net Present Value (Year {}):\t{}'.format(PROJECT_LIFETIME, self._npv))
        print('Internal Rate of Return:\t{}'.format(self._irr))
        print('Modified Internal Rate of Return:\t{}'.format(self._mirr))
        print('LCOE:\t{} Eur'.format(self._LCOE))
        print('Subsidy per MWh:\t{} Eur/MWh'.format(self._subsidy_MWh))
        print('Annual Subsidy:\t{} MEuro/year'.format(self._subsidy_MEuro_year))
    
        file_path = 'Results//economic_report.txt'
        with open(file_path, 'w') as file:
            file.write('EconomicAnalysis Report:\n')
            file.write('Investment year 0 (Equity):\t{} Eur\n'.format(self._capex))
            file.write('Simple Payback Period:\t{}\n'.format(self._spbp))
            file.write('Discounted Payback Period:\t{}\n'.format(self._dpbp))
            file.write('Net Present Value (Year {}):\t{}\n'.format(PROJECT_LIFETIME, self._npv))
            file.write('Internal Rate of Return:\t{}\n'.format(self._irr))
            file.write('Modified Internal Rate of Return:\t{}\n'.format(self._mirr))
            file.write('LCOE:\t{} Eur\n'.format(self._LCOE))
            file.write('Subsidy per MWh:\t{} Eur/MWh\n'.format(self._subsidy_MWh))
            file.write('Annual Subsidy:\t{} M Eur/year\n'.format(self._subsidy_MEuro_year))

    def get_cashflow(self):
        return self._discounted_cashflow_df