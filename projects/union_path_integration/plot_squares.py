# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2018, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""Plot capacity charts."""

from collections import defaultdict
import json
import math
import os
import itertools

import matplotlib.pyplot as plt
import matplotlib.lines
import numpy as np

import ambiguity_index

CWD = os.path.dirname(os.path.realpath(__file__))
CHART_DIR = os.path.join(CWD, "charts")


def createCharts(inFilenames, outFilename,
                 moduleWidths=(6, 9, 12),
                 moduleCounts=(6, 12, 18),
                 maxNumObjectsByParams={},
                 numObjectsAllowList=None):
  if not os.path.exists(CHART_DIR):
    os.makedirs(CHART_DIR)

  recognitionTimeResults = defaultdict(lambda: defaultdict(list))
  capacityResults = defaultdict(lambda: defaultdict(list))

  for inFilename in inFilenames:
    with open(inFilename, "r") as f:
      experiments = json.load(f)
    for exp in experiments:
      moduleWidth = exp[0]["locationModuleWidth"]
      numObjects = exp[0]["numObjects"]

      if numObjectsAllowList is not None and numObjects not in numObjectsAllowList:
        continue

      numModules = exp[0]["numModules"]

      recognitionTimes = []
      for numSensationsStr, numOccurrences in exp[1].items():
        if numSensationsStr == "null":
          recognitionTimes += [np.inf] * numOccurrences
        else:
          recognitionTimes += [int(numSensationsStr)] * numOccurrences
      recognitionTimeResults[(moduleWidth, numModules)][numObjects] += recognitionTimes

      failed = exp[1].get("null", 0)
      accuracy = 1.0 - (float(failed) / float(numObjects))
      capacityResults[(moduleWidth, numModules)][numObjects].append(accuracy)

  locs, labels = ambiguity_index.getTotalExpectedOccurrencesTicks_2_5(
      ambiguity_index.numOtherOccurrencesOfMostUniqueFeature_lowerBound50_100features_10locationsPerObject)

  ax2_color = 'gray'
  fig, (axRecognitionTime, axCapacity) = plt.subplots(figsize=(6, 8), nrows=2, sharex=True)

  #
  # CAPACITY
  #

  ax2Capacity = axCapacity.twiny()
  # Optional: swap axes
  # axCapacity.xaxis.tick_top()
  # axCapacity.xaxis.set_label_position('top')
  # ax2Capacity.xaxis.tick_bottom()
  # ax2Capacity.xaxis.set_label_position('bottom')


  colors = ("C0", "C1", "C2")
  markers = ("o", "o", "o")
  markerSizes = (2, 4, 6)
  for moduleWidth, color in reversed(zip(moduleWidths, colors)):
    for numModules, marker, markerSize in zip(moduleCounts, markers, markerSizes):
      resultsByNumObjects = capacityResults[(moduleWidth, numModules)]
      expResults = [(numObjects, sum(results) / len(results))
                     for numObjects, results in resultsByNumObjects.iteritems()
                    if (moduleWidth, numModules) not in maxNumObjectsByParams
                    or numObjects <= maxNumObjectsByParams[(moduleWidth, numModules)]]

      x = []
      y = []
      for i, j in sorted(expResults):
        x.append(i)
        y.append(j)

      axCapacity.plot(
        x, y, "{}-".format(marker), color=color, linewidth=1, markersize=markerSize
      )

  axCapacity.set_xlabel("# learned objects")
  axCapacity.set_ylabel("Recognition accuracy after many sensations")
  # ax2Capacity.set_xlabel("Sensory ambiguity index")

  ax2Capacity.set_xticks(locs)
  ax2Capacity.set_xticklabels(labels)
  ax2Capacity.set_xlim(axCapacity.get_xlim())
  ax2Capacity.xaxis.label.set_color(ax2_color)
  ax2Capacity.tick_params(axis='x', colors=ax2_color)

  #
  # RECOGNITION TIME
  #

  ax2RecognitionTime = axRecognitionTime.twiny()
  # Optional: swap axes
  # axRecognitionTime.xaxis.tick_top()
  # axRecognitionTime.xaxis.set_label_position('top')
  # ax2RecognitionTime.xaxis.tick_bottom()
  # ax2RecognitionTime.xaxis.set_label_position('bottom')

  colors = ("C0", "C1", "C2")
  markers = ("o", "o", "o")
  markerSizes = (2, 4, 6)
  for moduleWidth, color in reversed(zip(moduleWidths, colors)):
    for numModules, marker, markerSize in zip(moduleCounts, markers, markerSizes):
      resultsByNumObjects = recognitionTimeResults[(moduleWidth, numModules)]

      expResults = sorted((numObjects, np.median(results))
                          for numObjects, results in resultsByNumObjects.iteritems())

      # Results up to the final non-infinite median.
      lineResults = [(numObjects, median)
                     for numObjects, median in expResults
                     if median != np.inf]

      # Results excluding the final non-infinite median.
      numCircleMarkers = len(lineResults)
      if len(lineResults) < len(expResults):
        numCircleMarkers -= 1

      axRecognitionTime.plot([numObjects for numObjects, median in lineResults],
               [median for numObjects, median in lineResults],
               "{}-".format(marker), markevery=xrange(numCircleMarkers),
               color=color, linewidth=1, markersize=markerSize)

      if (len(lineResults) < len(expResults) and len(lineResults) > 0):
        endNumObjects, endMedian = lineResults[-1]
        axRecognitionTime.plot([endNumObjects], [endMedian], "x", color=color,
                 markeredgewidth=markerSize/2, markersize=markerSize*1.5)

  axRecognitionTime.set_ylim(0, axRecognitionTime.get_ylim()[1])
  # axRecognitionTime.set_xlabel("# learned objects")
  axRecognitionTime.set_ylabel("Median # sensations before recognition")
  ax2RecognitionTime.set_xlabel("Median # locations recalled by an object's most unique feature", labelpad=8)

  # Carefully use whitespace in title to shift the entries in the legend to
  # align with the previous legend.
  leg = axRecognitionTime.legend(loc="upper right", title="Cells per module:       ",
                   bbox_to_anchor=(1.035, 1.0),
                   frameon=False,
                   handles=[matplotlib.lines.Line2D([], [], color=color)
                            for color in colors],
                   labels=["{}x{}".format(moduleWidth, moduleWidth)
                           for moduleWidth in moduleWidths])
  axRecognitionTime.add_artist(leg)


  leg = axRecognitionTime.legend(loc="center right", title="Number of modules:",
                   bbox_to_anchor=(1.0, 0.5),
                   frameon=False,
                   handles=[matplotlib.lines.Line2D([], [],
                                                    marker=marker,
                                                    markersize=markerSize,
                                                    color="black")
                            for marker, markerSize in zip(markers, markerSizes)],
                   labels=moduleCounts)

  ax2RecognitionTime.set_xticks(locs)
  ax2RecognitionTime.set_xticklabels(labels)
  ax2RecognitionTime.set_xlim(axRecognitionTime.get_xlim())
  ax2RecognitionTime.xaxis.label.set_color(ax2_color)
  ax2RecognitionTime.tick_params(axis='x', colors=ax2_color)

  plt.tight_layout()

  filePath = os.path.join(CHART_DIR, outFilename)
  print "Saving", filePath
  plt.savefig(filePath)



if __name__ == "__main__":
  createCharts(
    ["results/squares_varyNumModules_100_feats_6_moduleWidth.json",
     "results/squares_varyNumModules_100_feats_9_moduleWidth.json",
     "results/squares_varyNumModules_100_feats_12_moduleWidth.json",
    ],
    "combined100_squares_varyCellsPerModule_varyNumModules.pdf",
    maxNumObjectsByParams={
      (12, 18): 600
      # (1.0, 4): 150,
    },
    numObjectsAllowList=set([3] + range(20, 601, 20)),
  )
