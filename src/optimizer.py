"""Allocation boundary for a future OR-Tools/PuLP multi-leg optimizer."""
from src.recommendations import best_vessel

def recommend_allocation(vessel_options):
    return best_vessel(vessel_options)
