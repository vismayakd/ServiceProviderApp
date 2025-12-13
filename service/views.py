from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth import login,authenticate,logout
from .forms import (CompanyRegistrationForm,CustomerRegistrationForm,
                    CustomerProfileForm,CompanyProfileForm,ServiceTypeForm,
                    ServiceRequestForm,TechnicianForm,TechnicianSelfEditForm)
from . models import CompanyProfile,ServiceRequest,TechnicianProfile,CustomerProfile, ServiceType,Notification
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .tasks import send_custom_email,create_notification
from django.core.paginator import Paginator
from decimal import Decimal
import random
import string
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Q, F, Count

User = get_user_model()
def generate_username(email, company_name):
    email_prefix = email.split('@')[0]
    random_number = random.randint(100, 999)
    return f"{company_name[:3].lower()}_{email_prefix}_{random_number}"

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def home(request):
    return render(request,'home.html')

def company_form(request):
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'company'
            user.save()

            CompanyProfile.objects.create(
                user=user,
                company_name=form.cleaned_data['company_name'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                logo=form.cleaned_data.get('logo')
            )
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('login')
    else:
        form = CompanyRegistrationForm()
    return render(request,'registration_form.html',
        context={'form':form,'title':'company'})

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.role == 'company':
                return redirect('company_dashboard')
            elif user.role == 'customer':
                return redirect('customer_dashboard')
            elif user.role == 'technician':
                return redirect('technician_dashboard')
            else:
                messages.error(request, "Invalid User!")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('home')


@login_required
def profile_edit(request):
    user = request.user
    old_username = user.username
    old_password = user.password
    role_templates = {
        'customer': ('customer_profile.html', CustomerProfile, CustomerProfileForm, 'customer_dashboard'),
        'company': ('company_profile.html', CompanyProfile, CompanyProfileForm, 'company_dashboard'),
        'technician': ('technician_profile.html', TechnicianProfile, TechnicianSelfEditForm, 'technician_dashboard'),
    }

    if user.role not in role_templates:
        messages.error(request, "Invalid role. Cannot edit profile.")
        return redirect('home')

    template, profile_model, form_class, redirect_url = role_templates[user.role]
    profile = get_object_or_404(profile_model, user=user)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            user.refresh_from_db()
            username_changed = (old_username != user.username)
            password_changed = (old_password != user.password)

            if username_changed or password_changed:
                messages.info(request, "Your credentials have been updated. Please log in again.")
                logout(request)
                return redirect('login')

            messages.success(request, "Profile updated successfully!")
            return redirect(redirect_url)
    else:
        form = form_class(instance=profile,user=request.user)

    return render(request, template, {'form': form, 'profile': profile})

@login_required 
def company_dashboard(request):
    company = request.user.company_profile    
    all_requests = ServiceRequest.objects.filter(company=company).select_related(
        'customer', 'technician', 'service_type'
    ).order_by('-preferred_date')

    counts = {
        'requested': all_requests.filter(status='requested').count(),
        'assigned': all_requests.filter(status='assigned').count(),
        'accepted': all_requests.filter(status='accepted').count(),
        'rejected': all_requests.filter(status='rejected').count(),
        'Proceeding': all_requests.filter(status='Proceeding').count(),
        'payment_pending': all_requests.filter(status='payment_pending').count(),
        'paid': all_requests.filter(status='paid').count(),
        'completed': all_requests.filter(status='completed').count(),
        'cancelled': all_requests.filter(status='cancelled').count(),
        'total': all_requests.count(),
    }
    
    
    status_cards = [
        ('requested', 'Requested', 'bi-hourglass-split', 'primary'),
        ('assigned', 'Assigned', 'bi-person-check-fill', 'info'),
        ('accepted', 'Accepted', 'bi-calendar-check-fill', 'success'),
        ('Proceeding', 'Proceeding', 'bi-gear-wide-connected', 'warning'),
        ('completed', 'Completed', 'bi-check-circle-fill', 'success'),
        ('payment_pending', 'Payment Pending', 'bi-wallet2', 'danger'),
        ('paid', 'Paid', 'bi-cash-stack', 'success'), 
        ('cancelled', 'Cancelled', 'bi-x-circle', 'secondary'),
    ]



    selected_status = request.GET.get('status')
    
    filtered_requests = all_requests
    if selected_status:
        filtered_requests = all_requests.filter(status=selected_status)

    paginator = Paginator(filtered_requests, 10)
    page_number = request.GET.get('page')
    service_requests = paginator.get_page(page_number)
    
    context = {
        'requests': service_requests,
        'count':counts,
        'status_cards': status_cards,
        'selected_status': selected_status,
        'company': company
    }

    return render(request, 'company_dashboard.html', context)


@login_required
def technician_list(request):
    company = get_object_or_404(CompanyProfile,user=request.user)
   
    service_types = ServiceType.objects.filter(company=company)
    selected_service = request.GET.get('service')
    if selected_service:
        selected_service = int(selected_service)
        technician_list  = TechnicianProfile.objects.filter(
            company=company, service_types__id=selected_service)
    else:
        technician_list  = TechnicianProfile.objects.filter(
            company=company)
    paginator = Paginator(technician_list, 10)
    page_number = request.GET.get('page')
    technicians = paginator.get_page(page_number)
    
    return render(request,'technician_list.html',context={
        'page_obj':technicians,'service_types':service_types,
        'selected_service':selected_service})


@login_required
def technician_add(request):
    company = request.user.company_profile
    services = ServiceType.objects.filter(company=company)

   
    service_choices = [(s.id, s.name) for s in services]
    if request.method == 'POST':
        form = TechnicianForm(request.POST)
        form.fields['service_types'].queryset = ServiceType.objects.filter(company=company)

        if form.is_valid():
            email = form.cleaned_data['email']
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            service_types = form.cleaned_data['service_types']

            username = generate_username(email, company.company_name)
            password = generate_password()

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='technician'
            )

            technician = form.save(commit=False)
            technician.user = user
            technician.name = name
            technician.company = company
            technician.save()
            technician.service_types.set(service_types)
            try:
                send_custom_email.delay(
                    subject=f"Welcome to {company.company_name}!",
                    message=f"""
                    Dear {technician.name},

                    Welcome to **{company.company_name}**!

                    Your technician account has been successfully created and activated.
                    You can now log in to your dashboard and begin managing your assigned service requests.

                     **Login Credentials**
                    • **Username:** {technician.user.username}
                    • **Password:** {password}

                    Please keep your credentials confidential and do not share them with anyone.

                    If you have any questions or need assistance, feel free to reach out to your company admin or our support team.

                    Thank you for joining our team!
                    We look forward to working with you.

                    Warm regards,
                    {company.company_name}
                    Support Team
                    """,
                        email=technician.user.email
                )
                messages.success(request, "Technician added and credentials sent by email.")
            except Exception as e:
                messages.warning(request, f"Technician added but email could not be sent")
            return redirect('technician_list')

    else:
        form = TechnicianForm()
        form.fields['service_types'].queryset = ServiceType.objects.filter(company=company)

    return render(request, 'technician_form.html', {'form': form,'service_choices':service_choices})



@login_required
def technician_edit(request, tech_id):
    technician = get_object_or_404(TechnicianProfile, id=tech_id)
    if request.method == "POST":
        technician.name = request.POST.get('name')
        technician.phone = request.POST.get('phone')
        selected_services = request.POST.getlist('service_types')
        technician.service_types.set(selected_services)
        technician.save()
        messages.success(request, "Technician updated successfully.")
    return redirect('technician_list')


@login_required
def technician_delete(request, tech_id):
    technician = get_object_or_404(TechnicianProfile, id=tech_id)
    if request.method == "POST":
        active_requests = ServiceRequest.objects.filter(
            technician=technician,
            status__in=['assigned', 'accepted', 'Proceeding']
        )
        print("active", active_requests)
        for req in active_requests:
            req.technician = None  
            req.status = 'requested'  
            req.save()
        user = technician.user
        technician.delete()
        user.delete()
        messages.success(request, "Technician deleted successfully.")
    return redirect('technician_list')


@login_required
def assign_technician(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    company = request.user.company_profile
    service_type = service_request.service_type
    technicians = TechnicianProfile.objects.filter(
        company=company,service_types=service_type)
    print("te", technicians)
    tech_data = []
    for tech in technicians:
        duties = ServiceRequest.objects.filter(
            technician=tech,
            status__in=['assigned', 'accepted', 'Proceeding', 'completed']
        ).order_by('preferred_date')
        tech_data.append({
            'tech': tech,
            'duties': duties
        })

    if request.method == 'POST':
        tech_id = request.POST.get('technician')
        technician = get_object_or_404(TechnicianProfile, id=tech_id)
        service_request.technician = technician
        service_request.status = 'assigned'
        service_request.save()
        message = f"New {service_request.service_type.name} service request assigned to you for {service_request.customer.cust_name}."
        create_notification.delay(technician.user.id, message)
        send_custom_email.delay(
            subject="Technician Assigned",
            message=f"""
                Hello {service_request.customer.cust_name},

                Your service request '{service_request.service_type.name}' 
                has been assigned to technician {technician.name}.

                Company: {company.company_name}
                """,
                email=service_request.customer.user.email
            )
        messages.success(request, f"{technician.name} has been assigned to this request.")
        return redirect('company_dashboard')

    return render(request, 'assign_technician.html', {
        'service_request': service_request,
        'tech_data': tech_data
    })


@login_required
def mark_payment_pending(request, pk):
    req = get_object_or_404(ServiceRequest, pk=pk)
    cust_user = req.customer.user.id
    if request.method == 'POST' and req.status == 'completed':
        req.status = 'payment_pending'
        req.save()
        message = f"Please complete payment for {req.title}"
        create_notification.delay(cust_user, message)
        messages.success(request, f"Requested {req.customer.cust_name} for makimg payment.")
    return redirect('company_dashboard')

def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user =  form.save(commit=False)
            user.role = 'customer'
            user.save()
            CustomerProfile.objects.create(
                    user=user,
                    cust_name=form.cleaned_data['cust_name'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                )
            send_custom_email.delay(
                subject="Welcome to ServiceConnect!",
                message=f"""
                Hello {form.cleaned_data['cust_name']},
                Your account has been created successfully.
                Thank you for joining ServiceConnect!""",
                email=form.cleaned_data['email']
            )
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('login')
    else:

        form = CustomerRegistrationForm()

    return render(request,'registration_form.html',
        context={'form':form,'title':'customer'})

def customer_dashboard(request):
    search = request.GET.get('search', '')
    company_id = request.GET.get('company', '')

    # services = ServiceType.objects.all()
    services = ServiceType.objects.annotate(
        avg_rating=Avg('service_requests__rating'),
        rating_count=Count('service_requests__rating')  
    ).order_by('-id')  
    if search:
        services = services.filter(name__icontains=search)
    if company_id:
        services = services.filter(company__id=company_id)
    
    paginator = Paginator(services, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    companies = CompanyProfile.objects.all()
    context ={ 
        "page_obj": page_obj,
        "companies": companies,
        "search": search,
        "company_id": company_id
    }
    
    return render(request,'customer_dashboard.html',
        context)

@login_required
def service_view(request):
    company = get_object_or_404(CompanyProfile, user=request.user)
    services_list = ServiceType.objects.filter(company=company)
    paginator = Paginator(services_list, 8) 

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request,'service_view.html',
        context={'page_obj':page_obj})


@login_required
def add_service(request):
    company = get_object_or_404(CompanyProfile, user=request.user)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save(commit=False)
            service.company = company
            service.save()
            messages.success(request, "Service added successfully!")
            return redirect('service_view')
    else:
        form = ServiceTypeForm()
    return render(request, 'service_form.html', 
        {'form': form, 'title': 'Add Service'})

@login_required
def edit_service(request, pk):
    service = get_object_or_404(ServiceType, pk=pk, company__user=request.user)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated successfully!")
            return redirect('service_view')
    else:
        form = ServiceTypeForm(instance=service)
    return render(request, 'service_form.html', 
        {'form': form, 'title': 'Edit Service'})

@login_required
def delete_service(request, pk):
    service = get_object_or_404(ServiceType, pk=pk, company__user=request.user)
    if request.method == 'POST':
        service.delete()
        messages.success(request, "Service deleted successfully!")
        return redirect('service_view')
    return render(request, 'delete_form.html', {'object': service})


@login_required
def cust_view_services(request,id):
    company = get_object_or_404(CompanyProfile,id=id)
    services = ServiceType.objects.filter(company=company)
    return render(request,'company_services.html',context={'services':services})

@login_required
def request_service(request, service_id):
    service = get_object_or_404(ServiceType, id=service_id)
    company = service.company
    customer_profile = get_object_or_404(CustomerProfile, user=request.user)
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.customer = customer_profile
            service_request.company = company
            service_request.service_type = service
            service_request.title = f"{service.name} - {company.company_name}"
            service_request.base_price = service.base_price
            service_request.save()
            message = f"New service request from {request.user.customer_profile.cust_name} for {service_request.service_type.name}."
            create_notification.delay(company.user.id, message)
            send_custom_email.delay(
                subject="New Service Request Received",
                message=f"""
                Hello {company.company_name},

                A new service request has been submitted.

                Customer: {customer_profile.cust_name}
                Service Requested: {service_request.service_type.name}
                Preferred Date: {service_request.preferred_date}""",
                    email=company.user.email
            )
            messages.success(request, "Service request submitted successfully!")
            return redirect('customer_dashboard')
        else:
            messages.error(request, "Something went wrong. Please check your input")
    else:
        form = ServiceRequestForm()

    return render(request, 'request_service.html', 
        { 'form': form, 'company': company, 'service': service})


@login_required
def cust_view_requests(request):
    customer = get_object_or_404(CustomerProfile, user=request.user)
    request_list = ServiceRequest.objects.filter(customer=customer).order_by('-created_at')

    status = request.GET.get('status')
    if status:
        request_list = request_list.filter(status=status)

    paginator = Paginator(request_list, 10)
    page_number = request.GET.get('page')
    requests = paginator.get_page(page_number)

    return render(request, 'customer_requests.html', {'requests': requests})



@login_required
def invoice_view(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    context = {
        'service_request': service_request,
        'customer': service_request.customer,
        'company': service_request.company,
        'technician': service_request.technician,
    }
    return render(request, 'invoice.html', context)


@login_required
def payment_proceed(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    if not service_request.actual_price:
        service_request.actual_price = service_request.base_price + (service_request.extra_charges or 0)

    service_request.status = 'paid'
    service_request.save()
    company_user = service_request.company.user.id
    message = f"{service_request.customer.cust_name} has paid {service_request.actual_price}"
    create_notification.delay(company_user, message)
    messages.success(request, "Payment successful! Thank you.")
    return redirect('feedback_view', request_id=service_request.id)

@login_required
def feedback_view(request, request_id):
    service_request = get_object_or_404(ServiceRequest, id=request_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        feedback_text = request.POST.get("feedback")

        service_request.rating = int(rating)
        service_request.feedback = feedback_text
        service_request.save()

        messages.success(request, "Thank you for sharing your valuable feedback!")
        return redirect("customer_dashboard")

    return render(request, "feedback.html", {'service_request': service_request})


@login_required
def technician_dashboard(request):
    tech_profile = get_object_or_404(TechnicianProfile, user=request.user)
    service_requests = ServiceRequest.objects.filter(technician=tech_profile)
    return render(request,'technician_dashboard.html',
        context={'tech':tech_profile, 'requests':service_requests})


@login_required
def update_request_status(request, request_id, status):
    tech_profile = get_object_or_404(TechnicianProfile, user=request.user)
    service_request = get_object_or_404(ServiceRequest, id=request_id, technician=tech_profile)
    company_user = service_request.company.user.id
    print("status",status)
    valid_statuses = ['accepted', 'rejected', 'Proceeding']
    if status not in valid_statuses:
        messages.error(request, "Invalid status update.")
        return redirect('technician_dashboard')

    service_request.status = status

    service_request.save()

    if status in ['accepted', 'Proceeding']:
        tech_profile.status = 'busy'
        if status == 'accepted':
            message = f"{tech_profile.name} has accepted {service_request.service_type.name} service for {service_request.customer.cust_name}"
        else:
            message = f"{tech_profile.name} is proceeding with {service_request.service_type.name} service for {service_request.customer.cust_name}"
    elif status == 'rejected':
        tech_profile.status = 'available'
        message = f"{tech_profile.name} has rejected {service_request.service_type.name} service for {service_request.customer.cust_name}"
    tech_profile.save()
    create_notification.delay(company_user, message)
    return redirect('technician_dashboard')


# @login_required
# def complete_service(request, request_id):
#     tech_profile = get_object_or_404(TechnicianProfile, user=request.user)
#     service_request = get_object_or_404(
#         ServiceRequest,
#         id=request_id,
#         technician=tech_profile
#     )
#     company_user = service_request.company.user.id
#     if request.method == 'POST':
#         extra_charges_input = request.POST.get('extra_charges', '').strip()
#         try:
#             extra_charges = Decimal(extra_charges_input) if extra_charges_input else Decimal(0)
#         except:
#             extra_charges = Decimal(0)
#         service_request.extra_charges = extra_charges
#         service_request.actual_price = service_request.base_price + extra_charges
#         service_request.status = 'completed'
#         service_request.save()
#         tech_profile.status = 'available'
#         tech_profile.save()
#         message = f"{tech_profile.name} has completed {service_request.service_type.name} service for {service_request.customer.cust_name}"
#         create_notification.delay(company_user, message)
#         messages.success(request, "Service marked as completed and sent for admin approval.")
#         return redirect('technician_dashboard')

#     return redirect('technician_dashboard')
@login_required
def complete_service(request, request_id):
    tech_profile = get_object_or_404(TechnicianProfile, user=request.user)
    service_request = get_object_or_404(
        ServiceRequest,
        id=request_id,
        technician=tech_profile
    )
    company_user = service_request.company.user.id
    
    if request.method == 'POST':
        extra_charges_input = request.POST.get('extra_charges', '').strip()
        try:
            extra_charges = Decimal(extra_charges_input) if extra_charges_input else Decimal(0)
        except:
            extra_charges = Decimal(0)
            
        service_request.extra_charges = extra_charges
        service_request.actual_price = service_request.base_price + extra_charges
        
        if extra_charges > 0:
            service_request.status = 'completed'
            message = f"{tech_profile.name} has completed {service_request.service_type.name} service for {service_request.customer.cust_name} with extra charges. Approval required."
            create_notification.delay(company_user, message)
            messages.success(request, "Service marked as completed. Waiting for company approval due to extra charges.")
        else:
            service_request.status = 'payment_pending'
            cust_user_id = service_request.customer.user.id
            cust_message = f"{service_request.title} service is completed. Please make the payment."
            create_notification.delay(cust_user_id, cust_message)
            comp_message = f"{tech_profile.name} has completed {service_request.service_type.name} service for {service_request.customer.cust_name}. Payment pending."
            create_notification.delay(company_user, comp_message)
            
            messages.success(request, "Service completed. Customer has been notified for payment.")

        service_request.save()
        tech_profile.status = 'available'
        tech_profile.save()
        
        return redirect('technician_dashboard')

    return redirect('technician_dashboard')

@login_required
def notifications(request):
    notifications = Notification.objects.filter(
        user=request.user, is_read=False).order_by('-created_at')
    data = [
        {"message": n.message, "created_at": n.created_at.strftime("%b %d, %H:%M"), "read": n.is_read}
        for n in notifications
    ]
    unread_count = notifications.count()
    return JsonResponse({"notifications": data,"unread_count":unread_count})


@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(
        user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"status": "ok"})