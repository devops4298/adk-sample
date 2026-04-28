"""
ADK Master Example Package
===========================

A comprehensive example demonstrating all Google ADK features.

Usage:
    from adk_master_example import app, root_agent
    
    # Or run directly
    python run.py
"""

from .agent import app, root_agent, config

__all__ = ["app", "root_agent", "config"]
