# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View, TemplateView, ListView, UpdateView
from .models import UserProfile, Temple
from billing_manager.models import Bill
from temple_inventory.models import InventoryItem
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import localtime
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.urls import reverse_lazy

from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from billing_manager.decorators import check_temple_session


class CustomLoginView(LoginView):
    template_name = 'temple_auth/login.html'
    form_class = CustomAuthenticationForm

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            user_profile = user.userprofile
            if not user_profile.has_selected_temple():
                return redirect('temple_selection')
            return redirect('dashboard')
        else:
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def temple_selection_view(request):
    user_profile = request.user.userprofile
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    if not request.user.is_staff and not user_profile.temples.exists():
        messages.error(request, "No access to any temple.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        temple_id = request.POST.get('temple_id')
        temple = user_profile.temples.filter(id=temple_id).first()
        if temple:
            request.session['temple_id'] = temple.id
            messages.success(request, f"Access granted to {temple.temple_name}.")
            if is_central_admin:
                return redirect('list-temples')
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid selection.")

    return render(request, 'temple_auth/temple_selection.html', {'temples': user_profile.temples.all(), 'is_central_admin': is_central_admin})


@login_required
def temple_creation_view(request):
    if request.method == 'POST':
        # Extract form data from the POST request
        temple_name = request.POST.get('temple_name')
        temple_place = request.POST.get('temple_place')
        temple_short_name = request.POST.get('temple_short_name')
        temple_bill_title = request.POST.get('temple_bill_title')
        temple_bill_mid = request.POST.get('temple_bill_mid')
        temple_bill_footer = request.POST.get('temple_bill_footer')

        # Validate mandatory fields
        if not temple_name:
            messages.error(request, "Temple name is required.")
            return render(request, 'temple_auth/temple_selection.html', context=request.POST)

        # Create and save the Temple instance
        try:
            temple = Temple.objects.create(
                temple_name=temple_name,
                temple_place=temple_place,
                temple_short_name=temple_short_name,
                temple_bill_title=temple_bill_title,
                temple_bill_mid=temple_bill_mid,
                temple_bill_footer=temple_bill_footer
            )
            messages.success(request, f"Temple '{temple.temple_name}' created successfully.")
            return redirect('temple_selection')  # Redirect to a temple list or dashboard page
        except Exception as e:
            messages.error(request, f"An error occurred while creating the temple: {e}")
            return redirect('temple_selection')  # Redirect to a temple list or dashboard page

    # GET request: Render the empty form
    return render(request, 'temple_auth/temple_selection.html')

@login_required
@check_temple_session
def dashboard_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')
    is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    temple = get_object_or_404(Temple, id=temple_id)
    context = {
        'is_billing_assistant': is_billing_assistant,
        'is_central_admin': is_central_admin,
        'temple': temple
    }

    return render(request, 'temple_auth/new_dashboard.html', context)


@login_required
@check_temple_session
def whats_new_page(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')

    temple = get_object_or_404(Temple, id=temple_id)
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    return render(request, 'temple_auth/whats_new.html', {'temple': temple, 'is_central_admin': is_central_admin})


@login_required
@check_temple_session
def settings_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')
    
    user_profile = UserProfile.objects.get(user=request.user)  # Get the logged-in user's profile

    temple = get_object_or_404(Temple, id=temple_id)
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    return render(
        request, 'temple_auth/settings.html',
        {'temple': temple, 'user_profile': user_profile, 'is_central_admin': is_central_admin}
    )


@login_required
@check_temple_session
def update_temple_bill(request):
    if request.method == "POST":
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        temple.temple_bill_footer = request.POST.get('temple_bill_footer', '')
        temple.save()
        messages.success(request, "Bill details updated successfully!")
        return redirect('settings')  # Redirect after saving


@login_required
@check_temple_session
def update_split_receipt(request):
    user_profile = UserProfile.objects.get(user=request.user)  # Get the logged-in user's profile

    if request.method == "POST":
        # Update the is_split_bill field based on the checkbox
        is_split_bill = request.POST.get('is_split_bill') == 'on'
        user_profile.is_split_bill = is_split_bill
        user_profile.save()

        # Add a success message
        messages.success(request, "Split receipt preference updated successfully!")
        return redirect('settings')  # Redirect after saving

@method_decorator(check_temple_session, name='dispatch')
class AdminSubMenu(LoginRequiredMixin, TemplateView):
    template_name = 'temple_auth/admin_section.html'

@method_decorator(check_temple_session, name='dispatch')
class TempleListView(LoginRequiredMixin, ListView):
    model = Temple
    template_name = 'temple_auth/temple_list.html'
    context_object_name = 'temples'
    paginate_by = 100

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['active_temple'] = temple.id
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        context['temple'] = temple
        
        return context

@method_decorator(check_temple_session, name='dispatch')
class TempleDetailView(LoginRequiredMixin, ListView):
    model = UserProfile
    template_name = 'temple_auth/list_temple_users.html'
    context_object_name = 'users'
    paginate_by = 100

    def get_queryset(self):
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        queryset = UserProfile.objects.filter(
            temples__id__in=[temple_id]  # Corrected the lookup field
        ).order_by('user__username')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['active_temple'] = temple.id
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin

        users_list = []
        for user in self.get_queryset():
            if user.user.groups.filter(name='Central Admin').exists():
                continue
            user_detail = {}
            user_detail["username"] = user.user.username
            role = ""
            if user.user.groups.filter(name='Temple Admin').exists():
                role = "Temple Admin"
            elif user.user.groups.filter(name='Billing Assistant').exists():
                role = "Billing Assistant"

            user_detail["role"] = role
            user_detail["first_name"] = user.user.first_name
            user_detail["last_name"] = user.user.last_name
            user_detail["email"] = user.user.email
            user_detail["is_active"] = user.user.is_active
            if user.user.last_login:
                user_detail["last_login"] = user.user.last_login.strftime("%d-%m-%Y %I:%M:%S %p")
            else:
                user_detail["last_login"] = ""
            users_list.append(user_detail)
        context['user_list'] = users_list
        shortname = temple.temple_short_name  if temple.temple_short_name  else ""
        place = temple.temple_place if temple.temple_place else ""
        context['temple_breadcrumb'] = str(shortname) + str(place)
        context['temple'] = temple
        return context

@method_decorator(check_temple_session, name='dispatch')
class TempleUpdateView(LoginRequiredMixin, UpdateView):
    model = Temple
    fields = [
        "temple_name",
        "temple_place",
        "temple_short_name",
        "temple_bill_title",
        "temple_bill_mid",
        "temple_bill_footer",
    ]
    template_name = "temple_auth/temple_edit.html"
    success_url = reverse_lazy("list-temples")  # Redirect to the list view after a successful update

    def form_valid(self, form):
        # Add a success message
        temple = form.instance
        messages.success(self.request, f"Temple '{temple.temple_name}' details updated successfully.")
        return super().form_valid(form)

    # def test_func(self):
    #     # Restrict access to staff/admin users
    #     return self.request.user.is_staff


@login_required
def temple_deselect_view(request):
    # Check if the temple_id exists in the session
    if 'temple_id' in request.session:
        del request.session['temple_id']  # Remove the temple_id from the session
        messages.success(request, "You have been logged out of the temple.")
    else:
        messages.error(request, "You are not currently logged into any temple.")

    # Redirect the user back to the temple selection page
    return redirect('temple_selection')