from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from billing_manager.models import Bill, BillInventoryItem, BillVazhipaduOffering
from typing import Dict, Any
from temple_auth.models import UserProfile


class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/create_bill.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple).order_by('id')

    def get_star_queryset(self) -> Any:
        return Star.objects.all().order_by('id')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        
        context['vazhipadu_items'] = self.get_vazhipadu_queryset(temple)
        context['inventory_items'] = self.get_inventory_queryset(temple)
        context['star_items'] = self.get_star_queryset()
        context['temple'] = temple
        
        return context


class BillListView(LoginRequiredMixin, ListView):
    model = Bill
    template_name = 'billing_manager/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 10

    def get_queryset(self):
        # Specify an ordering for the Bill objects
        return Bill.objects.order_by('-created_at')
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple
        return context

@login_required
def submit_billing(request: HttpRequest) -> HttpResponse:
    """Handle billing submission and create the associated records for the specified temple."""
    if request.method == 'POST':
        # Extract and validate input data
        billing_name = request.POST.get('billing_name', '').strip()
        billing_address = request.POST.get('billing_address', '').strip()

        # Retrieve the current temple from the session
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        # Prices from the POST data
        pooja_price = sum(map(float, request.POST.getlist('pooja_price[]')))
        thing_price = sum(map(float, request.POST.getlist('thing_price[]')))

        # Validation for billing name
        if not billing_name:
            messages.error(request, "Billing name and address are required.")
            # Preserve input values in session for pre-filling the form
            request.session['billing_data'] = {
                'billing_name': billing_name,
                'billing_address': billing_address,
                'names': request.POST.getlist('names[]'),
                'pooja': request.POST.getlist('pooja[]'),
                'customer_star': request.POST.getlist('nakshatram[]'),
                'vazhipadu_price': request.POST.getlist('pooja_price[]'),
                'thing': request.POST.getlist('thing[]'),
                'quantity': request.POST.getlist('quantity[]'),
                'thing_price': request.POST.getlist('thing_price[]')
            }
            return redirect('add-bill')  # Redirect back to the billing page

        # Begin a transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Create the bill instance
                bill = Bill.objects.create(
                    customer_name=billing_name,
                    customer_address=billing_address,
                    user=request.user,
                    temple=temple,
                    total_amount=Decimal(pooja_price + thing_price)
                )

                # Handle vazhipadu offerings if present
                if request.POST.getlist('pooja[]'):
                    names = request.POST.getlist('name[]')
                    vazhipadu_list = request.POST.getlist('pooja[]')
                    stars = request.POST.getlist('nakshatram[]')
                    vazhipadu_prices = request.POST.getlist('pooja_price[]')

                    # Create BillVazhipaduOffering instances for each offering
                    for index, vazhipadu_name in enumerate(vazhipadu_list):
                        if vazhipadu_name.strip():  # Validate not empty
                            vazhipadu_offering = get_object_or_404(VazhipaduOffering, name=vazhipadu_name, temple=temple)
                            price = Decimal(vazhipadu_prices[index])
                            customer_star = get_object_or_404(Star, name=stars[index])

                            BillVazhipaduOffering.objects.create(
                                bill=bill,
                                vazhipadu_offering=vazhipadu_offering,
                                person_name=names[index],
                                person_star=customer_star,
                                quantity=1,  # Default to 1 if not specified
                                price=price
                            )

                # Handle inventory items if present
                if request.POST.getlist('thing[]'):
                    thing_names = request.POST.getlist('thing[]')
                    thing_quantities = request.POST.getlist('quantity[]')
                    thing_prices = request.POST.getlist('thing_price[]')

                    # Create BillInventoryItem instances for each inventory item
                    for index, thing_name in enumerate(thing_names):
                        if thing_name.strip():  # Validate not empty
                            inventory_item = get_object_or_404(InventoryItem, name=thing_name, temple=temple)
                            quantity = int(thing_quantities[index])
                            price = Decimal(thing_prices[index])

                            BillInventoryItem.objects.create(
                                bill=bill,
                                inventory_item=inventory_item,
                                quantity=quantity,
                                price=price
                            )

                # Commit the bill instance creation after both vazhipadu and inventory items are handled
                bill.save()

                # Clear session data on successful submission
                request.session.pop('billing_data', None)

                messages.success(request, "Billing details have been successfully recorded.")
                return redirect(reverse('bill-detail', kwargs={'pk': bill.id}))  # Redirect to the bill detail page

        except Exception as e:
            # If any exception occurs, rollback the transaction to prevent partial saves
            messages.error(request, f"An error occurred while processing the billing: {e}")
            return redirect('add-bill')  # Redirect to an error page or billing form if something goes wrong

    messages.error(request, "Invalid request method.")
    return redirect('add-bill')  # Handle non-POST request



class BillDetailView(LoginRequiredMixin, DetailView):
    model = Bill
    template_name = "billing_manager/bill_detail.html"
    context_object_name = "bill"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional data if necessary
        context["title"] = f"Bill Details for {self.object.customer_name}"
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple
        return context


class ReceiptView(LoginRequiredMixin, DetailView):
    model = Bill
    context_object_name = "bill"

    def get_template_names(self):
        # Retrieve the current user profile
        user_profile = UserProfile.objects.filter(user=self.request.user)[0]
        if user_profile.is_split_bill:
            # If the user has selected split billing, return the split receipt template
            return ["billing_manager/split_receipt.html"]
        else:
            # Otherwise, return the standard receipt template
            return ["billing_manager/receipt.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Retrieve the current temple from the session
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        # Add any additional data if necessary
        context["title"] = f"Bill Details for {self.object.customer_name}"
        context["temple"] = temple
        return context