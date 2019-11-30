import json
import re
from io import BytesIO
from typing import Dict, Tuple
from zipfile import ZipFile

import networkx as nx
import pandas as pd
import pyproj
from matplotlib.patches import Polygon

# -- Variables --

archive = ZipFile("data/RATP_GTFS_LINES.zip")

stations: Dict[str, pd.DataFrame] = dict()
stop_times: Dict[str, pd.DataFrame] = dict()
trips: Dict[str, pd.DataFrame] = dict()
transfers: Dict[str, pd.DataFrame] = dict()

for z in archive.filelist:
    match = re.match('.*(METRO_\d+b?|RER_\w).zip', z.filename)
    if match:
        line_nb = match.group(1)
        with archive.open(z.filename, 'r') as fh:
            b = ZipFile(BytesIO(fh.read()))
            # information about stations (id, name, latlon)
            with b.open('stops.txt') as fh:
                stations[line_nb] = pd.read_csv(BytesIO(fh.read()))
            # information about trips with sequences of stations and durations
            with b.open('stop_times.txt') as fh:
                stop_times[line_nb] = pd.read_csv(BytesIO(fh.read()))
            # associate a trip to a route
            # (particularly relevant for RER missions)
            with b.open('trips.txt') as fh:
                trips[line_nb] = pd.read_csv(BytesIO(fh.read()))
            with b.open('transfers.txt') as fh:
                transfers[line_nb] = pd.read_csv(BytesIO(fh.read()))

# Merged station information

all_stations = pd.concat(
    [value.assign(line=key)
     for key, value in stations.items()]
).set_index('stop_id')

# Projected coordinates information

Lambert93 = pyproj.Proj(init='EPSG:2154')
x, y = Lambert93(all_stations.stop_lon.values, all_stations.stop_lat.values)
pos: Dict[int, Tuple[float, float]] = dict(
    (id_, (x_, y_)) for id_, x_, y_ in zip(all_stations.index, x, y)
)


def search_station(pattern):
    """Fuzzy search for stations."""
    matching_lines = all_stations.stop_name.str.match(pattern)
    return all_stations [matching_lines].stop_name.to_dict()

# Contours from OpenStreetMap

with open('data/paris_shapes.json', 'r') as fh:
    data = json.load(fh)
    paris_shape = data['paris_shape']
    rivers_shape = data['rivers_shape']


# -- Colors from the documentation --

line_colors: Dict[str, str] = {
    'METRO_1': "#{:0>2x}{:0>2x}{:0>2x}".format(242, 201, 49),
    'METRO_2': "#{:0>2x}{:0>2x}{:0>2x}".format(33, 110, 180),
    'METRO_3': "#{:0>2x}{:0>2x}{:0>2x}".format(154, 153, 64),
    'METRO_3b': "#{:0>2x}{:0>2x}{:0>2x}".format(137, 199, 214),
    'METRO_4': "#{:0>2x}{:0>2x}{:0>2x}".format(187, 77, 152),
    'METRO_5': "#{:0>2x}{:0>2x}{:0>2x}".format(222, 139, 83),
    'METRO_6': "#{:0>2x}{:0>2x}{:0>2x}".format(121, 187, 146),
    'METRO_7': "#{:0>2x}{:0>2x}{:0>2x}".format(223, 154, 177),
    'METRO_7b': "#{:0>2x}{:0>2x}{:0>2x}".format(121, 187, 146),
    'METRO_8': "#{:0>2x}{:0>2x}{:0>2x}".format(197, 163, 202),
    'METRO_9': "#{:0>2x}{:0>2x}{:0>2x}".format(205, 200, 63),
    'METRO_10': "#{:0>2x}{:0>2x}{:0>2x}".format(223, 176, 57),
    'METRO_11': "#{:0>2x}{:0>2x}{:0>2x}".format(142, 101, 56),
    'METRO_12': "#{:0>2x}{:0>2x}{:0>2x}".format(50, 142, 91),
    'METRO_13': "#{:0>2x}{:0>2x}{:0>2x}".format(137, 199, 214),
    'METRO_14': "#{:0>2x}{:0>2x}{:0>2x}".format(103, 50, 142),
    'RER_A': "#{:0>2x}{:0>2x}{:0>2x}".format(255, 20, 0),
    'RER_B': "#{:0>2x}{:0>2x}{:0>2x}".format(60, 145, 220)
}



def plot_ratp(ax, g, color=None):

    nx.draw_networkx(
        g, ax=ax,
        pos=pos,
        node_size=5,
        node_color='grey' if color is None else color,
        edge_color=[g[u][v]['color'] for u, v in g.edges]
        if color is None else color,
        width=[.7 if g[u][v]['type'] == 'RER'
               else .5 for u, v in g.edges],
        with_labels=False,
        arrows=False,
    )

    ax.add_patch(
        Polygon(
            paris_shape,
            facecolor='whitesmoke',
            alpha=.5,
            zorder=-2
        )
    )

    for (x, y) in rivers_shape:
        ax.plot(
            x, y,
            color='lightsteelblue',
            alpha=.5,
            linewidth=1.5
        )

    ax.set_axis_off()
    ax.set_xlim((642500, 662000))
    ax.set_ylim((6856000, 6869000))
    ax.set_aspect(1)

def plot_path(ax, g, sol):

    for ix, (orig, dest) in enumerate(zip(sol['path'], sol['path'][1:])):

        ax.plot(
            *list(zip(*[pos[orig.id], pos[dest.id]])),
            color=g[orig.id][dest.id]['color'],
            marker='.',
            linewidth=2
        )

        if g[orig.id][dest.id]['type'] == 'CONNECTION':
            ax.text(
                *pos[orig.id],
                f"{sol['path'][ix]!r}",
                fontsize=13,
                horizontalalignment='right',
                verticalalignment='top')
            ax.text(
                *pos[dest.id],
                f"{sol['path'][ix+1]!r}",
                fontsize=13,
            )


    ax.text(
        *pos[sol['path'][0].id],
        f"{sol['path'][0]!r}",
        fontsize=13,
        horizontalalignment='right',
        verticalalignment='top')

    ax.text(
        *pos[sol['path'][-1].id],
        f"{sol['path'][-1]!r}",
        fontsize=13,
    )


def animate_path(ax, sol):

    ax.text(
        *pos[sol['path'][0].id],
        f"{sol['path'][0]!r}",
        fontsize=13,
        horizontalalignment='right',
        verticalalignment='top'
    )

    ax.scatter(
        *pos[sol['path'][-1].id],
        color="crimson",
        s=15,
        marker='^',
        zorder=2
    )

    ax.text(
        *pos[sol['path'][-1].id],
        f"{sol['path'][-1]!r}",
        fontsize=13
    )

    def animate(i):
        elts = ax.scatter(
            *list(zip(*list(pos[a] for a in sol['stats'].search_path[:i+1]))),
            color="crimson",
            s=15,
            zorder=2
        )
        return []

    return animate


class Station(object):
    """Pretty printing of the stations from their id."""

    def __init__(self, id_):
        self.id = id_
        self.name = all_stations.loc[id_].stop_name
        self.line = all_stations.loc[id_].line

    def __repr__(self):
        return f"{self.name} ({self.line.split('_')[1]})"


class StatsPatch(object):

    """Ugly patch to track what happens during the A* algorithm.
    Don't do this alone at home without adult supervision.
    """

    def __init__(self, g):
        self.g = g
        self.counter = 0
        self.search_path = []

    def __enter__(self):
        self._old_view_getitem = nx.classes.coreviews.AdjacencyView.__getitem__
        def new_view_getitem(g, n):
            self.counter += 1
            self.search_path.append(n)
            return self._old_view_getitem(g, n)
        nx.classes.coreviews.AdjacencyView.__getitem__ = new_view_getitem

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        nx.classes.coreviews.AdjacencyView.__getitem__ = self._old_view_getitem

