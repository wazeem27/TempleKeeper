from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from billing_manager.models import Bill, BillInventoryItem, BillVazhipaduOffering
from typing import Dict, Any


class BillingView(TemplateView):
    template_name = "billing_manager/create_bill.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple)

    def get_star_queryset(self) -> Any:
        return Star.objects.all()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        
        context['vazhipadu_items'] = self.get_vazhipadu_queryset(temple)
        context['inventory_items'] = self.get_inventory_queryset(temple)
        context['star_items'] = self.get_star_queryset()
        
        return context


def submit_billing(request: HttpRequest) -> HttpResponse:
    """Handle billing submission and create the associated records for the specified temple."""
    if request.method == 'POST':
        # Extract and validate input data
        billing_name = request.POST.get('billing_name', '').strip()
        billing_address = request.POST.get('billing_address', '').strip()
        
        # Retrieve the current temple from the session
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if not billing_name or not billing_address:
            messages.error(request, "Billing name and address are required.")
            # Preserve input values in the session for pre-filling
            request.session['billing_data'] = {
                'billing_name': billing_name,
                'billing_address': billing_address,
                'names': request.POST.getlist('names[]'),
                'pooja': request.POST.getlist('pooja[]'),
                'customer_star': request.POST.getlist('customer_star[]'),
                'vazhipadu_price': request.POST.getlist('vazhipadu_price[]'),
                'thing': request.POST.getlist('thing[]'),
                'quantity': request.POST.getlist('quantity[]'),
                'thing_price': request.POST.getlist('thing_price[]')
            }
            return redirect('billing')  # Redirect back to the billing page

        # Begin a transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Create the bill instance
                bill = Bill.objects.create(
                    customer_name=billing_name,
                    customer_address=billing_address,
                    user=request.user,
                    temple=temple,
                    total_amount=Decimal('0.00')
                )

                # Handle vazhipadu offerings if present
                if request.POST.getlist('pooja[]'):
                    names = request.POST.getlist('names[]')
                    vazhipadu_list = request.POST.getlist('pooja[]')
                    stars = request.POST.getlist('customer_star[]')
                    vazhipadu_prices = request.POST.getlist('vazhipadu_price[]')

                    for index, vazhipadu_name in enumerate(vazhipadu_list):
                        if vazhipadu_name.strip():  # Validate not empty
                            vazhipadu_offering = get_object_or_404(VazhipaduOffering, name=vazhipadu_name, temple=temple)
                            price = Decimal(vazhipadu_prices[index])
                            customer_star = get_object_or_404(Star, name=stars[index])

                            BillVazhipaduOffering.objects.create(
                                bill=bill,
                                vazhipadu_offering=vazhipadu_offering,
                                quantity=1,  # Default to 1 if not specified
                                price=price
                            )

                # Handle inventory items if present
                if request.POST.getlist('thing[]'):
                    thing_names = request.POST.getlist('thing[]')
                    thing_quantities = request.POST.getlist('quantity[]')
                    thing_prices = request.POST.getlist('thing_price[]')

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

                # Calculate total amount for the bill
                total_amount = sum(item.price * item.quantity for item in bill.bill_inventory_items.all()) + \
                               sum(offering.price * offering.quantity for offering in bill.bill_vazhipadu_offerings.all())
                
                # Update the total amount in the Bill instance
                bill.total_amount = total_amount
                bill.save()

                # Clear session data on successful submission
                request.session.pop('billing_data', None)

                messages.success(request, "Billing details have been successfully recorded.")
                return redirect('billing')  # Redirect to a success page

        except Exception as e:
            # Log the error for debugging (could be implemented in a real scenario)
            messages.error(request, f"An error occurred while processing the billing: {e}")
            return redirect('billing-error')  # Redirect to an error page if something goes wrong

    messages.error(request, "Invalid request method.")
    return redirect('billing-error')  # Handle non-POST requests