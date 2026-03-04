"""Scenario management module for saving, loading, and comparing simulation scenarios.

This module provides functionality to save multiple simulation configurations
and compare their results side-by-side.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .models import SimulationConfig, SimulationResults
from .engine import calculate_scenarios


@dataclass
class SavedScenario:
    """A saved scenario with name, configuration, and results.
    
    Parameters
    ----------
    name : str
        Display name for the scenario.
    config : SimulationConfig
        The simulation configuration.
    results : SimulationResults
        The simulation results.
    created_at : str
        Timestamp when the scenario was saved.
    """
    name: str
    config: SimulationConfig
    results: SimulationResults
    created_at: str


class ScenarioManager:
    """Manages saved scenarios for comparison.
    
    This class handles saving, loading, deleting, and comparing scenarios.
    It's designed to work with Streamlit's session_state for persistence
    across user interactions.
    
    Parameters
    ----------
    max_scenarios : int
        Maximum number of scenarios to store. Default is 5.
    
    Attributes
    ----------
    max_scenarios : int
        Maximum number of scenarios allowed.
    scenarios : List[SavedScenario]
        List of saved scenarios.
    """
    
    def __init__(self, max_scenarios: int = 5):
        self.max_scenarios = max_scenarios
        self.scenarios: List[SavedScenario] = []
    
    def add_scenario(self, name: str, config: SimulationConfig, results: SimulationResults, created_at: str) -> bool:
        """Add a new scenario.
        
        Parameters
        ----------
        name : str
            Display name for the scenario.
        config : SimulationConfig
            The simulation configuration.
        results : SimulationResults
            The simulation results.
        created_at : str
            Timestamp when the scenario was saved.
            
        Returns
        -------
        bool
            True if added successfully, False if at capacity.
        """
        if len(self.scenarios) >= self.max_scenarios:
            return False
        
        # Check for duplicate names and append number if needed
        base_name = name
        counter = 1
        existing_names = {s.name for s in self.scenarios}
        while name in existing_names:
            name = f"{base_name} ({counter})"
            counter += 1
        
        scenario = SavedScenario(name, config, results, created_at)
        self.scenarios.append(scenario)
        return True
    
    def remove_scenario(self, name: str) -> bool:
        """Remove a scenario by name.
        
        Parameters
        ----------
        name : str
            Name of the scenario to remove.
            
        Returns
        -------
        bool
            True if removed successfully, False if not found.
        """
        for i, scenario in enumerate(self.scenarios):
            if scenario.name == name:
                self.scenarios.pop(i)
                return True
        return False
    
    def get_scenario(self, name: str) -> Optional[SavedScenario]:
        """Get a scenario by name.
        
        Parameters
        ----------
        name : str
            Name of the scenario to retrieve.
            
        Returns
        -------
        SavedScenario | None
            The scenario if found, None otherwise.
        """
        for scenario in self.scenarios:
            if scenario.name == name:
                return scenario
        return None
    
    def clear_all(self):
        """Remove all saved scenarios."""
        self.scenarios = []
    
    def is_full(self) -> bool:
        """Check if the scenario storage is at capacity."""
        return len(self.scenarios) >= self.max_scenarios
    
    def get_comparison_data(self) -> pd.DataFrame:
        """Generate comparison data for all saved scenarios.
        
        Returns
        -------
        pd.DataFrame
            DataFrame with comparison metrics for all scenarios.
        """
        if not self.scenarios:
            return pd.DataFrame()
        
        data = []
        for s in self.scenarios:
            row = {
                "Scenario Name": s.name,
                "Duration (Years)": s.config.duration_years,
                "Property Price ($)": s.config.property_price,
                "Down Payment (%)": s.config.down_payment_pct,
                "Mortgage Rate (%)": s.config.mortgage_rate_annual,
                "Property Appreciation (%)": s.config.property_appreciation_annual,
                "Equity Growth (%)": s.config.equity_growth_annual,
                "Monthly Rent ($)": s.config.monthly_rent,
                "Rent Inflation (%)": s.config.rent_inflation_rate * 100,
                "Final Net Value - Buy ($)": s.results.final_net_buy,
                "Final Net Value - Rent ($)": s.results.final_net_rent,
                "Difference - Buy vs Rent ($)": s.results.final_difference,
                "Breakeven - Buy vs Rent (Years)": s.results.breakeven_year,
                "Monthly Mortgage Payment ($)": s.results.monthly_mortgage_payment,
            }
            
            if s.results.scenario_c_enabled:
                row["Final Net Value - Rent+Savings ($)"] = s.results.final_net_rent_savings
                diff_a_vs_c = s.results.final_net_buy - (s.results.final_net_rent_savings or 0)
                row["Difference - Buy vs Rent+Savings ($)"] = diff_a_vs_c
                row["Breakeven - Buy vs Rent+Savings (Years)"] = s.results.breakeven_year_vs_rent_savings
            else:
                row["Final Net Value - Rent+Savings ($)"] = None
                row["Difference - Buy vs Rent+Savings ($)"] = None
                row["Breakeven - Buy vs Rent+Savings (Years)"] = None
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert scenarios to a list of dictionaries for serialization.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of scenario dictionaries.
        """
        result = []
        for s in self.scenarios:
            result.append({
                "name": s.name,
                "config": {
                    "duration_years": s.config.duration_years,
                    "property_price": s.config.property_price,
                    "down_payment_pct": s.config.down_payment_pct,
                    "mortgage_rate_annual": s.config.mortgage_rate_annual,
                    "property_appreciation_annual": s.config.property_appreciation_annual,
                    "equity_growth_annual": s.config.equity_growth_annual,
                    "monthly_rent": s.config.monthly_rent,
                    "rent_inflation_rate": s.config.rent_inflation_rate,
                },
                "created_at": s.created_at,
            })
        return result
    
    @classmethod
    def from_dict_list(cls, data: List[Dict[str, Any]], max_scenarios: int = 5) -> "ScenarioManager":
        """Create a ScenarioManager from a list of dictionaries.
        
        Parameters
        ----------
        data : List[Dict[str, Any]]
            List of scenario dictionaries.
        max_scenarios : int
            Maximum number of scenarios. Default is 5.
            
        Returns
        -------
        ScenarioManager
            A new ScenarioManager with loaded scenarios.
        """
        manager = cls(max_scenarios=max_scenarios)
        for item in data:
            try:
                config = SimulationConfig(**item["config"])
                results = calculate_scenarios(config)
                manager.add_scenario(item["name"], config, results, item["created_at"])
            except Exception:
                # Skip invalid scenarios
                continue
        return manager


def create_comparison_table(scenarios: List[SavedScenario]) -> pd.DataFrame:
    """Create a formatted comparison table for display.
    
    Parameters
    ----------
    scenarios : List[SavedScenario]
        List of scenarios to compare.
        
    Returns
    -------
    pd.DataFrame
        Formatted comparison table.
    """
    if not scenarios:
        return pd.DataFrame()
    
    manager = ScenarioManager()
    manager.scenarios = scenarios
    df = manager.get_comparison_data()
    
    # Select key columns for display
    display_cols = [
        "Scenario Name",
        "Final Net Value - Buy ($)",
        "Final Net Value - Rent ($)",
        "Difference - Buy vs Rent ($)",
        "Breakeven - Buy vs Rent (Years)",
    ]
    
    # Check if any scenario has Scenario C enabled
    has_scenario_c = any(s.results.scenario_c_enabled for s in scenarios)
    if has_scenario_c:
        display_cols.extend([
            "Final Net Value - Rent+Savings ($)",
            "Difference - Buy vs Rent+Savings ($)",
        ])
    
    return df[display_cols]


def create_comparison_chart(scenarios: List[SavedScenario], metric: str = "net_value") -> go.Figure:
    """Create a comparison chart for saved scenarios.
    
    Parameters
    ----------
    scenarios : List[SavedScenario]
        List of scenarios to compare.
    metric : str
        Metric to compare: "net_value", "final_values", or "breakeven".
        
    Returns
    -------
    go.Figure
        Plotly figure with comparison visualization.
    """
    if not scenarios:
        fig = go.Figure()
        fig.update_layout(title="No scenarios to compare")
        return fig
    
    if metric == "final_values":
        return _create_final_values_chart(scenarios)
    elif metric == "breakeven":
        return _create_breakeven_chart(scenarios)
    else:  # net_value
        return _create_net_value_comparison_chart(scenarios)


def _create_final_values_chart(scenarios: List[SavedScenario]) -> go.Figure:
    """Create a bar chart comparing final values."""
    fig = go.Figure()
    
    names = [s.name for s in scenarios]
    buy_values = [s.results.final_net_buy for s in scenarios]
    rent_values = [s.results.final_net_rent for s in scenarios]
    
    fig.add_trace(go.Bar(
        name="Buy (Scenario A)",
        x=names,
        y=buy_values,
        marker_color="#2ecc71",
        text=[f"${v:,.0f}" for v in buy_values],
        textposition="outside",
    ))
    
    fig.add_trace(go.Bar(
        name="Rent + Invest (Scenario B)",
        x=names,
        y=rent_values,
        marker_color="#3498db",
        text=[f"${v:,.0f}" for v in rent_values],
        textposition="outside",
    ))
    
    # Add Scenario C if any scenario has it enabled
    savings_values = []
    has_c = False
    for s in scenarios:
        if s.results.scenario_c_enabled and s.results.final_net_rent_savings is not None:
            savings_values.append(s.results.final_net_rent_savings)
            has_c = True
        else:
            savings_values.append(0)
    
    if has_c:
        fig.add_trace(go.Bar(
            name="Rent + Savings (Scenario C)",
            x=names,
            y=savings_values,
            marker_color="#9b59b6",
            text=[f"${v:,.0f}" if v > 0 else "" for v in savings_values],
            textposition="outside",
        ))
    
    fig.update_layout(
        title="Final Net Values Comparison",
        xaxis_title="Scenario",
        yaxis_title="Final Net Value ($)",
        barmode="group",
        template="plotly_white",
        height=500,
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig


def _create_breakeven_chart(scenarios: List[SavedScenario]) -> go.Figure:
    """Create a chart showing breakeven points."""
    fig = go.Figure()
    
    names = []
    breakeven_a_b = []
    breakeven_a_c = []
    
    for s in scenarios:
        names.append(s.name)
        breakeven_a_b.append(s.results.breakeven_year if s.results.breakeven_year else None)
        breakeven_a_c.append(s.results.breakeven_year_vs_rent_savings if s.results.breakeven_year_vs_rent_savings else None)
    
    fig.add_trace(go.Bar(
        name="Breakeven: Buy vs Rent (A vs B)",
        x=names,
        y=breakeven_a_b,
        marker_color="#f39c12",
        text=[f"{v:.1f}y" if v else "N/A" for v in breakeven_a_b],
        textposition="outside",
    ))
    
    # Only add A vs C if any scenario has it
    if any(v is not None for v in breakeven_a_c):
        fig.add_trace(go.Bar(
            name="Breakeven: Buy vs Rent+Savings (A vs C)",
            x=names,
            y=[v if v else 0 for v in breakeven_a_c],
            marker_color="#e74c3c",
            text=[f"{v:.1f}y" if v else "N/A" for v in breakeven_a_c],
            textposition="outside",
        ))
    
    fig.update_layout(
        title="Breakeven Points Comparison",
        xaxis_title="Scenario",
        yaxis_title="Years to Breakeven",
        barmode="group",
        template="plotly_white",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig


def _create_net_value_comparison_chart(scenarios: List[SavedScenario]) -> go.Figure:
    """Create a line chart comparing net value trajectories."""
    fig = go.Figure()
    
    colors_buy = ["#27ae60", "#2ecc71", "#58d68d", "#82e0aa", "#abebc6"]
    colors_rent = ["#2980b9", "#3498db", "#5dade2", "#85c1e9", "#aed6f1"]
    
    for i, s in enumerate(scenarios):
        color_buy = colors_buy[i % len(colors_buy)]
        color_rent = colors_rent[i % len(colors_rent)]
        
        # Buy trajectory
        fig.add_trace(go.Scatter(
            x=s.results.data["Year"],
            y=s.results.data["Net_Buy"],
            name=f"{s.name} - Buy",
            line=dict(color=color_buy, width=2),
            mode="lines",
            hovertemplate="%{fullData.name}: $%{y:,.0f}<extra></extra>",
        ))
        
        # Rent trajectory
        fig.add_trace(go.Scatter(
            x=s.results.data["Year"],
            y=s.results.data["Net_Rent"],
            name=f"{s.name} - Rent",
            line=dict(color=color_rent, width=2, dash="dash"),
            mode="lines",
            hovertemplate="%{fullData.name}: $%{y:,.0f}<extra></extra>",
        ))
    
    fig.update_layout(
        title="Net Value Trajectories Comparison",
        xaxis_title="Years",
        yaxis_title="Net Value ($)",
        template="plotly_white",
        height=600,
        hovermode="x unified",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig


def export_comparison_csv(scenarios: List[SavedScenario]) -> str:
    """Export comparison data as CSV string.
    
    Parameters
    ----------
    scenarios : List[SavedScenario]
        List of scenarios to export.
        
    Returns
    -------
    str
        CSV formatted string.
    """
    if not scenarios:
        return ""
    
    manager = ScenarioManager()
    manager.scenarios = scenarios
    df = manager.get_comparison_data()
    return df.to_csv(index=False)
