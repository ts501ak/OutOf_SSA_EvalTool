#!/usr/bin/env python3 

from ast import Tuple
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Set

from shared import (
    SSA_ALGOS,
    get_res_dir,
    log_and_print,
    get_plot_dir,
    clear_and_create_dir
)

def plot_bar_chart(values, labels, title, out_path: Path):
    num_bars = len(values)
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
    plt.savefig(out_path)
    plt.close()

def plot_histogramm(data, title, x, y, withavg, out_path: Path, custom_bins=None):
    if not data:
        print(f"Keine Daten zum Plotten für {out_path.name}!")
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
    plt.savefig(out_path)
    plt.close()

def plot_histogramm2Sets(data1, data2, title, x, y, label1, label2, avgToplot, out_path: Path, step=2, log_y=False):
    if (not data1) or (not data2):
        print(f"Keine Daten zum Plotten für {out_path.name}!")
        return

    max_val = max(max(data1), max(data2))
    bins = np.arange(0, max_val + step, step)

    plt.figure(figsize=(8,5))
    plt.hist(data1, alpha=0.5, bins=bins, density=True, label=label1, histtype="stepfilled", align="left",log=log_y)
    plt.hist(data2, alpha=0.5, bins=bins, density=True, label=label2, histtype="stepfilled", align="mid",log=log_y)
    
    if avgToplot:
        plt.axvline(avgToplot, color='red', linestyle='--', linewidth=2, label=f'Durchschnitt: {avgToplot:.2f}')
        
    plt.legend()
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.grid(axis='y', alpha=0.75)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

def plot_scatter(x_data, y_data, title, xlabel, ylabel, out_path: Path):
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
    plt.savefig(out_path)
    plt.close()

def plot_pie_chart(data, title, out_path: Path, funcNames, threshold):
    total = sum(data)
    if total == 0: return
    
    percentages = [x / total * 100 for x in data]
    plt.figure(figsize=(10,10))
    _, _, autotexts = plt.pie(data, autopct='%1.1f%%', startangle=90, textprops={'color': 'black'})
    
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
    plt.savefig(out_path)
    plt.close()

def load_json(file: Path):
    stat = json.loads(file.read_text())
    func = f"{file.parent.stem}: {file.stem}"
    return stat, func


def _make_plots(plot_dir: Path, stat_path: Path, common_files: Set[Path], ged_rec_time: Optional[int] = None):
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
        for file in common_files:
            try:
                stat, func = load_json(file)
            except:
                print(f"[SKIP] JSON: {file}")
                continue

            try:
                total += 1
                funcNames.append(func)
                
                val_ged = stat["total_ged"]
                totalGED += val_ged
                singleGEDs.append(val_ged)
                
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
                
                total_zhk = m_zhk + nm_zhk
                ratioMatched.append(m_zhk / total_zhk if total_zhk > 0 else 0)

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
                log_and_print(f"[-]ERROR processing {func}: {e}", stat_path, print_file=sys.stderr)
                continue

        if ged_rec_time:
            temp = np.array(gedTimes, np.float32)
            GEDTimeout = len(temp[temp > (ged_rec_time - 1)])
            GEDNoTimeout = len(temp[temp <= (ged_rec_time - 1)])
            
    except Exception as e:
        log_and_print(f"[-]ERROR during file iteration] {e}", stat_path, print_file=sys.stderr)

    # 1. GED Time Distribution
    plot_histogramm(gedTimes, "Histogramm der GED-Zeiten", "benötigte GED-Zeit (s)", "Häufigkeit", True, plot_dir / "GED-Times.png")
    
    # 2. GED Population (The distribution of total_ged values)
    plot_histogramm(singleGEDs, "Histogramm der GED-Werte (Population)", "GED Wert", "Häufigkeit", True, plot_dir / "GED-Population.png")

    # 3. ZHK Size Comparison
    plot_histogramm2Sets(SourceZHK, DecompZHK, "Durchschnittliche Größe der ZHK", "Größe der ZHK", "Häufigkeit", "Source-Code", "Decompilat", np.mean(avgZHKSize), plot_dir / "ZHKSizeComparison.png")
    
    # 4. GED Timeouts Bar Chart
    plot_bar_chart([GEDTimeout, GEDNoTimeout], ["Timeout", "no Timeout"], "Timeouts during GED calculation", plot_dir / "GED-Timeouts.png")
    
    # 5. Matching Overview
    plot_bar_chart([np.mean(SourceZHK), np.mean(DecompZHK), np.mean(matchedZHK_list), np.mean(notMatchedZHK_list)], 
                   ["avg #ZHK Source", "avg #ZHK Decomp", "avg matched", "avg non-matched"], 
                   "Zusammenhangskomponenten", plot_dir / "ZHKMatching.png")
    
    # 6. GED Pie Chart (Composition)
    plot_pie_chart(singleGEDs, "Anteile der Funktionen an der Gesamt-GED", plot_dir / "GED-Composition.png", funcNames, 4)

    # 7. Correlation Plot: GED vs. Calculation Time
    if len(singleGEDs) == len(avgGEDTime):
        plot_scatter(singleGEDs, avgGEDTime, "Correlation: GED Value vs. Time", "GED Value", "Avg Time (s)", plot_dir / "GED_vs_Time_Scatter.png")

    # 8. Matching Success Ratio Histogram
    plot_histogramm(ratioMatched, "Matching Success Ratio Distribution", "Ratio (Matched / Total ZHK)", "Frequency", True, plot_dir / "Matching_Success_Ratio.png", custom_bins=np.linspace(0,1,11))

    # 9. Distribution of Matches an no matches per function
    plot_histogramm2Sets(matchedZHK_list, notMatchedZHK_list, "Verteilung der Matches und Non-Matches je Funktion", "#ZHK", "Häufigkeit", "# matched ZHK", "# non-matched ZHK", None, plot_dir / "DistributionMatchesPerFunction.png", 1)

    # 10. Histogramm of the size of matched and unmatched ZHK
    plot_histogramm2Sets(sizeUnmatchedZHK, sizeMatchedZHK, "Größe von (nicht) gematchten ZHK", "Größe", "Häufigkeit", "Unmatched ZHK", "Matched ZHK", None, plot_dir / "VerteilungGröße(Un-)matchedZHK.png", 1, log_y=True)

    # 11. Pie Chart of matched vs. unmatched GED
    plot_pie_chart([matchedGED, unmatchedGED], "Composition of total GED", plot_dir / "GEDComposition.png", ["matched", "unmatched"], 1)

    # 12. Pie Chart of matched vs. unmatched Timeouts
    plot_pie_chart([GEDMatchedTimeout, GEDUnmatchedTimeout], "Matched vs. Unmatched Timeouts", plot_dir / "TimeoutsMatchedVSUnmatched.png", ["Matched Timeouts", "Unmatched Timeouts"], 1)

    log_and_print(f"TOTAL GED: {totalGED:.2f}", stat_path)
    log_and_print(f"TOTAL FUNCTIONS EVALUATED: {total}", stat_path)
    log_and_print(f"GLOBAL MATCHING RATE: {(matchedZHK_total / (matchedZHK_total + notMatchedZHK_total) * 100):.2f}%" if (matchedZHK_total + notMatchedZHK_total) > 0 else "N/A", stat_path)

def get_common_res_files(): 
    common_rel_paths = None
    for ssa_algo in SSA_ALGOS:
        res_dir = get_res_dir(ssa_algo)
        current_files = {p.relative_to(res_dir) for p in res_dir.glob("**/*.json")}
        
        if common_rel_paths is None:
            common_rel_paths = current_files
        else:
            common_rel_paths.intersection_update(current_files)
            
    if not common_rel_paths:
        common_rel_paths = set()
    
    result = []
    for ssa_algo in SSA_ALGOS:
        res_dir = get_res_dir(ssa_algo)
        algo_absolute_paths = {res_dir / rel_path for rel_path in common_rel_paths}
        result.append((ssa_algo, algo_absolute_paths))
            
    return result
def make_all_plots(ged_rec_times: Optional[int] = None, pathOverride = None):
    runs = []
    try:
        if pathOverride:
            override_path = Path(pathOverride)
            if not override_path.exists():
                print(f"[-] Error: Override path does not exist: {override_path}", file=sys.stderr)
                return
            
            runs.append((
                str(override_path),
                Path("./plots"), 
                set(override_path.glob("**/*.json"))
            ))
        else:
            for ssa_algo, files in get_common_res_files(): 
                runs.append((ssa_algo, get_plot_dir(ssa_algo), files))
                
    except Exception as e:
        print(f"[-] Error during file discovery: {e}", file=sys.stderr)
        return

    for name, plot_dir, files in runs:
        try:
            stat_path = plot_dir / "stat.txt"
            clear_and_create_dir(plot_dir)

            log_and_print("-" * 30, stat_path)
            log_and_print(f"Processing: {name}", stat_path)
                
            if files:
                _make_plots(plot_dir, stat_path, files, ged_rec_times)
            else:
                log_and_print("[-] Warning: No files found to plot!", stat_path)
            
            log_and_print("-" * 30, stat_path)
            print()
            
        except Exception as e:
            print(f"[-] Error generating plots for {name}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Collect and visualize the stats in the JSON files")
    parser.add_argument("-r", "--ged-reconstruct-timeouts",
        dest="ged_rec_time",
        type=int,
        help="The number of Timeouts is reconstructed using the given Timeout"
    )
    parser.add_argument("-p","--pathOverride", #BITTE DIESMAL DRIN LASSEN!
        dest="PathOverride",
        type=str,
        help="OVERRIDES the standard Res-Path"
    )
    args = parser.parse_args()
    make_all_plots(args.ged_rec_time,args.PathOverride)

if __name__ == "__main__":
    main()
