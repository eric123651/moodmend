"""
Log management route module
Provides functions for getting, updating, deleting logs"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import request, jsonify, Blueprint
from backend.models import get_db, init_db, db_lock

# Create log management blueprint
log_bp = Blueprint('log', __name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('log_routes')

# Ensure data directory exists
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
os.makedirs(data_dir, exist_ok=True)

@log_bp.route('/api/get-logs', methods=['GET'])
def get_logs():
    """
    Get user's emotion logs list
    Supports filtering by date range and emotion type
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id')
        email = request.args.get('email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        emotion_type = request.args.get('emotion_type')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit

        # Validate required parameters
        if not user_id and not email:
            return jsonify({'error': 'Missing user_id or email parameter'}), 400

        # Initialize database
        init_db()
        db = get_db()

        # Build SQL query
        query = "SELECT id, user_id, content, emotion, confidence, suggestion, created_at, updated_at FROM emotion_logs WHERE "
        params = []

        if user_id:
            query += "user_id = ? AND "
            params.append(user_id)
        elif email:
            # Get user_id from email
            with db_lock:
                cursor = db.cursor()
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                user_id = user[0]
                query += "user_id = ? AND "
                params.append(user_id)

        # Add date range filter
        if start_date:
            query += "created_at >= ? AND "
            params.append(start_date)
        if end_date:
            query += "created_at <= ? AND "
            params.append(end_date)
        if emotion_type:
            query += "emotion = ? AND "
            params.append(emotion_type)

        # Remove last 'AND' and add pagination
        query = query.rstrip('WHERE ').rstrip(' AND ')
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Execute query
        with db_lock:
            cursor = db.cursor()
            cursor.execute(query, params)
            logs = cursor.fetchall()

            # Get total count for pagination
            count_query = "SELECT COUNT(*) FROM emotion_logs WHERE "
            if user_id:
                count_query += "user_id = ?"
                count_params = [user_id]
            else:
                count_query += "user_id = ?"
                count_params = [user_id]
            
            # Add other filters for count
            temp_query = count_query
            if start_date:
                temp_query += " AND created_at >= ?"
                count_params.append(start_date)
            if end_date:
                temp_query += " AND created_at <= ?"
                count_params.append(end_date)
            if emotion_type:
                temp_query += " AND emotion = ?"
                count_params.append(emotion_type)
            
            cursor.execute(temp_query, count_params)
            total = cursor.fetchone()[0]

        # Format results
        log_list = []
        for log in logs:
            log_list.append({
                'id': log[0],
                'user_id': log[1],
                'content': log[2],
                'emotion': log[3],
                'confidence': log[4],
                'suggestion': log[5],
                'created_at': log[6],
                'updated_at': log[7]
            })

        return jsonify({
            'logs': log_list,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Get logs failed: {str(e)}")
        return jsonify({'error': 'Failed to get logs, please try again later'}), 500

@log_bp.route('/api/get-log/<log_id>', methods=['GET'])
def get_log(log_id):
    """
    Get single log detail
    """
    try:
        # Initialize database
        init_db()
        db = get_db()

        # Get log
        with db_lock:
            cursor = db.cursor()
            cursor.execute(
                'SELECT id, user_id, content, emotion, confidence, suggestion, created_at, updated_at FROM emotion_logs WHERE id = ?',
                (log_id,)
            )
            log = cursor.fetchone()

        if not log:
            return jsonify({'error': 'Log not found'}), 404

        # Format result
        log_detail = {
            'id': log[0],
            'user_id': log[1],
            'content': log[2],
            'emotion': log[3],
            'confidence': log[4],
            'suggestion': log[5],
            'created_at': log[6],
            'updated_at': log[7]
        }

        return jsonify(log_detail), 200

    except Exception as e:
        logger.error(f"Get log failed: {str(e)}")
        return jsonify({'error': 'Failed to get log, please try again later'}), 500

@log_bp.route('/api/update-log/<log_id>', methods=['PUT'])
def update_log(log_id):
    """
    Update log (mainly for adding feedback)
    """
    try:
        # Parse request data
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        user_id = data.get('user_id')
        email = data.get('email')
        feedback = data.get('feedback')
        rating = data.get('rating')  # Optional: rating 1-5

        # Validate required parameters
        if not user_id and not email:
            return jsonify({'error': 'Missing user_id or email parameter'}), 400
        if not feedback and rating is None:
            return jsonify({'error': 'No data to update'}), 400

        # Initialize database
        init_db()
        db = get_db()

        # Verify ownership
        with db_lock:
            cursor = db.cursor()
            # Get log owner
            cursor.execute('SELECT user_id FROM emotion_logs WHERE id = ?', (log_id,))
            log = cursor.fetchone()
            if not log:
                return jsonify({'error': 'Log not found'}), 404
            log_user_id = log[0]

            # Check if user has permission
            if user_id:
                if str(user_id) != str(log_user_id):
                    return jsonify({'error': 'Permission denied'}), 403
            elif email:
                # Get user_id from email
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                if not user or str(user[0]) != str(log_user_id):
                    return jsonify({'error': 'Permission denied'}), 403

        # Update log
        update_fields = []
        update_params = []
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if feedback is not None:
            update_fields.append('feedback = ?')
            update_params.append(feedback)
        if rating is not None:
            # Validate rating
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({'error': 'Invalid rating, must be 1-5'}), 400
            update_fields.append('rating = ?')
            update_params.append(rating)

        update_fields.append('updated_at = ?')
        update_params.append(updated_at)
        update_params.append(log_id)

        with db_lock:
            cursor = db.cursor()
            query = f'UPDATE emotion_logs SET {" ".join(update_fields)} WHERE id = ?'
            cursor.execute(query, update_params)
            db.commit()

        return jsonify({
            'message': 'Log updated successfully',
            'updated_at': updated_at
        }), 200

    except Exception as e:
        logger.error(f"Update log failed: {str(e)}")
        return jsonify({'error': 'Failed to update log, please try again later'}), 500

@log_bp.route('/api/delete-log/<log_id>', methods=['DELETE'])
def delete_log(log_id):
    """
    Delete log
    """
    try:
        # Get parameters from request body or query string
        if request.is_json:
            data = request.json
            user_id = data.get('user_id')
            email = data.get('email')
        else:
            user_id = request.args.get('user_id')
            email = request.args.get('email')

        # Validate required parameters
        if not user_id and not email:
            return jsonify({'error': 'Missing user_id or email parameter'}), 400

        # Initialize database
        init_db()
        db = get_db()

        # Verify ownership
        with db_lock:
            cursor = db.cursor()
            # Get log owner
            cursor.execute('SELECT user_id FROM emotion_logs WHERE id = ?', (log_id,))
            log = cursor.fetchone()
            if not log:
                return jsonify({'error': 'Log not found'}), 404
            log_user_id = log[0]

            # Check if user has permission
            if user_id:
                if str(user_id) != str(log_user_id):
                    return jsonify({'error': 'Permission denied'}), 403
            elif email:
                # Get user_id from email
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                if not user or str(user[0]) != str(log_user_id):
                    return jsonify({'error': 'Permission denied'}), 403

            # Delete log
            cursor.execute('DELETE FROM emotion_logs WHERE id = ?', (log_id,))
            db.commit()

        return jsonify({
            'message': 'Log deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Delete log failed: {str(e)}")
        return jsonify({'error': 'Failed to delete log, please try again later'}), 500

@log_bp.route('/api/emotion-stats', methods=['GET'])
def emotion_stats():
    """
    Get user emotion statistics data
    """
    try:
        # Get query parameters
        user_id = request.args.get('user_id')
        email = request.args.get('email')
        period = request.args.get('period', 'week')  # day, week, month, year

        # Validate required parameters
        if not user_id and not email:
            return jsonify({'error': 'Missing user_id or email parameter'}), 400

        # Initialize database
        init_db()
        db = get_db()

        # Get user_id if email is provided
        if email:
            with db_lock:
                cursor = db.cursor()
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                user_id = user[0]

        # Calculate date range based on period
        today = datetime.now()
        if period == 'day':
            start_date = today.strftime('%Y-%m-%d')
        elif period == 'week':
            # Get start of week (Monday)
            days_since_monday = today.weekday()
            start_date = (today.replace(hour=0, minute=0, second=0, microsecond=0) - \
                         timedelta(days=days_since_monday)).strftime('%Y-%m-%d')
        elif period == 'month':
            start_date = today.strftime('%Y-%m-01')
        elif period == 'year':
            start_date = today.strftime('%Y-01-01')
        else:
            return jsonify({'error': 'Invalid period, must be day, week, month or year'}), 400

        # Get emotion statistics
        with db_lock:
            cursor = db.cursor()
            # Get emotion counts
            cursor.execute(
                'SELECT emotion, COUNT(*) as count FROM emotion_logs WHERE user_id = ? AND created_at >= ? GROUP BY emotion',
                (user_id, start_date)
            )
            emotion_counts = cursor.fetchall()

            # Get total logs
            cursor.execute(
                'SELECT COUNT(*) FROM emotion_logs WHERE user_id = ? AND created_at >= ?',
                (user_id, start_date)
            )
            total_logs = cursor.fetchone()[0]

            # Get average confidence
            cursor.execute(
                'SELECT AVG(confidence) FROM emotion_logs WHERE user_id = ? AND created_at >= ?',
                (user_id, start_date)
            )
            avg_confidence = cursor.fetchone()[0] or 0

        # Format emotion counts as dictionary
        emotion_stats = {}
        for emotion, count in emotion_counts:
            emotion_stats[emotion] = count

        # Add emotions with zero count
        all_emotions = ['happy', 'sad', 'angry', 'fear', 'surprise', 'disgust', 'neutral']
        for emotion in all_emotions:
            if emotion not in emotion_stats:
                emotion_stats[emotion] = 0

        return jsonify({
            'period': period,
            'start_date': start_date,
            'end_date': today.strftime('%Y-%m-%d'),
            'total_logs': total_logs,
            'average_confidence': float(avg_confidence),
            'emotion_distribution': emotion_stats,
            'summary': {
                'most_common_emotion': max(emotion_stats, key=emotion_stats.get) if total_logs > 0 else 'neutral',
                'emotion_diversity': len([e for e, c in emotion_stats.items() if c > 0])
            }
        }), 200

    except Exception as e:
        logger.error(f"Get emotion stats failed: {str(e)}")
        return jsonify({'error': 'Failed to get emotion statistics, please try again later'}), 500

logger.info("Log management routes registered successfully")