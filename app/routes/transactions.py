"""
Transaction routes blueprint.

This module defines the routes for managing transactions,
including viewing, adding, editing, and deleting transactions.
"""

import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash, current_app, send_file
from flask_login import login_required, current_user
from app.models import Transaction, Account, TransactionCategory
from app.extensions import db
from app.services.transaction_service import (
    get_transactions_by_date_range, get_transaction_stats,
    get_transaction_by_id, add_manual_transaction,
    update_transaction, delete_transaction, categorize_transactions
)

# Create the blueprint
transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')


@transactions_bp.route('/')
@login_required
def index():
    """Transaction list page with filtering and pagination."""
    # Parse filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Date range
    date_range = request.args.get('date_range', '30')
    
    if date_range == 'custom':
        # Custom date range
        try:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            # Default to last 30 days if custom dates are invalid
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            date_range = '30'
    else:
        # Predefined date range
        try:
            days = int(date_range)
        except ValueError:
            days = 30
            
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
    
    # Other filters
    category_id = request.args.get('category_id', type=int)
    account_id = request.args.get('account_id', type=int)
    search = request.args.get('search', '')
    tx_type = request.args.get('type', '')
    
    # Prepare amount filter based on transaction type
    min_amount = None
    max_amount = None
    is_extra = None
    
    if tx_type == 'expense':
        max_amount = 0  # Only expenses (negative amounts)
    elif tx_type == 'income':
        min_amount = 0  # Only income (positive amounts)
    elif tx_type == 'extra':
        is_extra = True  # Only extras
    
    # Get filtered transactions with pagination
    result = get_transactions_by_date_range(
        current_user.id, start_date, end_date,
        category_id=category_id, 
        account_id=account_id,
        min_amount=min_amount,
        max_amount=max_amount,
        is_extra=is_extra,
        keywords=search,
        page=page,
        per_page=per_page
    )
    
    # Get transaction statistics
    stats = get_transaction_stats(current_user.id, start_date, end_date)
    
    # Get categories and accounts for filter dropdowns
    categories = TransactionCategory.query.filter_by(user_id=current_user.id).order_by(TransactionCategory.name).all()
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.name).all()
    
    # Build pagination data
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': result['total'],
        'pages': result['pages'],
        'has_next': result['has_next'],
        'has_prev': result['has_prev']
    }
    
    # Filter arguments for pagination links
    filter_args = {}
    if date_range:
        filter_args['date_range'] = date_range
    if date_range == 'custom':
        filter_args['start_date'] = start_date.strftime('%Y-%m-%d')
        filter_args['end_date'] = end_date.strftime('%Y-%m-%d')
    if category_id:
        filter_args['category_id'] = category_id
    if account_id:
        filter_args['account_id'] = account_id
    if search:
        filter_args['search'] = search
    if tx_type:
        filter_args['type'] = tx_type
    
    # Render the template
    return render_template(
        'transactions/index.html',
        transactions=result['transactions'],
        pagination=pagination,
        filter_args=filter_args,
        categories=categories,
        accounts=accounts,
        stats=stats,
        days=int(date_range) if date_range.isdigit() else None,
        date_range=date_range,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        category_id=category_id,
        account_id=account_id,
        search=search,
        type=tx_type,
        today=datetime.now().strftime('%Y-%m-%d')
    )


@transactions_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new transaction."""
    try:
        # Parse form data
        date_str = request.form.get('date')
        description = request.form.get('description')
        amount = request.form.get('amount')
        account_id = request.form.get('account_id')
        category_id = request.form.get('category_id') or None
        is_extra = 'is_extra' in request.form
        notes = request.form.get('notes')
        
        # Validate required fields
        if not date_str or not description or not amount or not account_id:
            flash('Missing required fields', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Parse amount
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Create the transaction
        transaction = add_manual_transaction(
            current_user.id,
            date,
            amount,
            description,
            account_id=int(account_id),
            category_id=int(category_id) if category_id else None,
            is_extra=is_extra,
            notes=notes
        )
        
        flash('Transaction added successfully', 'success')
        return redirect(url_for('transactions.index'))
    except Exception as e:
        current_app.logger.error(f"Error adding transaction: {str(e)}")
        flash(f'Error adding transaction: {str(e)}', 'danger')
        return redirect(url_for('transactions.index'))


@transactions_bp.route('/edit/<int:transaction_id>', methods=['POST'])
@login_required
def edit(transaction_id):
    """Edit an existing transaction."""
    try:
        # Parse form data
        date_str = request.form.get('date')
        description = request.form.get('description')
        amount = request.form.get('amount')
        account_id = request.form.get('account_id')
        category_id = request.form.get('category_id') or None
        is_extra = 'is_extra' in request.form
        notes = request.form.get('notes')
        
        # Validate required fields
        if not date_str or not description or not amount or not account_id:
            flash('Missing required fields', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Parse amount
        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount', 'danger')
            return redirect(url_for('transactions.index'))
        
        # Update the transaction
        transaction = update_transaction(
            transaction_id,
            current_user.id,
            date=date,
            amount=amount,
            description=description,
            account_id=int(account_id),
            category_id=int(category_id) if category_id else None,
            is_extra=is_extra,
            notes=notes
        )
        
        if transaction:
            flash('Transaction updated successfully', 'success')
        else:
            flash('Transaction not found', 'danger')
            
        return redirect(url_for('transactions.index'))
    except Exception as e:
        current_app.logger.error(f"Error updating transaction: {str(e)}")
        flash(f'Error updating transaction: {str(e)}', 'danger')
        return redirect(url_for('transactions.index'))


@transactions_bp.route('/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete(transaction_id):
    """Delete a transaction."""
    try:
        # Delete the transaction
        success = delete_transaction(transaction_id, current_user.id)
        
        if success:
            flash('Transaction deleted successfully', 'success')
        else:
            flash('Transaction not found', 'danger')
            
        return redirect(url_for('transactions.index'))
    except Exception as e:
        current_app.logger.error(f"Error deleting transaction: {str(e)}")
        flash(f'Error deleting transaction: {str(e)}', 'danger')
        return redirect(url_for('transactions.index'))


@transactions_bp.route('/auto-categorize', methods=['POST'])
@login_required
def auto_categorize():
    """Auto-categorize uncategorized transactions."""
    try:
        count = categorize_transactions(current_user.id, True)
        flash(f'Successfully categorized {count} transactions', 'success')
    except Exception as e:
        current_app.logger.error(f"Error auto-categorizing transactions: {str(e)}")
        flash(f'Error auto-categorizing transactions: {str(e)}', 'danger')
        
    return redirect(url_for('transactions.index'))


@transactions_bp.route('/export-csv')
@login_required
def export_csv():
    """Export transactions as CSV."""
    try:
        # Parse filter parameters (same as index)
        date_range = request.args.get('date_range', '30')
        
        if date_range == 'custom':
            try:
                start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
        else:
            try:
                days = int(date_range)
            except ValueError:
                days = 30
                
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
        
        # Other filters
        category_id = request.args.get('category_id', type=int)
        account_id = request.args.get('account_id', type=int)
        search = request.args.get('search', '')
        tx_type = request.args.get('type', '')
        
        # Prepare amount filter based on transaction type
        min_amount = None
        max_amount = None
        is_extra = None
        
        if tx_type == 'expense':
            max_amount = 0
        elif tx_type == 'income':
            min_amount = 0
        elif tx_type == 'extra':
            is_extra = True
        
        # Get filtered transactions (no pagination for export)
        result = get_transactions_by_date_range(
            current_user.id, start_date, end_date,
            category_id=category_id, 
            account_id=account_id,
            min_amount=min_amount,
            max_amount=max_amount,
            is_extra=is_extra,
            keywords=search,
            page=1,
            per_page=1000000  # Large number to get all transactions
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date', 'Description', 'Amount', 'Category', 
            'Account', 'Is Extra', 'Notes', 'Source'
        ])
        
        # Write transactions
        for tx in result['transactions']:
            category_name = tx.category.name if tx.category else 'Uncategorized'
            account_name = tx.account.name if tx.account else 'Unknown'
            
            writer.writerow([
                tx.date.strftime('%Y-%m-%d'),
                tx.description,
                float(tx.amount),
                category_name,
                account_name,
                'Yes' if tx.is_extra else 'No',
                tx.notes or '',
                tx.source.value
            ])
        
        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'transactions_export_{timestamp}.csv'
        )
    except Exception as e:
        current_app.logger.error(f"Error exporting transactions: {str(e)}")
        flash(f'Error exporting transactions: {str(e)}', 'danger')
        return redirect(url_for('transactions.index'))


@transactions_bp.route('/api/<int:transaction_id>')
@login_required
def api_transaction_detail(transaction_id):
    """API endpoint for transaction details."""
    transaction = get_transaction_by_id(transaction_id, current_user.id)
    
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404
    
    # Format the response
    result = {
        "id": transaction.id,
        "date": transaction.date.strftime('%Y-%m-%d'),
        "description": transaction.description,
        "amount": float(transaction.amount),
        "is_extra": transaction.is_extra,
        "category_id": transaction.category_id,
        "account_id": transaction.account_id,
        "notes": transaction.notes,
        "source": transaction.source.value,
        "created_at": transaction.created_at.isoformat(),
        "updated_at": transaction.updated_at.isoformat()
    }
    
    return jsonify(result)