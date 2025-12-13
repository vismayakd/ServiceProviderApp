from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification
from django.contrib.auth import get_user_model
# from django.shortcuts import get_object_or_404

@shared_task
def send_custom_email(subject, message, email):
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=True
        )
        return "Email sent"
    except Exception as e:
        return f"Error: {str(e)}"
@shared_task  
def create_notification(user_id, message):
    User = get_user_model()
    user = User.objects.get(id=user_id)
    Notification.objects.create(user=user, message=message)