from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r'^\d{10}$', 
    message="Enter a valid 10-digit phone number."
)

class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('company', 'Company'),
        ('technician', 'Technician'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    cust_name = models.CharField(max_length=100)
    phone =models.CharField(
        validators=[phone_validator], max_length=10, unique=True)
    address = models.TextField()

    def __str__(self):
        return self.user.username


class CompanyProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_profile')
    company_name = models.CharField(max_length=100)
    phone = models.CharField(
        validators=[phone_validator], max_length=10, unique=True)
    address = models.TextField()
    logo = models.ImageField(upload_to='company_logo/', blank=True, null=True)

    def __str__(self):
        return self.company_name
    
class ServiceType(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    image = models.ImageField(upload_to='service_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.company.company_name})"
    
class TechnicianProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='technician_profile')
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='company_technicians')
    name = models.CharField(max_length=100)
    phone = models.CharField(
        validators=[phone_validator], max_length=10, unique=True)
    service_types = models.ManyToManyField(ServiceType, related_name='service_technicians')
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.user.username} ({self.company.company_name})"
    
class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('Proceeding', 'Proceeding'),
        ('completed', 'Completed'),
        ('payment_pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='customer_requests')
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='company_requests')
    technician = models.ForeignKey(TechnicianProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='technician_requests')
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='service_requests')
    title = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    extra_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True, blank=True)
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    feedback = models.TextField(null=True, blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.cust_name} -{self.service_type.name} - {self.company.company_name}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"