from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, CustomerProfile, CompanyProfile, TechnicianProfile, ServiceType, ServiceRequest,Notification

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role',)
    search_fields = ('username', 'email')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(CustomerProfile)
admin.site.register(CompanyProfile)
admin.site.register(TechnicianProfile)
admin.site.register(ServiceType)
admin.site.register(ServiceRequest)
admin.site.register(Notification)