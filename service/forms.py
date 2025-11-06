from django import forms
from datetime import date
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from . models import CustomerProfile,CompanyProfile,ServiceType,ServiceRequest,TechnicianProfile


User = get_user_model()
class CompanyRegistrationForm(UserCreationForm):
    company_name = forms.CharField(label='Company Name', max_length=100)
    phone = forms.CharField(label='Phone', max_length=15)
    address = forms.CharField(label='Address', widget=forms.Textarea(attrs={'rows': 3}))
    logo = forms.ImageField(label='Company Logo', required=False)

    class Meta:
        model = User
        fields = [ 'company_name', 'phone','email', 'address', 'logo','username', 'password1', 'password2']

class CustomerRegistrationForm(UserCreationForm):
    cust_name = forms.CharField(label='Customer Name', max_length=100)
    phone = forms.CharField(label='Phone', max_length=15)
    address = forms.CharField(label='Address', widget=forms.Textarea(attrs={'rows': 3}))
    class Meta:
        model = User
        fields = [ 'cust_name', 'phone','email', 'address','username','password1', 'password2']


class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model=ServiceType
        fields = ['name','description','base_price','image']
    label = (
        'name','Service Name',
        'description','Description',
        'base_price','Charge',
        'image','Image',

    )
    widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter description'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter base price'}),
        }

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['description','preferred_date']
        label = (
            'preferred_date','Preferred Date',
            'description','Service Description'
                 )
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe your issue...',  'rows': 3}),
            'preferred_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date','min': date.today().isoformat()}
            ),
        }

class TechnicianForm(forms.ModelForm):
    email = forms.EmailField(label='Technician Email', required=True)

    class Meta:
        model = TechnicianProfile
        fields = ['name','phone', 'service_types']
        widgets = {
            'service_types': forms.CheckboxSelectMultiple()
        }

class UserEditForm(forms.ModelForm):
    username = forms.CharField(required=True, label="Username")
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, required=False, label="New Password")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email

    def save_user_fields(self, user):
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        user.save()
        return user

class CustomerProfileForm(UserEditForm):
    class Meta:
        model = CustomerProfile
        fields = ['cust_name', 'phone', 'address']

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        self.save_user_fields(user)
        if commit:
            profile.save()
        return 
    
class CompanyProfileForm(UserEditForm):
    class Meta:
        model = CompanyProfile
        fields = ['company_name', 'phone', 'address', 'logo']

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        self.save_user_fields(user)
        if commit:
            profile.save()
        return profile
    
class TechnicianSelfEditForm(UserEditForm):
    class Meta:
        model = TechnicianProfile
        fields = ['name', 'phone']

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        self.save_user_fields(user)
        if commit:
            profile.save()
        return profile

class CompleteServiceForm(forms.ModelForm):
    extra_charges = forms.DecimalField(max_digits=10, decimal_places=2,
        required=False, label="Extra Charges (if any)", initial=0)

    class Meta:
        model = ServiceRequest
        fields = ['base_price', 'extra_charges']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['base_price'].disabled = True 