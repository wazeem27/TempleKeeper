# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View
from .models import UserProfile, Temple
from billing_manager.models import Bill
from temple_inventory.models import InventoryItem

from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm


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
    if not request.user.is_staff and not user_profile.temples.exists():
        messages.error(request, "No access to any temple.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        temple_id = request.POST.get('temple_id')
        temple = user_profile.temples.filter(id=temple_id).first()
        if temple:
            request.session['temple_id'] = temple.id
            messages.success(request, f"Access granted to {temple.temple_name}.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid selection.")

    return render(request, 'temple_auth/temple_selection.html', {'temples': user_profile.temples.all()})


@login_required
def dashboard_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')

    temple = get_object_or_404(Temple, id=temple_id)
    return render(request, 'temple_auth/new_dashboard.html', {'temple': temple})


@login_required
def whats_new_page(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')

    temple = get_object_or_404(Temple, id=temple_id)
    return render(request, 'temple_auth/whats_new.html', {'temple': temple})


@login_required
def settings_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')
    
    user_profile = UserProfile.objects.get(user=request.user)  # Get the logged-in user's profile

    temple = get_object_or_404(Temple, id=temple_id)
    return render(request, 'temple_auth/settings.html', {'temple': temple, 'user_profile': user_profile})


def update_temple_bill(request):
    if request.method == "POST":
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        temple.temple_bill_title = request.POST.get('temple_bill_title', '')
        temple.temple_bill_mid = request.POST.get('temple_bill_mid', '')
        temple.temple_bill_footer = request.POST.get('temple_bill_footer', '')
        temple.save()
        messages.success(request, "Bill details updated successfully!")
        return redirect('settings')  # Redirect after saving



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