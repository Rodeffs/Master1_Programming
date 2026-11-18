import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import date, datetime, timedelta, time
from argparse import ArgumentParser


def generate_time_series(parameters):
    n_points = parameters["n"]
    dmins = parameters["m"]
    deviation = parameters["d"]
    trend_speed = parameters["ts"]
    trend_type = parameters["tt"]
    seasonality = parameters["s"]
    period1 = parameters["p1"]
    period2 = parameters["p2"]
    outliers = parameters["o"]
    gaps = parameters["g"]
    seed = parameters["seed"]

    if seed is not None:
        np.random.seed(seed)

    x = np.arange(n_points)
        
    # Генерируем временные метки (начиная с 00:00 сегодняшнего дня)
    
    start_date = datetime.combine(date.today(), time())
    dates = [(start_date + timedelta(minutes=dmins*i)) for i in range(n_points)]

    # Задаём шум через его стандартное отклонение
    
    deviation_types = ["const", "grow", "decay"]
    
    base_deviation = 10  # начальное отклонение
    scale_deviation = base_deviation / n_points  # скорость роста отклонения

    if deviation == "random":
        deviation = np.random.choice(deviation_types)

    noise = np.zeros(n_points, dtype=np.float64)
    
    match deviation:
        case "const":
            noise = np.random.normal(0, base_deviation, n_points)

        case "grow":
            for i in range(n_points):
                noise[i] = np.random.normal(0, base_deviation + scale_deviation*i)

        case "decay":
             for i in range(n_points):
                noise[i] = np.random.normal(0, 2*base_deviation - scale_deviation*i)           
            
    # Генерируем тренд

    trend_component = np.zeros(n_points, dtype=np.float64)

    trend_speeds = ["none", "fast_up", "slow_up", "fast_down", "slow_down"]

    if trend_speed == "random":
        trend_speed = np.random.choice(trend_speeds)

    trend_types = ["linear", "exponential", "quadratic", "logarithmic"]

    if trend_type == "random":
        trend_type = np.random.choice(trend_types)

    if trend_speed != "none":
        lin_slope, exp_scale, exp_pow, quad_a, quad_b, log_scale = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        if trend_speed == "fast_up" or trend_speed == "fast_down":
            lin_slope = np.random.uniform(0.4, 1.0)
            exp_scale = np.random.uniform(0.5, 1.0)
            exp_pow = np.random.uniform(5/n_points, 7/n_points)
            quad_a = np.random.uniform(0.0001, 0.0005)
            quad_b = np.random.uniform(0.2, 0.5)
            log_scale = np.random.uniform(50, 80)

            if trend_speed == "fast_down":
                lin_slope, exp_scale, quad_a, quad_b, log_scale = -lin_slope, -exp_scale, -quad_a, -quad_b, -log_scale

        elif trend_speed == "slow_up" or trend_speed == "slow_down":
            lin_slope = np.random.uniform(0.1, 0.2)
            exp_scale = np.random.uniform(0.5, 1.0)
            exp_pow = np.random.uniform(3/n_points, 4/n_points)
            quad_a = np.random.uniform(0.00001, 0.00005)
            quad_b = np.random.uniform(0.1, 0.2)
            log_scale = np.random.uniform(10, 20)

            if trend_speed == "slow_down":
                lin_slope, exp_scale, quad_a, quad_b, log_scale = -lin_slope, -exp_scale, -quad_a, -quad_b, -log_scale

        initial_trend = np.random.uniform(50, 100) # случайное начальное значение
        
        match trend_type:
            case "linear":  # линейный тренд: y = mx + b
                trend_component = lin_slope * x + initial_trend
    
            case "exponential":  # экспоненциальный тренд: y = a*exp(bx) + c
                trend_component = exp_scale * np.exp(exp_pow * x) + initial_trend

            case "quadratic":  # квадратичный тренд: y = ax^2 + bx + c
                trend_component = quad_a * x**2 + quad_b * x + initial_trend

            case "logarithmic":  # логарифмический тренд: y = a*log(x+1) + b
                trend_component = log_scale * np.log(x + 1) + initial_trend

    # Генерируем сезонность

    seasonal_component = np.zeros(n_points, dtype=np.float64)

    seasonality_types = ["none", "one", "two"]

    if seasonality == "random":
        seasonality = np.random.choice(seasonality_types)

    if seasonality == "one" or seasonality == "two":  # первая сезонная компонента
        amplitude = np.random.uniform(10, 30) # амплитуда
        phase = np.random.uniform(0, 2*np.pi) # фаза

        seasonal_component += amplitude * np.sin(2*np.pi*x/period1 + phase)  # синусоида

    if seasonality == "two":  # вторая сезонная компонента
        amplitude = np.random.uniform(20, 40) # амплитуда
        phase = np.random.uniform(0, 2*np.pi) # фаза

        seasonal_component += amplitude * np.sin(2*np.pi*x/period2 + phase)  # синусоида
        
    # Комбинируем все компоненты
    
    values = noise + trend_component + seasonal_component

    # Добавляем выбросы и пропуски
    
    # Делаем так, чтобы они не накладывались друг на друга
    outliers_gaps = np.random.choice(x, outliers+gaps, replace=False)  # replace=False позволяет избегать повторов

    # Выброс - это всё, что либо меньше Q25 - 1.5 * (Q75 - Q25), либо больше Q75 + 1.5 * (Q75 - Q25)
    
    Q75 = np.percentile(values, 75)
    Q25 = np.percentile(values, 25)
    IQR = Q75 - Q25

    for i in range(outliers+gaps):
        cur = outliers_gaps[i]

        if i < outliers:  # добавляем выбосы
            IQR_scale = np.random.uniform(1.6, 3.0)
            outlier_rng = np.random.uniform(0, 1)

            if outlier_rng <= 0.5:  # 50/50 положительный или отрицательный выброс
                values[cur] = Q25 - IQR_scale * IQR

            else:
                values[cur] = Q75 + IQR_scale * IQR

        else:  # добавляем пропуски
            values[cur] = np.nan
    
    return dates, values


def save_csv(dates, values, dir_path):
    timestamp = datetime.now().strftime("ts_%Y%m%d_%H%M%S")
    path = Path(f"{dir_path}/{timestamp}.csv")
    n = 1

    while True:
        try:
            with path.open("x", encoding="utf-8") as file:
                break

        except FileExistsError:
            path = Path(f"{dir_path}/{timestamp}_{n}.csv")
            n += 1

    with path.open(mode="w", encoding="utf-8") as file:
        file.write("timestamp,value\n")

        for date, value in zip(dates, values):
            file.write(f"{date},{value}\n")


def save_meta(parameters, filename):
    with open(filename, mode="w", encoding="utf-8") as file:
        json.dump(parameters, file)


def read_meta(filename):
    with open(filename, mode="r", encoding="utf-8") as file:
        return json.load(file)


def plot_time_series(dates, values, figsize=(14, 6), filename=None):        
    plt.figure(figsize=figsize)
    
    plt.plot(dates, values, label='Временной ряд', color='blue', linewidth=1.5)
    plt.title('Сгенерированный временной ряд', fontsize=16, fontweight='bold')
    plt.xlabel('Дата и время', fontsize=12)
    plt.ylabel('Значение', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Автоматически форматируем ось X для дат
    plt.gcf().autofmt_xdate()

    if filename is not None:
        plt.savefig(filename)


def print_series(dates, values):
    for date, value in zip(dates, values):
        print(f"{date}\t{value}")


def main():
    parser = ArgumentParser()

    parser.add_argument("-n", action="store", type=int, default=1000, help="the number of points in series, default is 1000")
    parser.add_argument("-m", action="store", type=int, default=5, help="the timedelta in minutes, default is 5")
    parser.add_argument("-d", choices=["const", "grow", "decay", "random"], default="random", help="the deviation type, default is random")
    parser.add_argument("-ts", choices=["none", "fast_up", "slow_up", "fast_down", "slow_down", "random"], default="random", help="the trend speed, default is random")
    parser.add_argument("-tt", choices=["linear", "exponential", "quadratic", "logarithmic", "random"], default="random", help="the trend type, default is random")
    parser.add_argument("-s", choices=["none", "one", "two", "random"], default="random", help="the amount of seasonalities, default is random")
    parser.add_argument("-p1", action="store", type=int, default=12, help="the period (amount of points) of the first seasonality, default is 12")
    parser.add_argument("-p2", action="store", type=int, default=72, help="the period (amount of points) of the second seasonality, default is 72")
    parser.add_argument("-o", action="store", type=int, default=0, help="the number of outliers in series, default is 0")
    parser.add_argument("-g", action="store", type=int, default=0, help="the number of gaps in series, default is 0")
    parser.add_argument("--seed", action="store", type=int, default=None, help="the rng seed, default is none")
    parser.add_argument("--read_meta", action="store", type=str, default=None, help="read json metadata from filepath")
    parser.add_argument("--save_meta", action="store", type=str, default=None, help="save json metadata to filepath")
    parser.add_argument("--png", action="store", type=str, default=None, help="save png to filepath")
    parser.add_argument("--nosave", action="store_true", help="do not save time series to csv")
    parser.add_argument("--print", action="store_true", help="print time series")
    parser.add_argument("--output_dir", action="store", type=str, default=".", help="the directory to save time series to, default is cwd")
    
    args = vars(parser.parse_args())  # сразу в словарь
    
    json_read = args.pop("read_meta")
    json_save = args.pop("save_meta")
    png = args.pop("png")
    output_dir = args.pop("output_dir")
    nosave = args.pop("nosave")
    printout = args.pop("print")

    if json_read != None:
        args = read_meta(json_read)

    if json_save != None:
        save_meta(args, json_save)

    dates, values = generate_time_series(args)

    if png != None:
        plot_time_series(dates, values, filename=png)

    if not nosave:
        save_csv(dates, values, output_dir)

    if printout:
        print_series(dates, values)


if __name__ == "__main__":
    main()
