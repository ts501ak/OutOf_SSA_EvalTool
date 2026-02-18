import matplotlib.pyplot as plt
import numpy as np
import argparse
import pathlib
import json

def main():
    parsi = argparse.ArgumentParser(description="Collect and visualize the stats in the JSON files")
    parsi.add_argument("--path","-p",type=str,help="Path to the results folder",default="./res/")
    args = parsi.parse_args()

    totalGED = 0
    avgSourceZHK = []
    avgDecompZHK = []
    matchedZHK = 0
    notMatchedZHK = 0
    avgSavePoints = []
    avgZHKSize = []
    GEDTimeout = 0
    GEDNoTimeout = 0
    avgGEDTime = []
    gedTimes = []

    for stat in iterJSONFiles(args.path):
        totalGED += stat["total_ged"]
        avgSourceZHK.append(stat["avg_source_zhk"])
        avgDecompZHK.append(stat["avg_decomp_zhk"])
        matchedZHK += stat["matched_zhk"]
        notMatchedZHK += stat["not_matched_zhk"]
        avgSavePoints.append(stat["avg_save_points"])
        avgZHKSize.append(stat["avg_zhk_size"])
        GEDTimeout += stat["ged_timeouts"]
        GEDNoTimeout += stat["ged_no_timeout"]
        avgGEDTime.append(stat["avg_ged_time"])
        gedTimes.extend(stat["ged_times"])

    plot_histogram(gedTimes)
    plot_bar_chart([GEDTimeout,GEDNoTimeout],["Timeout","no Timeout"],"Timeouts during GED calculation")
    plot_bar_chart([np.mean(avgSourceZHK),np.mean(avgDecompZHK),np.mean(matchedZHK),np.mean(notMatchedZHK),np.mean(avgZHKSize)],["avg #ZHK Source-Code","avg #ZHK Decompilat","avg matched ZHK","avg non-matched ZHK","avg Größe ZHK"],"Zusammenhangskomponenten")
    print("TOTAL GED:",totalGED)


def getTotalGED(path : str):
    totalGED = 0
    for stat in iterJSONFiles(path):
        totalGED += stat[totalGED]
    return totalGED


def plot_bar_chart(values, labels=None, title="Balkendiagramm", colors=None):
    """
    Plottet ein Säulendiagramm mit beliebig vielen Balken.
    
    Parameters
    ----------
    values : list of float
        Werte der Balken.
    labels : list of str, optional
        Beschriftungen für die Balken. Wenn None, werden 1,2,3,... verwendet.
    title : str
        Titel des Diagramms.
    colors : list of str, optional
        Farben der Balken. Wenn None, werden Standardfarben verwendet.
    """
    num_bars = len(values)
    
    if labels is None:
        labels = [str(i+1) for i in range(num_bars)]
    
    if colors is None:
        colors = plt.cm.tab20.colors  # eine Palette für bis zu 20 Balken
        if num_bars > len(colors):
            colors = ['skyblue'] * num_bars  # fallback
    
    x_pos = range(num_bars)
    
    plt.figure(figsize=(max(6, num_bars), 5))  # breite passt sich der Anzahl an
    plt.bar(x_pos, values, color=colors[:num_bars], edgecolor='black')
    
    # Werte über die Balken schreiben
    for i, v in enumerate(values):
        plt.text(i, v + 0.01 * max(values), f"{v:.2f}", ha='center', va='bottom')
    
    plt.xticks(x_pos, labels)
    plt.ylabel("Wert")
    plt.title(title)
    plt.grid(axis='y', alpha=0.5)
    plt.show()


def plot_histogram(data):
    """
    Plottet ein Histogramm der Floats in 5er-Bins.
    
    Parameters
    ----------
    data : list of float
        Die zu analysierenden Werte.
    """
    if not data:
        print("Keine Daten zum Plotten!")
        return

    mean_value = np.mean(data)
    max_val = max(data)
    
    # Bin-Grenzen: 0, 5, 10, ..., bis zum nächsten Vielfachen von 5 über max_val
    bins = np.arange(0, max_val + 5, 5)

    plt.figure(figsize=(8,5))
    plt.hist(data, bins=bins, edgecolor='black')
    plt.axvline(mean_value, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {mean_value:.2f}')
    plt.legend()
    plt.title("Histogramm der GED-Zeiten")
    plt.xlabel("benötigte GED-Zeit")
    plt.ylabel("Häufigkeit")
    plt.grid(axis='y', alpha=0.75)
    plt.show()


def iterJSONFiles(path : str):
    folder = pathlib.Path(path)
    for fp in sorted(folder.glob("*.json")):
        with fp.open("r") as f:
            data = json.load(f)
            if not isinstance(data,dict):
                pass
            else:
                yield data