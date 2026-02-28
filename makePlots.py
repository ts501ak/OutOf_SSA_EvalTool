#!/usr/bin/env python3 

from shared import PLOTS_DIR, RES_DIR, clear_and_create_dir
import matplotlib.pyplot as plt
from typing import Optional
from pathlib import Path
import numpy as np
import argparse
import json
import os

def makePlots(reconstructTiemoutsFromGEDTimes: Optional[int] = None):
    # Data Collections
    total = 0
    totalGED = 0
    matchedGED = 0
    unmatchedGED = 0
    SourceZHK = []
    DecompZHK = []
    matchedZHK_list = []
    notMatchedZHK_list = []
    matchedZHK_total = 0
    notMatchedZHK_total = 0
    SavePoints = []
    avgZHKSize = []
    GEDTimeout = 0
    GEDMatchedTimeout = 0
    GEDUnmatchedTimeout = 0
    GEDNoTimeout = 0
    avgGEDTime = []
    gedTimes = []
    singleGEDs = []
    funcNames = []
    ratioMatched = []
    sizeUnmatchedZHK = []
    sizeMatchedZHK = []

    try:
        for stat, func in iterJSONFiles(RES_DIR):
            try:
                total += 1
                funcNames.append(func)
                
                # GED Values
                val_ged = stat["total_ged"]
                totalGED += val_ged
                singleGEDs.append(val_ged)
                
                # ZHK Data
                s_zhk = stat["avg_source_zhk"]
                d_zhk = stat["avg_decomp_zhk"]
                m_zhk = stat["matched_zhk"]
                nm_zhk = stat["not_matched_zhk"]
                
                SourceZHK.append(s_zhk)
                DecompZHK.append(d_zhk)
                matchedZHK_list.append(m_zhk)
                notMatchedZHK_list.append(nm_zhk)
                matchedZHK_total += m_zhk
                notMatchedZHK_total += nm_zhk
                
                # Calculate Match Ratio for this specific function
                total_zhk = m_zhk + nm_zhk
                ratioMatched.append(m_zhk / total_zhk if total_zhk > 0 else 0)

                # Metadata
                SavePoints.append(stat["avg_save_points"])
                avgZHKSize.append(stat["avg_zhk_size"])
                GEDTimeout += stat["ged_timeouts"]
                GEDNoTimeout += stat["ged_no_timeout"]
                avgGEDTime.append(stat["avg_ged_time"])
                gedTimes.extend(stat["ged_times"])
                sizeUnmatchedZHK.extend(stat["unmatched_ZHK_size"])
                sizeMatchedZHK.extend(stat["matched_ZHK_size"])
                matchedGED += stat["matched_ged"]
                unmatchedGED += stat["unmatched_ged"]
                GEDUnmatchedTimeout += stat["unmatchedTimeouts"]
                GEDMatchedTimeout += stat["matchedTimeouts"]

            except Exception as e:
                print(f"[ERROR processing {func}]", e)
                continue

        if reconstructTiemoutsFromGEDTimes:
            temp = np.array(gedTimes, np.float32)
            GEDTimeout = len(temp[temp > (reconstructTiemoutsFromGEDTimes - 0.01)])
            GEDNoTimeout = len(temp[temp <= (reconstructTiemoutsFromGEDTimes - 0.01)])
            
    except Exception as e:
        print("[ERROR during file iteration] ", e)

    # create and clear the directory
    clear_and_create_dir(PLOTS_DIR)

    # 1. GED Time Distribution
    plot_histogramm(gedTimes, "Histogramm der GED-Zeiten", "benötigte GED-Zeit (s)", "Häufigkeit", True, "GED-Times.png")
    
    # 2. GED Population (The distribution of total_ged values)
    plot_histogramm(singleGEDs, "Histogramm der GED-Werte (Population)", "GED Wert", "Häufigkeit", True, "GED-Population.png")

    # 3. ZHK Size Comparison
    plot_histogramm2Sets(SourceZHK, DecompZHK, "Durchschnittliche Größe der ZHK", "Größe der ZHK", "Häufigkeit", "Source-Code", "Decompilat", np.mean(avgZHKSize), "ZHKSizeComparison.png")
    
    # 4. GED Timeouts Bar Chart
    plot_bar_chart([GEDTimeout, GEDNoTimeout], ["Timeout", "no Timeout"], "Timeouts during GED calculation", name="GED-Timeouts.png")
    
    # 5. Matching Overview
    plot_bar_chart([np.mean(SourceZHK), np.mean(DecompZHK), np.mean(matchedZHK_list), np.mean(notMatchedZHK_list)], 
                   ["avg #ZHK Source", "avg #ZHK Decomp", "avg matched", "avg non-matched"], 
                   "Zusammenhangskomponenten", name="ZHKMatching.png")
    
    # 6. GED Pie Chart (Composition)
    create_pie_chart(singleGEDs, "Anteile der Funktionen an der Gesamt-GED", "GED-Composition.png", funcNames, 4)

    # 7. Correlation Plot: GED vs. Calculation Time
    # Note: We use avgGEDTime because gedTimes might have multiple entries per function
    if len(singleGEDs) == len(avgGEDTime):
        plot_scatter(singleGEDs, avgGEDTime, "Correlation: GED Value vs. Time", "GED Value", "Avg Time (s)", "GED_vs_Time_Scatter.png")

    # 8. Matching Success Ratio Histogram
    plot_histogramm(ratioMatched, "Matching Success Ratio Distribution", "Ratio (Matched / Total ZHK)", "Frequency", True, "Matching_Success_Ratio.png", custom_bins=np.linspace(0,1,11))

    # 9. Distribution of Matches an no matches per function
    plot_histogramm2Sets(matchedZHK_list,notMatchedZHK_list,"Verteilung der Matches und Non-Matches je Funktion","#ZHK","Häufigkeit","# matched ZHK","# non-matched ZHK",None,"DistributionMatchesPerFunction.png",1)

    # 10. Histogramm of the size of matched and unmatched ZHK
    plot_histogramm2Sets(sizeUnmatchedZHK,sizeMatchedZHK,"Größe von (nicht) gematchten ZHK","Größe","Häufigkeit","Unmatched ZHK","Matched ZHK",None,"VerteilungGröße(Un-)matchedZHK.png",1)

    # 11. Pie Chart of matched vs. unmatched GED
    create_pie_chart([matchedGED,unmatchedGED],"Composition of total GED","GEDComposition.png",["matched","unmatched"],1)

    # 12. Pie Chart of matched vs. unmatched Tiemouts
    create_pie_chart([GEDMatchedTimeout,GEDUnmatchedTimeout],"Matched vs. Unmatched Tiemouts","TiemeoutsMatchedVSUnmatched.png",["Matched Timeouts","Unmatched Tiemouts"],1)

    print("-" * 30)
    print(f"TOTAL GED: {totalGED:.2f}")
    print(f"TOTAL FUNCTIONS EVALUATED: {total}")
    print(f"GLOBAL MATCHING RATE: {(matchedZHK_total / (matchedZHK_total + notMatchedZHK_total) * 100):.2f}%" if (matchedZHK_total + notMatchedZHK_total) > 0 else "N/A")
    print("-" * 30)


def plot_bar_chart(values, labels=None, title="Balkendiagramm", colors=None, name="BarChart.png"):
    num_bars = len(values)
    if labels is None:
        labels = [str(i+1) for i in range(num_bars)]
    if colors is None:
        colors = plt.cm.tab20.colors
        if num_bars > len(colors):
            colors = ['skyblue'] * num_bars
    
    x_pos = range(num_bars)
    plt.figure(figsize=(max(8, num_bars*1.5), 5))
    plt.bar(x_pos, values, color=colors[:num_bars], edgecolor='black')
    
    for i, v in enumerate(values):
        plt.text(i, v + 0.01 * max(values), f"{v:.2f}", ha='center', va='bottom')
    
    plt.xticks(x_pos, labels, rotation=15)
    plt.ylabel("Anzahl")
    plt.title(title)
    plt.grid(axis='y', alpha=0.5)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name)
    plt.close()

def plot_histogramm(data, title, x, y, withavg, name="Histogramm.png", custom_bins=None):
    if not data:
        print(f"Keine Daten zum Plotten für {name}!")
        return

    mean_value = np.mean(data)
    if custom_bins is not None:
        bins = custom_bins
    else:
        max_val = max(data)
        bins = np.arange(0, max_val + 5, 5)

    plt.figure(figsize=(8,5))
    plt.hist(data, bins=bins, density=True, edgecolor='black', alpha=0.7)
    if withavg:
        plt.axvline(mean_value, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {mean_value:.2f}')
    plt.legend()
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.grid(axis='y', alpha=0.75)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name)
    plt.close()

def plot_histogramm2Sets(data1, data2, title, x, y, label1, label2, avgToplot=None, name="DoubleHistogramm.png",step = 2):
    if (not data1) or (not data2):
        print(f"Keine Daten zum Plotten für {name}!")
        return

    max_val = max(max(data1), max(data2))
    bins = np.arange(0, max_val + step, step)

    plt.figure(figsize=(8,5))
    plt.hist(data1, alpha=0.5, bins=bins, density=True, label=label1, histtype="stepfilled")
    plt.hist(data2, alpha=0.5, bins=bins, density=True, label=label2, histtype="stepfilled")
    if avgToplot:
        plt.axvline(avgToplot, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {avgToplot:.2f}')
    plt.legend()
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.grid(axis='y', alpha=0.75)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name)
    plt.close()

def plot_scatter(x_data, y_data, title, xlabel, ylabel, name):
    plt.figure(figsize=(10, 6))
    plt.scatter(x_data, y_data, alpha=0.6, edgecolors='k')
    
    if len(x_data) > 1:
        try:
            z = np.polyfit(x_data, y_data, 1)
            p = np.poly1d(z)
            plt.plot(sorted(x_data), p(sorted(x_data)), "r--", alpha=0.8, label="Trendline")
        except:
            pass
            
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / name)
    plt.close()

def create_pie_chart(data, title, filename, funcNames=None, threshold=5):
    total = sum(data)
    if total == 0: return
    
    percentages = [x / total * 100 for x in data]
    plt.figure(figsize=(10,10))
    wedges, texts, autotexts = plt.pie(data, autopct='%1.1f%%', startangle=90, textprops={'color': 'black'})
    
    for i, autotext in enumerate(autotexts):
        if percentages[i] < threshold:
            autotext.set_text("")
        else:
            name = funcNames[i] if funcNames else f"ID {i}"
            autotext.set_text(f'{name}\n{percentages[i]:.1f}%')
            autotext.set_fontsize(8)
    
    plt.title(title)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename)
    plt.close()

def iterJSONFiles(folder: Path):
    for fp in sorted(folder.glob("**/*.json")):
        with fp.open("r") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    filename = f"{fp.parent.stem}: {fp.stem}"
                    yield data, filename
            except json.JSONDecodeError:
                print(f"[SKIP] Corrupt JSON: {fp}")


def main():
    parser = argparse.ArgumentParser(description="Collect and visualize the stats in the JSON files")
    parser.add_argument("-r", "--reconstructTiemoutsFromGEDTimes",
        type=int,
        help="The number of Timeouts is reconstructed using the given Timeout"
    )
    args = parser.parse_args()
    makePlots(None)

if __name__ == "__main__":
    main()
