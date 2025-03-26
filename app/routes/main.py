"""
Main routes blueprint.

This module defines the main routes for the application, including
the home page and other non-authenticated pages.
"""

from flask import Blueprint, render_template, redirect, url_for

# Create the blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page route."""
    return "Welcome to the Budget App! This is the home page."


@main_bp.route('/about')
def about():
    """About page route."""
    return "This is the Budget App, a tool for tracking and forecasting finances."
