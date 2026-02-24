import matplotlib.pyplot as plt
import numpy as np
import argparse
import pathlib
import json
import os

def makePlots():
    parsi = argparse.ArgumentParser(description="Collect and visualize the stats in the JSON files")
    parsi.add_argument("--path","-p",type=str,help="Path to the results folder",default="./res/")
    parsi.add_argument("--reconstructTiemoutsFromGEDTimes",type=int,help="The number of Timeouts is reconstructed using the given Timeout")
    args = parsi.parse_args()

    total = 0
    totalGED = 0
    SourceZHK = []
    DecompZHK = []
    matchedZHK = 0
    notMatchedZHK = 0
    SavePoints = []
    avgZHKSize = []
    GEDTimeout = 0
    GEDNoTimeout = 0
    avgGEDTime = []
    gedTimes = []
    singleGEDs = []
    funcNames = []

    try:
        for stat, func in iterJSONFiles(args.path):
            try:
                total += 1
                funcNames.append(func)
                totalGED += stat["total_ged"]
                singleGEDs.append(stat["total_ged"])
                SourceZHK.append(stat["avg_source_zhk"])
                DecompZHK.append(stat["avg_decomp_zhk"])
                matchedZHK += stat["matched_zhk"]
                notMatchedZHK += stat["not_matched_zhk"]
                SavePoints.append(stat["avg_save_points"])
                avgZHKSize.append(stat["avg_zhk_size"])
                GEDTimeout += stat["ged_timeouts"]
                GEDNoTimeout += stat["ged_no_timeout"]
                avgGEDTime.append(stat["avg_ged_time"])
                gedTimes.extend(stat["ged_times"])
            except Exception as e:
                print("[ERROR]",e)
                continue
        if args.reconstructTiemoutsFromGEDTimes:
            temp = np.array(gedTimes,np.float32)
            GEDTimeout = len(temp[temp>(args.reconstructTiemoutsFromGEDTimes-0.01)])
            GEDNoTimeout = len(temp[temp<=(args.reconstructTiemoutsFromGEDTimes - 0.01)])
    except Exception as e:
        print("[ERROR] ",e)

    if not os.path.exists("./plots/"):
        os.makedirs("./plots/")

    plot_histogramm(gedTimes,"Histrogramm der GED-Zeiten","benötigte GED-Zeit","Häufigkeit",True,"GED-Times.png")
    plot_histogramm2Sets(SourceZHK,DecompZHK,"Durchschnittliche Größe der ZHK","Größe der ZHK","Häufigkeit","Source-Code","Decompilat",np.mean(avgZHKSize),"ZHKSizeComparison.png")
    plot_bar_chart([GEDTimeout,GEDNoTimeout],["Timeout","no Timeout"],"Timeouts during GED calculation",name="GED-Timeouts.png")
    plot_bar_chart([np.mean(SourceZHK),np.mean(DecompZHK),np.mean(matchedZHK),np.mean(notMatchedZHK)],["avg #ZHK Source-Code","avg #ZHK Decompilat","matched ZHK","non-matched ZHK"],"Zusammenhangskomponenten",name="ZHKMatching.png")
    create_pie_chart(singleGEDs,"Anteile der Funktionen an der Gesamt-GED","GED-Composition.png",funcNames,4)
    print("TOTAL GED:",totalGED)
    print("TOTAL FUNCTIONS EVALUATED:",total)


def getTotalGED(path : str):
    totalGED = 0
    for stat in iterJSONFiles(path):
        totalGED += stat[totalGED]
    return totalGED


def plot_bar_chart(values, labels=None, title="Balkendiagramm", colors=None, name : str = "BarChart.png"):
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
    
    plt.figure(figsize=(max(6, num_bars*2.5), 5))  # breite passt sich der Anzahl an
    plt.bar(x_pos, values, color=colors[:num_bars], edgecolor='black')
    
    # Werte über die Balken schreiben
    for i, v in enumerate(values):
        plt.text(i, v + 0.01 * max(values), f"{v:.2f}", ha='center', va='bottom')
    
    plt.xticks(x_pos, labels)
    plt.ylabel("Anzahl")
    plt.title(title)
    plt.grid(axis='y', alpha=0.5)
    plt.savefig(f"plots/{name}")
    plt.close()

def plot_histogramm(data,title,x,y,withavg : bool,name : str = "Histrogramm.png"):
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
    plt.hist(data, bins=bins, density=True, edgecolor='black')
    if withavg:
        plt.axvline(mean_value, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {mean_value:.2f}')
    plt.legend()
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.grid(axis='y', alpha=0.75)
    plt.savefig(f"plots/{name}")
    plt.close()

def plot_histogramm2Sets(data1,data2,title,x,y,label1,label2,avgToplot=None,name : str = "DoubleHistogramm.png"):
    """
    Plottet ein Histogramm der Floats in 5er-Bins.
    
    Parameters
    ----------
    data : list of float
        Die zu analysierenden Werte.
    """
    if (not data1) or (not data2):
        print("Keine Daten zum Plotten!")
        return

    max_val = max(*data1,*data2)
    
    # Bin-Grenzen: 0, 5, 10, ..., bis zum nächsten Vielfachen von 5 über max_val
    bins = np.arange(0, max_val + 5, 2)

    plt.figure(figsize=(8,5))
    plt.hist(data1,alpha=0.5, bins=bins,density=True,label=label1,stacked=True,align="mid",histtype="stepfilled",linestyle="-",linewidth=1.5)
    plt.hist(data2,alpha=0.5, bins=bins,density=True,label=label2,align="left",histtype="stepfilled",linestyle="-",linewidth=1.5)
    if avgToplot:
        plt.axvline(avgToplot, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {avgToplot:.2f}')
    plt.legend()
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.grid(axis='y', alpha=0.75)
    plt.savefig(f"plots/{name}")
    plt.close()

def create_pie_chart(data, title, filename,funcNames=None,threshold=5):
    # Berechnung der Prozentsätze basierend auf den Werten in der Liste
    total = sum(data)
    percentages = [x / total * 100 for x in data]
    
    # Erzeuge das Tortendiagramm
    plt.figure(figsize=(8,8))
    wedges, texts, autotexts = plt.pie(data, autopct='%1.1f%%', startangle=90, textprops={'color': 'black'})
    
    # Optional: Machen Sie die Beschriftungen schöner
    for i, autotext in enumerate(autotexts):
        if percentages[i] < threshold:
            autotext.set_text("")
        else:
            autotext.set_text(f'{funcNames[i]}: {percentages[i]:.1f}%')  # Zeige den Wert und den Prozentsatz
    
    # Diagramm anpassen
    plt.title(title)
    plt.axis('equal')  # sorgt dafür, dass das Diagramm rund ist (nicht oval)
    
    # Speichern ohne Anzeige
    plt.savefig(f"plots/{filename}")  # Speichert das Diagramm in der angegebenen Datei
    plt.close()  # Verhindert die Anzeige des Diagramms

def iterJSONFiles(path : str):
    folder = pathlib.Path(path)
    for fp in sorted(folder.glob("**/*.json")):
        with fp.open("r") as f:
            data = json.load(f)
            if not isinstance(data,dict):
                pass
            else:
                filename = f"{fp.parent.stem}: {fp.stem}"
                yield data, filename


if __name__ == "__main__":
    makePlots()