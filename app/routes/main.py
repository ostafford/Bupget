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
    return render_template('main/index.html')


@main_bp.route('/about')
def about():
    """About page route."""
    return render_template('main/about.html')
