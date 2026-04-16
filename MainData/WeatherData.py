import pandas as pd
import os 
from inputs import location
import matplotlib.pyplot as plt

class WeatherData:
    def __init__(self, project_year_start, project_life):
        
        input_filepath = os.path.join("MainData", f"{location}WeatherData.csv")
        weather_data_df = pd.read_csv(input_filepath)
        
        # Convertir a DateTime y establecer como índice
        weather_data_df['DateTime'] = pd.to_datetime(weather_data_df[['Year', 'Month', 'Day', 'Hour', 'Minute']])
        weather_data_df.set_index('DateTime', inplace=True)
        
        # Agrupar por hora y calcular el promedio
        weather_data_df = weather_data_df.resample('h').mean()
        
        # Asegúrate de restablecer el índice aquí, manteniendo DateTime como una columna
        weather_data_df.reset_index(inplace=True)
        
        # Extraer la hora y el día del año
        weather_data_df['day_of_year'] = weather_data_df['DateTime'].dt.dayofyear
        weather_data_df['Hour'] = weather_data_df['DateTime'].dt.hour
        
        # Agrupar por 'day_of_year' y 'Hour' y calcular la media
        weather_data_df = weather_data_df.groupby(['day_of_year', 'Hour'], as_index=False).mean()
                
        # Preparar DataFrame extendido
        self._project_life = project_life
        self._project_year_start = project_year_start
        weather_data_df_extended = self._extend_weather_data_df(weather_data_df, project_year_start, project_life)
        
        # Eliminar columnas que ya no son necesarias
        if 'Minute' in weather_data_df.columns:
            weather_data_df.drop('Minute', axis=1, inplace=True)
        if 'day_of_year' in weather_data_df.columns:
            weather_data_df.drop('Year', axis=1, inplace=True)
        
        
        self.weather_data_df = weather_data_df_extended
        
    def _extend_weather_data_df(self, df, start_year, project_life):
        extended_df = pd.DataFrame()
        for year in range(start_year, start_year + project_life):
            temp_df = df.copy()
            temp_df['Year'] = year
            extended_df = pd.concat([extended_df, temp_df])
        return extended_df
    
    def get_weather_data_df(self):
        return self.weather_data_df
    
    def plot_temperature_and_humidity(self):
        plt.figure(figsize=(12, 8))
        font_size = 20
        # Asegurar que los datos están ordenados por índice
        weather_data_df_sorted = self.weather_data_df.sort_index()
        
        # Graficar la temperatura, excluyendo el último punto
        ax1 = plt.subplot(2, 1, 1)  # Dos filas, una columna, primer gráfico
        ax1.plot(weather_data_df_sorted.index[:-1], weather_data_df_sorted['Temperature'][:-1], label='Temperature', color='red')
        ax1.set_xlabel('Time [h]', fontsize=font_size)
        ax1.set_ylabel('Temperature (°C)', fontsize=font_size)
        ax1.tick_params(axis='both', which='major', labelsize=font_size)
        ax1.set_xlim(0, weather_data_df_sorted.index.max())  # Utilizar el máximo índice como límite superior
        
        # Configuración similar para el segundo gráfico si es necesario
        ax2 = plt.subplot(2, 1, 2)
        ax2.plot(weather_data_df_sorted.index[:-1], weather_data_df_sorted['Relative Humidity'][:-1], label='Relative Humidity', color='blue')
        ax2.set_xlabel('Time [h]', fontsize=font_size)
        ax2.set_ylabel('Relative Humidity (%)', fontsize=font_size)
        ax2.tick_params(axis='both', which='major', labelsize=font_size)
        ax2.set_xlim(0, weather_data_df_sorted.index.max())
        
        plt.tight_layout()
        plt.show()

        
# Uso de la clase
# project_start_year = 2022
# project_life = 1
# weather_data = WeatherData(project_start_year, project_life)
# extended_weather_data_df = weather_data.get_weather_data_df()
# print(extended_weather_data_df.head())
# weather_data.plot_temperature_and_humidity()
