import datetime
import holidays
from inputs import tension_level

class TariffPeriod:
    def __init__(self, current_year=2023):
        self.current_year = current_year
        
        if self.is_leap_year(self.current_year) is True:
            self.dias_por_mes = {
                "Enero": 31,
                "Febrero": 29,
                "Marzo": 31,
                "Abril": 30,
                "Mayo": 31,
                "Junio": 30,
                "Julio": 31,
                "Agosto": 31,
                "Septiembre": 30,
                "Octubre": 31,
                "Noviembre": 30,
                "Diciembre": 31
            }
        else:
            self.dias_por_mes = {
                "Enero": 31,
                "Febrero": 28,
                "Marzo": 31,
                "Abril": 30,
                "Mayo": 31,
                "Junio": 30,
                "Julio": 31,
                "Agosto": 31,
                "Septiembre": 30,
                "Octubre": 31,
                "Noviembre": 30,
                "Diciembre": 31
            }
        self.horarios_facturacion = {
            "Enero":    ["P6", "P2", "P1", "P2", "P1", "P2", "P6"],
            "Febrero":  ["P6", "P2", "P1", "P2", "P1", "P2", "P6"],
            "Marzo":    ["P6", "P3", "P2", "P3", "P2", "P3", "P6"],
            "Abril":    ["P6", "P5", "P4", "P5", "P4", "P5", "P6"],
            "Mayo":     ["P6", "P5", "P4", "P5", "P4", "P5", "P6"],
            "Junio":    ["P6", "P4", "P3", "P4", "P3", "P4", "P6"],
            "Julio":    ["P6", "P2", "P1", "P2", "P1", "P2", "P6"],
            "Agosto":   ["P6", "P4", "P3", "P4", "P3", "P4", "P6"],
            "Septiembre": ["P6", "P4", "P3", "P4", "P3", "P4", "P6"],
            "Octubre":  ["P6", "P5", "P4", "P5", "P4", "P5", "P6"],
            "Noviembre": ["P6", "P3", "P2", "P3", "P2", "P3", "P6"],
            "Diciembre": ["P6", "P2", "P1", "P2", "P1", "P2", "P6"]
        }
        self.festivos_es = holidays.Spain(years=self.current_year)
        
        self.termino_potencia_peajes = {## EUR/kW/year, P1, P2, P3, P4, P5, P6
            "2.0 TD": [22.401746, 0.776564, None, None, None, None],
            "3.0 TD": [11.997830, 7.687805, 3.307437, 2.791786, 0.934435, 0.934435],
            "6.1 TD": [20.557850, 12.762884, 9.926251, 7.848380, 0.325141, 0.325141],
            "6.2 TD": [13.138413, 8.751207, 5.615670, 4.671118, 0.238475, 0.238475],
            "6.3 TD": [10.474293, 6.510420, 5.241724, 4.138835, 0.341465, 0.341465],
            "6.4 TD": [7.310560, 4.116430, 3.161822, 2.877385, 0.194493, 0.194493],
            "Exempted": [0,0,0,0,0,0]
        }
        
        self.termino_energia_peajes = {##EUR/kWh, P1, P2, P3, P4, P5, P6
            "2.0 TD": [0.033081, 0.019184, 0.000557, None, None, None],
            "3.0 TD": [0.023974, 0.012820, 0.007573, 0.005495, 0.000424, 0.000234],
            "6.1 TD": [0.021899, 0.011675, 0.007394, 0.005376, 0.000406, 0.000212],
            "6.2 TD": [0.011872, 0.006530, 0.003686, 0.002774, 0.000249, 0.000090],
            "6.3 TD": [0.010399, 0.005651, 0.003603, 0.002659, 0.000238, 0.000140],
            "6.4 TD": [0.008757, 0.004806, 0.003067, 0.002206, 0.000139, 0.000089],
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
        self.termino_energia_cargos = {##EUR/kWh, P1, P2, P3, P4, P5, P6
            "2.0 TD": [0.043893, 0.008779, 0.002195, None, None, None],
            "3.0 TD": [0.024469, 0.018118, 0.009788, 0.004894, 0.003137, 0.001958],
            "6.1 TD": [0.013305, 0.009856, 0.005322, 0.002661, 0.001706, 0.001064],
            "6.2 TD": [0.006243, 0.004624, 0.002497, 0.001249, 0.000800, 0.000499],
            "6.3 TD": [0.005117, 0.003791, 0.002047, 0.001023, 0.000656, 0.000409],
            "6.4 TD": [0.001944, 0.001440, 0.000778, 0.000389, 0.000249, 0.000156],
            "Exempted": [0,0,0,0,0,0]
        }
        
    def is_leap_year(self,year):
        try:
            # Try to create a date for February 29th of the given year
            datetime.date(year, 2, 29)
            # If no exception is raised, the year is a leap year
            return True
        except ValueError:
            # If an exception is raised, the year is not a leap year
            return False
        
    def obtener_mes(self, dia_del_ano):
        acumulado = 0
        for mes, dias in self.dias_por_mes.items():
            acumulado += dias
            if dia_del_ano <= acumulado:
                return mes
        return None

    def es_fin_de_semana_o_festivo(self, dia_del_ano):
        fecha = datetime.datetime(self.current_year, 1, 1) + datetime.timedelta(dia_del_ano - 1)
        es_fin_de_semana = fecha.weekday() >= 5  # 5 para sábado, 6 para domingo
        es_festivo = fecha in self.festivos_es
        return es_fin_de_semana or es_festivo

    def obtener_periodo_facturacion(self, dia_del_ano, hora):
        if self.es_fin_de_semana_o_festivo(dia_del_ano):
            return "P6"  # Período para fines de semana y festivos
        
        mes = self.obtener_mes(dia_del_ano)
        if not mes:
            return None
        
        if 0 <= hora < 8:
            franja = 0
        elif 8 <= hora < 9:
            franja = 1
        elif 9 <= hora < 14:
            franja = 2
        elif 14 <= hora < 18:
            franja = 3
        elif 18 <= hora < 22:
            franja = 4
        elif 22 <= hora < 24:
            franja = 5
        else:
            return None
        
        return self.horarios_facturacion[mes][franja]

    def obtener_dia_semana_y_fecha(self, dia_del_ano):
        fecha = datetime.datetime(self.current_year, 1, 1) + datetime.timedelta(dia_del_ano - 1)
        dia_semana = fecha.strftime('%A')  # Nombre del día de la semana
        mes = fecha.strftime('%B')  # Nombre del mes
        dia_mes = fecha.day  # Día del mes
        return dia_semana, mes, dia_mes

    def agregar_periodo_facturacion_a_dataframe(self, df, fecha_col, hora_col):
        def determinar_periodo(row):
            fecha = row[fecha_col]
            hora = row[hora_col]
            dia_del_ano = fecha.timetuple().tm_yday
            return self.obtener_periodo_facturacion(dia_del_ano, hora)
        
        df['TariffPeriod'] = df.apply(determinar_periodo, axis=1)
        
        def determinar_potencia_peaje(row):
            periodo = row['TariffPeriod']
            indice_periodo = int(periodo[1]) - 1  # Convertir P1, P2, etc. a índices 0, 1, etc.
            return self.termino_potencia_peajes[tension_level][indice_periodo]
        
        def determinar_energia_peaje(row):
            periodo = row['TariffPeriod']
            indice_periodo = int(periodo[1]) - 1
            return self.termino_energia_peajes[tension_level][indice_periodo]
        
        def determinar_energia_cargos(row):
            periodo = row['TariffPeriod']
            indice_periodo = int(periodo[1]) - 1
            return self.termino_energia_cargos[tension_level][indice_periodo]
        #df['TerminoPotenciaPeaje'] = df.apply(determinar_potencia_peaje, axis=1)
        df['EnergyTermTolls'] = df.apply(determinar_energia_peaje, axis=1)
        df['EnergyTermOtherCharges'] = df.apply(determinar_energia_cargos, axis=1)
        return df
