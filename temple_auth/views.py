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
from .forms import CustomAuthenticationForm, TempleCreateForm, UserUpdateForm
from django.urls import reverse_lazy
from django.contrib.auth.hashers import make_password
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from billing_manager.decorators import check_temple_session
from django.contrib.auth.models import User, Group
from .models import Note
from .forms import NoteForm

class CustomLoginView(LoginView):
    template_name = 'temple_auth/login.html'
    form_class = CustomAuthenticationForm

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            # Check if the user is in the "Central Admin" group
            if not user.groups.filter(name='Central Admin').exists():
                user_temples = user.userprofile.temples.all()
                if not all([not temple.deactivate for temple in user_temples]):
                    form.add_error(None, f'Hi {user.username}, Please contact administration for access.')
                    return self.form_invalid(form)

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
    temples = user_profile.temples.all()

    if not is_central_admin:
        temples = user_profile.temples.filter(deactivate=False)
    if not request.user.is_staff and not user_profile.temples.exists():
        messages.error(request, "No access to any temple.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        temple_id = request.POST.get('temple_id')
        temple = user_profile.temples.filter(id=temple_id).first()
        if temple:
            request.session['temple_id'] = str(temple.id)
            messages.success(request, f"Access granted to {temple.temple_name}.")
            if is_central_admin:
                return redirect('list-temples')
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid selection.")

    return render(request, 'temple_auth/temple_selection.html', {'temples': temples, 'is_central_admin': is_central_admin})


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
    title = temple.temple_bill_title if temple.temple_bill_title else ""
    mid = temple.temple_bill_mid if temple.temple_bill_mid else ""
    footer = temple.temple_bill_footer if temple.temple_bill_footer else ""
    return render(
        request, 'temple_auth/settings.html',
        {
            'temple': temple, 'user_profile': user_profile, 'is_central_admin': is_central_admin,
            'title': title, 'mid': mid, 'footer': footer
        }
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

    def post(self, request, *args, **kwargs):
        form = TempleCreateForm(request.POST)
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if form.is_valid():
            new_temple = form.save(commit=False)
            new_temple.save()
            messages.success(request, f"'{new_temple.temple_name}' successfully added.")
        else:
            messages.error(request, "Invalid input given for temple creation.")
        return redirect('list-temples')



@method_decorator(check_temple_session, name='dispatch')
class TempleDetailView(LoginRequiredMixin, ListView):
    model = UserProfile
    template_name = 'temple_auth/list_temple_users.html'
    context_object_name = 'users'
    paginate_by = 100

    def get_queryset(self):
        temple_id = self.kwargs['temple_id']
        self.temple = get_object_or_404(Temple, id=temple_id)

        queryset = UserProfile.objects.filter(
            temples=self.temple  # Corrected the lookup field
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['active_temple'] = self.temple.id
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
            user_detail["id"] = user.user.id
            user_detail["is_active"] = user.user.is_active
            if user.user.last_login:
                user_detail["last_login"] = user.user.last_login.strftime("%d-%m-%Y %I:%M:%S %p")
            else:
                user_detail["last_login"] = ""
            users_list.append(user_detail)
        context['user_list'] = users_list
        shortname = self.temple.temple_short_name  if self.temple.temple_short_name  else ""
        place = self.temple.temple_place if self.temple.temple_place else ""
        context['temple_breadcrumb'] = str(shortname) + " - " + str(place)
        context['temple'] = self.temple
        context["temple_id"] = str(self.temple)
        return context

    def post(self, request, *args, **kwargs):
        temple_id = self.kwargs['temple_id']

        # Access all input data
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        re_password = request.POST.get('retypePassword')
        group_name = request.POST.get('role')

        # Validation
        if not username or not password or not re_password or not group_name:
            messages.error(request, "All fields are required.")
            return redirect('temple-detail', temple_id=temple_id)

        if password != re_password:
            messages.error(request, "Passwords do not match.")
            return redirect('temple-detail', temple_id=temple_id)

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('temple-detail', temple_id=temple_id)

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            messages.error(request, f'Group "{group_name}" does not exist')
            return redirect('temple-detail', temple_id=temple_id)

        temples = Temple.objects.filter(id__in=[temple_id])

        if not temples.exists():
            messages.error(request, "At least one valid temple must be selected.")
            return redirect('temple-detail', temple_id=temple_id)

        # User Creation
        user = User.objects.create(username=username)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.set_password(password)
        user.save()

        # User Profile Creation
        user_profile = UserProfile.objects.create(user=user)
        user_profile.temples.set(temples)

        # Add User to Group
        user.groups.add(group)
        messages.success(request, f'User "{username}" created, added to privilege "{group_name}", and linked to selected temples.')
        return redirect('temple-detail', temple_id=temple_id)



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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['active_temple'] = temple.id
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        return context

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


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "temple_auth/user_edit.html"
    context_object_name = 'user_to_edit'

    def get_success_url(self):
        # Redirect to the temple detail page with the user's pk
        user = User.objects.get(id=self.object.pk)
        profile = UserProfile.objects.get(user=user)
        if profile.temples:
            temple = profile.temples.values()[0].get('id')
            messages.success(self.request, f"Successfully updated details for user: {user.username}")
            return reverse_lazy("temple-detail", kwargs={'temple_id': temple})
        return reverse_lazy("list-temples")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['active_temple'] = temple.id
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        context["username"] = User.objects.get(id=self.object.pk).username
        context['user_to_edit'] = User.objects.get(id=self.object.pk)
        context['temple'] = temple
        return context


@login_required
@check_temple_session
def update_password_view(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # Ensure only superusers can update passwords for other users
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    if not is_central_admin:
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validate new passwords
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("user-update", pk=user.id)

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect("user-update", pk=user.id)

        # Update the password
        user.password = make_password(new_password)
        user.save()
        messages.success(request, f"Password for {user.username} updated successfully.")
        return redirect("user-update", pk=user.id)
    message.error("Invalid request.")
    return redirect("user-update", pk=user.id)


@login_required
@check_temple_session
def update_deactivate_view(request, temple_id, user_id):
    user = get_object_or_404(User, id=user_id)

    # Ensure only superusers can update passwords for other users
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()
    temple = get_object_or_404(Temple, id=temple_id)
    if not is_central_admin:
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == "POST":

        # Update the password
        is_active = "Deactivate" if user.is_active else "Activated"
        user.is_active = False if user.is_active else True
        user.save()

        messages.success(request, f"User {user.username} is {is_active} successfully.")
        return redirect("temple-detail", temple_id=temple.id)
    message.error("Invalid request.")
    return redirect("temple-detail", temple_id=temple.id)



class NoteListView(LoginRequiredMixin, View):
    template_name = "temple_auth/user_note.html"

    def get(self, request):
        notes = Note.objects.filter(user=request.user).order_by('-updated_at')
        is_central_admin = request.user.groups.filter(name='Central Admin').exists()
        return render(request, self.template_name, {'notes': notes, 'is_central_admin': is_central_admin})

class NoteCreateView(LoginRequiredMixin, View):
    template_name = "temple_auth/user_note_create.html"

    def get(self, request):
        form = NoteForm()
        is_central_admin = request.user.groups.filter(name='Central Admin').exists()
        return render(request, self.template_name, {'form': form, 'is_central_admin': is_central_admin})

    def post(self, request):
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            return redirect('note_list')
        return render(request, self.template_name, {'form': form})

class NoteUpdateView(LoginRequiredMixin, View):
    template_name = "temple_auth/note_update.html"

    def get(self, request, pk):
        # Fetch the note instance for the logged-in user
        note = get_object_or_404(Note, pk=pk, user=request.user)
        form = NoteForm(instance=note)  # Pre-fill the form with the note's data
        is_central_admin = request.user.groups.filter(name='Central Admin').exists()
        return render(request, self.template_name, {'form': form, 'is_central_admin': is_central_admin})

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('note_list')  # Redirect to the note list after saving
        return render(request, self.template_name, {'form': form})

class NoteDeleteView(LoginRequiredMixin, View):
    template_name = "note_confirm_delete.html"

    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        is_central_admin = request.user.groups.filter(name='Central Admin').exists()
        return render(request, self.template_name, {'note': note, 'is_central_admin': is_central_admin})

    def post(self, request, pk):
        note = get_object_or_404(Note, pk=pk, user=request.user)
        note.delete()
        return redirect('note_list')


@login_required
@check_temple_session
def deactivate_temple(request, temple_id):

    # Ensure only superusers can update passwords for other users
    is_central_admin = request.user.groups.filter(name='Central Admin').exists()        
    if not is_central_admin:
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == "POST":
        temple = get_object_or_404(Temple, id=temple_id)
        # Update the password
        is_active = "Activated" if temple.deactivate else "Deactivated"
        if temple.deactivate:
            temple.deactivate = False
        else:
            temple.deactivate = True
        temple.save()

        messages.success(request, f"Temple {temple.temple_short_name} is {is_active} successfully.")
        return redirect("list-temples")
    message.error("Invalid request.")
    return redirect("list-temples")

