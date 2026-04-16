import pandas as pd
import matplotlib.pyplot as plt
import time
from Operations.Operations import Operations
from EconomicAnalysis.EconomicAnalysis import EconomicAnalysis
from inputs import unit, resource_consumption_power, charge_to_discharge_ratio, storage_capacity, resource_rate_rcs, resource_rate_rps
from Mish.utils import get_rate

class RunMain():

    def run(self):
        ## Operations
        start_time = time.time()

        operations_data_obj = Operations()
        #operations_data_obj.write_results_data()
        self._operation_yearly_df = operations_data_obj.get_project_yearly_stats_df()
        tank_level_max = operations_data_obj.calculate_maximum_storage_capacity()
        self._capex = operations_data_obj.get_total_capex(tank_level_max)

        end_time = time.time()
        print('Execution time:', end_time-start_time, 'seconds')

        ## Economics
        print('Starting economic analysis...')
        economics_analysis_obj = EconomicAnalysis(self._operation_yearly_df, self._capex)
        economics_analysis_obj.print_report()


if __name__ == '__main__':
    print("\n================= START OF ANALYSIS =================\n")

    # Define the case study message
    message = "Case study:\n"
    message += f"- The RCS (Resource Consumption Subsystem) has a power of {resource_consumption_power} MW.\n"
     
    # Calculate the power of the RPS
    rps_power = resource_consumption_power * charge_to_discharge_ratio / (get_rate(resource_rate_rcs, load_frac = 1, T = 15, RH = 0) * resource_rate_rps)
    message += f"- The RPS (Resource Production Subsystem) has a power of {rps_power:.2f} MW.\n"

    # Define the storage capacity
    if storage_capacity == -1:
        message += "- Storage capacity: unlimited, it will be calculated during the simulation.\n"
    else:
        message += f"- Storage capacity: {storage_capacity} {unit}.\n"

    print(message)
    
    # Run the simulation
    simulator = RunMain()
    simulator.run()

    # Final message
    #input("\nSimulation completed. Press Enter to close.")




