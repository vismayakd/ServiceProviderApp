from django.urls import path
from . import views


urlpatterns = [
   
    path('',views.home,name='home'),
   
    path('login/',views.user_login,name='login'),
    path('logout/',views.user_logout,name='logout'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
   
    path('add_customer/',views.customer_register,name='add_customer'),
    path('customer_dashboard/',views.customer_dashboard,name='customer_dashboard'),
    path('company_services/<int:id>',views.cust_view_services,name='cust_view_services'),
    path('request_service/<int:service_id>/', views.request_service, name='request_service'),
    path('my_requests/',views.cust_view_requests,name='my_requests'),
    path('invoice/<int:request_id>',views.invoice_view,name='invoice'),
    path('pay/<int:request_id>/', views.payment_proceed, name='payment_proceed'),
    path('feedback/<int:request_id>/', views.feedback_view, name='feedback_view'),

    path('add_company/',views.company_form,name='add_company'),
    path('company_dashboard/',views.company_dashboard,name='company_dashboard'),
    path('service_view/', views.service_view, name='service_view'),
    path('add_service/', views.add_service, name='add_service'),
    path('edit_service/<int:pk>/', views.edit_service, name='edit_service'),
    path('delete_service/<int:pk>/', views.delete_service, name='delete_service'),
    path('technician_list/',views.technician_list,name='technician_list'),
    path('add_technician/',views.technician_add,name='add_technician'),
    path('technician_edit/<int:tech_id>/', views.technician_edit, name='technician_edit'),
    path('technician_delete/<int:tech_id>/', views.technician_delete, name='technician_delete'),
    path("assign_technician/<int:request_id>/", views.assign_technician, name="assign_technician"),
    path("mark_payment_pending/<int:pk>/", views.mark_payment_pending, name="mark_payment_pending"),


    path('technician_dashboard/',views.technician_dashboard,name='technician_dashboard'),
    path('update_req_status/<int:request_id>/<str:status>/', views.update_request_status, name='update_request_status'),
    path('complete_service/<int:request_id>/', views.complete_service, name='complete_service'),


]