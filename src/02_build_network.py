#!/usr/bin/env python3
"""
Build 1D reach network topology for East River.

Uses network_edges.csv from real HydroShare processing (stage 01).
Fails if network is missing — no synthetic fallback.
"""

from __future__ import annotations

import argparse

import networkx as nx
import pandas as pd

from src.east_river_real_data import export_nhdplus_network_csv
from src.real_data_guard import RealDataRequiredError, assert_no_synthetic_provenance, require_file, require_real_data
from src.utils import ensure_dirs, load_config, resolve_path, setup_logging

LOG = setup_logging("build_network")


def build_graph(network_df: pd.DataFrame) -> nx.DiGraph:
    """Directed graph: upstream -> downstream."""
    g = nx.DiGraph()
    for _, row in network_df.iterrows():
        g.add_node(
            row["reach_id"],
            length_m=row["length_m"],
            width_m=row["width_m"],
            slope=row.get("slope", 0.01),
            area_m2=row.get("area_m2", row["length_m"] * row["width_m"]),
        )
        up = row.get("upstream_id")
        if pd.notna(up) and up:
            g.add_edge(up, row["reach_id"])
    return g


def compute_topological_order(g: nx.DiGraph) -> list[str]:
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("Network contains cycles; expected dendritic DAG.")
    return list(nx.topological_sort(g))


def main(config_path: str | None = None) -> None:
    cfg = load_config(config_path)
    require_real_data(cfg, "02_build_network")
    ensure_dirs(cfg)
    proc = resolve_path(cfg, "data_proc")
    net_csv = proc / "network_edges.csv"

    require_file(net_csv, "network_edges.csv from stage 01")
    assert_no_synthetic_provenance(proc)
    network_df = pd.read_csv(net_csv)
    LOG.info("Loaded real network (%d reaches)", len(network_df))

    export_nhdplus_network_csv(cfg)

    g = build_graph(network_df)
    order = compute_topological_order(g)

    reach_attrs = pd.DataFrame(
        [
            {
                "reach_id": n,
                "order_idx": i,
                "n_upstream": g.in_degree(n),
                "n_downstream": g.out_degree(n),
                **g.nodes[n],
            }
            for i, n in enumerate(order)
        ]
    )
    reach_attrs.to_csv(proc / "reach_attributes.csv", index=False)

    edges = [{"from_reach": u, "to_reach": v} for u, v in g.edges()]
    pd.DataFrame(edges).to_csv(proc / "network_adjacency.csv", index=False)

    LOG.info("Network order: %s ... %s", order[0], order[-1])
    LOG.info("Wrote reach_attributes.csv and network_adjacency.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build river network topology")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    main(args.config)
