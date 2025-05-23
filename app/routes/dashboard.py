"""
Dashboard routes blueprint.

This module defines the dashboard routes for the application,
which provide the main interface for authenticated users.
"""

from flask import Blueprint, render_template
from flask_login import login_required

# Create the blueprint
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home page route."""
    return render_template('dashboard/index.html')


@dashboard_bp.route('/overview')
@login_required
def overview():
    """Financial overview route."""
    return render_template('dashboard/overview.html')
