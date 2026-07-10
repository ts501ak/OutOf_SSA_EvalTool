#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import json
import traceback
import os

from analyzer import analysis_common as common
from analyzer.shared import RES_DIR, PLOT_DIR


def main():
    try:
        mct = common.mctfunction

        algos = ["boissinot2008", "conditional", "sreedhar"]

        for algo in algos:
            (PLOT_DIR / algo).mkdir(exist_ok=True)

        algoList = []

        for alg in algos:
            path = RES_DIR.joinpath(alg)

            nvL = []
            numCopyAssigL = []
            totalOperatorsL = []
            distinctOperatorsL = []
            totalOperandsL = []
            distinctOperandsL = []
            halsteadVocabularyL = []
            halsteadLengthL = []
            halsteadVolumeL = []
            halsteadDifficultyL = []
            halsteadEffortL = []
            halsteadBugsL = []
            varDefsL = []
            varUsesL = []
            varScopeL = []
            varDistanceL = []
            varMaxLiveDistanceL = []
            varDisjointWebsL = []

            for jsonPath in path.rglob("*.json"):
                with open(jsonPath, encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        print(f"Error loading {jsonPath}: {e}")
                        continue

                nvL.append(data.get("num_variables"))
                numCopyAssigL.append(data.get("num_copy_assignments"))
                totalOperatorsL.append(data.get("total_operators"))
                distinctOperatorsL.append(data.get("distinct_operators"))
                totalOperandsL.append(data.get("total_operands"))
                distinctOperandsL.append(data.get("distinct_operands"))
                halsteadVocabularyL.append(data.get("halstead_vocabulary"))
                halsteadLengthL.append(data.get("halstead_length"))
                halsteadVolumeL.append(data.get("halstead_volume"))
                halsteadDifficultyL.append(data.get("halstead_difficulty"))
                halsteadEffortL.append(data.get("halstead_effort"))
                halsteadBugsL.append(data.get("halstead_bugs"))
                variables = data.get("variables")
                if variables is None:
                    continue
                for x in variables.keys():
                    varDefsL.append(variables[x].get("definitions"))
                    varUsesL.append(variables[x].get("usages"))
                    varScopeL.append(variables[x].get("scopes"))
                    for dist in variables[x]["live_ranges"]:
                        varDistanceL.append(dist["distance"])
                    varMaxLiveDistanceL.append(variables[x].get("max_live_distance"))
                    varDisjointWebsL.append(variables[x].get("disjoint_webs"))

            nvL = common.clear_none(nvL)
            numCopyAssigL = common.clear_none(numCopyAssigL)
            totalOperatorsL = common.clear_none(totalOperatorsL)
            distinctOperatorsL = common.clear_none(distinctOperatorsL)
            totalOperandsL = common.clear_none(totalOperandsL)
            distinctOperandsL = common.clear_none(distinctOperandsL)
            halsteadVocabularyL = common.clear_none(halsteadVocabularyL)
            halsteadVocabularyL = sorted(halsteadVocabularyL, reverse=True)[1:]
            halsteadLengthL = common.clear_none(halsteadLengthL)
            halsteadLengthL = sorted(halsteadLengthL, reverse=True)[1:]
            halsteadVolumeL = common.clear_none(halsteadVolumeL)
            halsteadVolumeL = sorted(halsteadVolumeL, reverse=True)[1:]
            halsteadDifficultyL = common.clear_none(halsteadDifficultyL)
            halsteadDifficultyL = sorted(halsteadDifficultyL, reverse=True)[1:]
            halsteadEffortL = common.clear_none(halsteadEffortL)
            halsteadEffortL = sorted(halsteadEffortL, reverse=True)[1:]
            halsteadBugsL = common.clear_none(halsteadBugsL)
            halsteadBugsL = sorted(halsteadBugsL, reverse=True)[1:]
            varDefsL = common.clear_none(varDefsL)
            varUsesL = common.clear_none(varUsesL)
            varScopeL = common.clear_none(varScopeL)
            varDistanceL = common.clear_none(varDistanceL)
            varDistanceL = [abs(x) for x in varDistanceL]
            varMaxLiveDistanceL = common.clear_none(varMaxLiveDistanceL)
            varDisjointWebsL = common.clear_none(varDisjointWebsL)

            plot_distribution(nvL, xlabel="Number of Variables", ylabel="Frequency", title=f"Distribution of Number of Variables for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "num_variables.png")))
            plot_distribution(numCopyAssigL, xlabel="Number of Copy Assignments", ylabel="Frequency", title=f"Distribution of Number of Copy Assignments for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "num_copy_assignments.png")))
            plot_distribution(halsteadVocabularyL, xlabel="Halstead Vocabulary", ylabel="Frequency", title=f"Distribution of Halstead Vocabulary for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_vocabulary.png")))
            plot_distribution(halsteadLengthL, xlabel="Halstead Length", ylabel="Frequency", title=f"Distribution of Halstead Length for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_length.png")))
            plot_distribution(halsteadVolumeL, xlabel="Halstead Volume", ylabel="Frequency", title=f"Distribution of Halstead Volume for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_volume.png")))
            plot_distribution(halsteadDifficultyL, xlabel="Halstead Difficulty", ylabel="Frequency", title=f"Distribution of Halstead Difficulty for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_difficulty.png")))
            plot_distribution(halsteadEffortL, xlabel="Halstead Effort", ylabel="Frequency", title=f"Distribution of Halstead Effort for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_effort.png")))
            plot_distribution(halsteadBugsL, xlabel="Halstead Bugs", ylabel="Frequency", title=f"Distribution of Halstead Bugs for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "halstead_bugs.png")))
            plot_distribution(varDefsL, xlabel="Number of Variable Definitions", ylabel="Frequency", title=f"Distribution of Number of Variable Definitions for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_defs.png")))
            plot_distribution(varUsesL, xlabel="Number of Variable Uses", ylabel="Frequency", title=f"Distribution of Number of Variable Uses for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_uses.png")))
            plot_distribution(varScopeL, xlabel="Number of Variable Scopes", ylabel="Frequency", title=f"Distribution of Number of Variable Scopes for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_scopes.png")))
            plot_distribution(varDistanceL, xlabel="Variable Live Range Distance", ylabel="Frequency", title=f"Distribution of Variable Live Range Distance for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_live_range_distance.png")))
            plot_distribution(varMaxLiveDistanceL, xlabel="Variable Max Live Range Distance", ylabel="Frequency", title=f"Distribution of Variable Max Live Range Distance for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_max_live_range_distance.png")))
            plot_distribution(varDisjointWebsL, xlabel="Number of Disjoint Webs", ylabel="Frequency", title=f"Distribution of Number of Disjoint Webs for {alg}", save_path=str(PLOT_DIR.joinpath(alg, "var_disjoint_webs.png")))

            algoList.append([nvL, numCopyAssigL, totalOperatorsL, distinctOperatorsL, totalOperandsL, distinctOperandsL, halsteadVocabularyL, halsteadLengthL, halsteadVolumeL, halsteadDifficultyL, halsteadEffortL, halsteadBugsL, varDefsL, varUsesL, varScopeL, varDistanceL, varMaxLiveDistanceL, varDisjointWebsL])

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][0]), mct(algoList[0][1])],
                [mct(algoList[1][0]), mct(algoList[1][1])],
                [mct(algoList[2][0]), mct(algoList[2][1])],
            ],
            value_labels=["Number of Variables", "Number of Copy Assignments"],
            title="Comparison of SSA Algorithms - Variables and Copy Assignments",
            save_path=str(PLOT_DIR.joinpath("comparisonVariablesCopyAssignments.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][2]), mct(algoList[0][3]), mct(algoList[0][4]), mct(algoList[0][5])],
                [mct(algoList[1][2]), mct(algoList[1][3]), mct(algoList[1][4]), mct(algoList[1][5])],
                [mct(algoList[2][2]), mct(algoList[2][3]), mct(algoList[2][4]), mct(algoList[2][5])],
            ],
            value_labels=["Total Operators", "Distinct Operators", "Total Operands", "Distinct Operands"],
            title="Comparison of SSA Algorithms - Halstead Components",
            save_path=str(PLOT_DIR.joinpath("comparisonHalsteadComponents.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][6]), mct(algoList[0][7]), mct(algoList[0][9]), mct(algoList[0][11])],
                [mct(algoList[1][6]), mct(algoList[1][7]), mct(algoList[1][9]), mct(algoList[1][11])],
                [mct(algoList[2][6]), mct(algoList[2][7]), mct(algoList[2][9]), mct(algoList[2][11])],
            ],
            value_labels=["Halstead Vocabulary", "Halstead Length", "Halstead Difficulty", "Halstead Bugs"],
            title="Comparison of SSA Algorithms - Halstead Metrics",
            save_path=str(PLOT_DIR.joinpath("comparisonHalsteadMetrics.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][8])],
                [mct(algoList[1][8])],
                [mct(algoList[2][8])],
            ],
            value_labels=["Halstead Volume"],
            title="Comparison of SSA Algorithms - Halstead Volume",
            save_path=str(PLOT_DIR.joinpath("comparisonHalsteadVolume.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][10])],
                [mct(algoList[1][10])],
                [mct(algoList[2][10])],
            ],
            value_labels=["Halstead Effort"],
            title="Comparison of SSA Algorithms - Halstead Effort",
            save_path=str(PLOT_DIR.joinpath("comparisonHalsteadEffort.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][12]), mct(algoList[0][13])],
                [mct(algoList[1][12]), mct(algoList[1][13])],
                [mct(algoList[2][12]), mct(algoList[2][13])],
            ],
            value_labels=["Average Variable Definitions", "Average Variable Uses"],
            title="Comparison of SSA Algorithms - Variable Definitions and Uses",
            save_path=str(PLOT_DIR.joinpath("comparisonVariableDefsUses.png"))
        )

        plot_categorical_values(
            categories=algos,
            values_per_category=[
                [mct(algoList[0][14]), mct(algoList[0][15]), mct(algoList[0][16]), mct(algoList[0][17])],
                [mct(algoList[1][14]), mct(algoList[1][15]), mct(algoList[1][16]), mct(algoList[1][17])],
                [mct(algoList[2][14]), mct(algoList[2][15]), mct(algoList[2][16]), mct(algoList[2][17])],
            ],
            value_labels=["Average Variable Scope", "Average Variable Live Range Distance", "Average Variable Max Live Range Distance", "Average Number of Disjoint Webs"],
            title="Comparison of SSA Algorithms - Scopes and Live Ranges",
            save_path=str(PLOT_DIR.joinpath("comparisonVariableScopesLiveRanges.png"))
        )
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)


def plot_distribution(
    data,
    xlabel="Wert",
    ylabel="Häufigkeit",
    title="Verteilung der Werte",
    save_path="distribution.png"
):
    if not data:
        raise ValueError("Die Datenliste darf nicht leer sein.")

    data = np.asarray(data, dtype=float)

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    q75, q25 = np.percentile(data, [75, 25])
    iqr = q75 - q25

    if iqr > 0:
        bin_width = 2 * iqr / (len(data) ** (1 / 3))
        bins = max(5, int(np.ceil((data.max() - data.min()) / bin_width)))
    else:
        bins = min(20, max(5, int(np.sqrt(len(data)))))

    ax.hist(data, bins=bins, edgecolor="black", alpha=1, color="olive")

    mean_value = float(np.mean(data))
    ax.axvline(mean_value, color="sienna", linestyle="--", linewidth=2, label=f"Durchschnitt: {mean_value:.2f}")

    x_min = data.min()
    x_max = data.max()

    margin = (x_max - x_min) * 0.05
    if margin == 0:
        margin = 1

    ax.set_xlim(x_min - margin, x_max + margin)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="best")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_categorical_values(
    categories,
    values_per_category,
    value_labels,
    title="Kategorisierte Werte",
    save_path="categorical_values.png",
    figsize=(14, 7),
):
    if len(categories) != len(values_per_category):
        raise ValueError(
            "Anzahl der Kategorien und Wertelisten muss übereinstimmen."
        )

    n_metrics = len(value_labels)

    for values in values_per_category:
        if len(values) != n_metrics:
            raise ValueError(
                "Jede Kategorie muss genau "
                f"{n_metrics} Werte besitzen."
            )

    os.makedirs(
        os.path.dirname(save_path) or ".",
        exist_ok=True
    )

    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.colormaps['Dark2'](np.linspace(0, 1, n_metrics))

    x = np.arange(len(categories))

    total_width = 0.8
    bar_width = total_width / n_metrics

    for metric_idx, metric_name in enumerate(value_labels):
        metric_values = [
            values[metric_idx]
            for values in values_per_category
        ]

        offset = (
            metric_idx - (n_metrics - 1) / 2
        ) * bar_width

        bars = ax.bar(
            x + offset,
            metric_values,
            width=bar_width,
            color=colors[metric_idx],
            label=metric_name
        )

        for bar in bars:
            height = bar.get_height()

            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=8
            )

    ax.set_xticks(x)
    ax.set_xticklabels(
        categories,
        rotation=45 if len(categories) > 8 else 0,
        ha="right" if len(categories) > 8 else "center"
    )

    all_values = [
        value
        for values in values_per_category
        for value in values
    ]

    max_value = max(all_values)
    min_value = min(all_values)

    padding = max(
        (max_value - min_value) * 0.1,
        max_value * 0.05
    )

    ax.set_ylim(
        max(0, min_value - padding),
        max_value + padding
    )

    ax.set_title(title)

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.4
    )

    ax.legend(
        title="Werte",
        loc="best"
    )

    fig.tight_layout()

    plt.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


if __name__ == "__main__":
    main()