from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth import login,authenticate,logout
from .forms import (CompanyRegistrationForm,CustomerRegistrationForm,
                    CustomerProfileForm,CompanyProfileForm,ServiceTypeForm,
                    ServiceRequestForm,TechnicianForm,TechnicianSelfEditForm)
from . models import CompanyProfile,ServiceRequest,TechnicianProfile,CustomerProfile, ServiceType
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from decimal import Decimal
import random
import string

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
    if request.user.role != 'company':
        return redirect('login')  

    company = request.user.company_profile 
    service_requests_list = ServiceRequest.objects.filter(
        company=company).order_by('-preferred_date')
    technicians = TechnicianProfile.objects.filter(company=company)
    paginator = Paginator(service_requests_list, 10)
    page_number = request.GET.get('page')
    service_requests = paginator.get_page(page_number)

    return render(request,'company_dashboard.html',
        context={'company':company, 'requests': service_requests,'technicians': technicians})

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
    return render(request,'technician_list.html',context={
        'technicians':technician_list,'service_types':service_types,
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
                subject = f"Welcome to {company.company_name} as a Technician!"
                message = (
                    f"Dear {technician.name},\n\n"
                    f"Welcome to {company.company_name}!\n\n"
                    f"We’re excited to have you on board as one of our valued technicians. "
                    f"Your account has been successfully created in our system.\n\n"
                    f"Here are your login details:\n"
                    f"Username: {username}\n"
                    f"Password: {password}\n\n"
                    f"You can log in to your account using the link below:\n"
                    f"http://127.0.0.1:8000/login/\n\n"
                    f"Best regards,\n"
                    f"{company.company_name} \n"
                )
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
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
        messages.success(request, f"{technician.name} has been assigned to this request.")
        return redirect('company_dashboard')

    return render(request, 'assign_technician.html', {
        'service_request': service_request,
        'tech_data': tech_data
    })


@login_required
def mark_payment_pending(request, pk):
    req = get_object_or_404(ServiceRequest, pk=pk)
    if request.method == 'POST' and req.status == 'completed':
        req.status = 'payment_pending'
        req.save()
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
    
        return redirect('login')
    else:

        form = CustomerRegistrationForm()

    return render(request,'registration_form.html',
        context={'form':form,'title':'customer'})

def customer_dashboard(request):
    companies = CompanyProfile.objects.all()
    return render(request,'customer_dashboard.html',
        context={'companies':companies})

@login_required
def service_view(request):
    company = get_object_or_404(CompanyProfile, user=request.user)
    services_list = ServiceType.objects.filter(company=company)
    return render(request,'service_view.html',
        context={'service_types':services_list})


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
    print("company",company)
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
    customer = get_object_or_404(CustomerProfile,user=request.user)
    requests= ServiceRequest.objects.filter(customer=customer)
    return render(request,'customer_requests.html',context={'requests':requests})


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
    print("status",status)
    valid_statuses = ['accepted', 'rejected', 'Proceeding']
    if status not in valid_statuses:
        messages.error(request, "Invalid status update.")
        return redirect('technician_dashboard')

    service_request.status = status
    service_request.save()

    if status in ['accepted', 'proceeding']:
        tech_profile.status = 'busy'
    elif status == 'rejected':
        tech_profile.status = 'available'
    tech_profile.save()

    return redirect('technician_dashboard')


@login_required
def complete_service(request, request_id):
    tech_profile = get_object_or_404(TechnicianProfile, user=request.user)
    service_request = get_object_or_404(
        ServiceRequest,
        id=request_id,
        technician=tech_profile
    )

    if request.method == 'POST':
        extra_charges_input = request.POST.get('extra_charges', '').strip()
        print("input",extra_charges_input)
        try:
            extra_charges = Decimal(extra_charges_input) if extra_charges_input else Decimal(0)
        except:
            extra_charges = Decimal(0)

        print("extra",extra_charges)
        service_request.extra_charges = extra_charges
        service_request.actual_price = service_request.base_price + extra_charges
        service_request.status = 'completed'
        service_request.save()

       
        tech_profile.status = 'available'
        tech_profile.save()

        messages.success(request, "Service marked as completed and sent for admin approval.")
        return redirect('technician_dashboard')

    return redirect('technician_dashboard')