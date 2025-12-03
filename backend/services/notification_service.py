from datetime import datetime, timedelta
from models.user import User
from models.user_interaction import UserInteraction
from routes.notifications import create_system_notification
import logging

def check_user_inactivity():
    """Check for inactive users and send reminder notifications"""
    try:
        users = User.objects()
        now = datetime.utcnow()
        
        for user in users:
            # Get user's last activity
            last_interaction = UserInteraction.objects(user=user).order_by('-timestamp').first()
            
            if not last_interaction:
                # New user - send welcome reminder
                create_system_notification(
                    user=user,
                    title='Start Your Learning Journey! 🚀',
                    message='Explore our recommended courses to begin learning.',
                    notification_type='reminder',
                    action_url='/dashboard'
                )
                continue
            
            days_inactive = (now - last_interaction.timestamp).days
            
            # Send notifications based on inactivity period
            if days_inactive == 2:
                create_system_notification(
                    user=user,
                    title='Missing You! 📚',
                    message="You haven't practiced in 2 days. Quick refresher?",
                    notification_type='reminder',
                    action_url='/dashboard'
                )
            elif days_inactive == 7:
                create_system_notification(
                    user=user,
                    title='Week Break - Time to Return! ⏰',
                    message="It's been a week! Let's get back to learning.",
                    notification_type='warning',
                    action_url='/recommendations'
                )
            elif days_inactive == 30:
                create_system_notification(
                    user=user,
                    title='We Miss You! 💙',
                    message="It's been a month. Here are some easy courses to restart.",
                    notification_type='info',
                    action_url='/dashboard'
                )
                
    except Exception as e:
        logging.error(f"Error checking user inactivity: {e}")

def check_incomplete_courses():
    """Send notifications for users with incomplete courses"""
    try:
        users = User.objects()
        
        for user in users:
            if not user.interactions:
                continue
                
            # Find in-progress courses
            in_progress = [
                resource_id for resource_id, interaction in user.interactions.items()
                if interaction.get('status') == 'in-progress'
            ]
            
            if len(in_progress) > 0:
                # Check if user hasn't interacted with in-progress courses recently
                recent_activity = UserInteraction.objects(
                    user=user,
                    timestamp__gte=datetime.utcnow() - timedelta(days=3)
                ).count()
                
                if recent_activity == 0:
                    create_system_notification(
                        user=user,
                        title='Continue Your Progress! 📈',
                        message=f'You have {len(in_progress)} courses in progress. Keep going!',
                        notification_type='reminder',
                        action_url='/profile'
                    )
                    
    except Exception as e:
        logging.error(f"Error checking incomplete courses: {e}")

def send_progress_reminders():
    """Send progress-based reminder notifications"""
    try:
        users = User.objects()
        
        for user in users:
            # Check learning streak
            recent_days = []
            for i in range(7):  # Check last 7 days
                day = datetime.utcnow() - timedelta(days=i)
                day_interactions = UserInteraction.objects(
                    user=user,
                    timestamp__gte=day.replace(hour=0, minute=0, second=0),
                    timestamp__lt=day.replace(hour=23, minute=59, second=59)
                ).count()
                recent_days.append(day_interactions > 0)
            
            # If user was active but stopped
            if recent_days[1] and not recent_days[0]:  # Active yesterday but not today
                create_system_notification(
                    user=user,
                    title='Keep Your Streak! 🔥',
                    message="Don't break your learning streak! Quick 5-minute session?",
                    notification_type='reminder',
                    action_url='/tasks'
                )
                
    except Exception as e:
        logging.error(f"Error sending progress reminders: {e}")