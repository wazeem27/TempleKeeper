from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from collections import defaultdict
from django.utils.timezone import localtime
from billing_manager.models import Bill, BillInventoryItem, BillVazhipaduOffering
from typing import Dict, Any
from temple_auth.models import UserProfile


subreceipt_ids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']

class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/create_bill.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple).order_by('order')

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
        # Base queryset filtered by temple
        temple_id = self.request.session.get('temple_id')
        if not temple_id:
            return Bill.objects.none()  # If no temple_id, return an empty queryset

        queryset = Bill.objects.prefetch_related(
            'vazhipadu_offerings',
            'bill_vazhipadu_offerings__vazhipadu_offering',
            'bill_vazhipadu_offerings__person_star',
            'user'
        ).filter(temple_id=temple_id).order_by('id')

        # Get search and date range filter parameters
        search_query = self.request.GET.get('q', '')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        # Filter by search query
        if search_query:
            queryset = queryset.filter(
                Q(id__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(bill_vazhipadu_offerings__vazhipadu_offering__name__icontains=search_query) |
                Q(bill_vazhipadu_offerings__person_name__icontains=search_query)
            ).distinct()

        # Filter by date range
        if start_date:
            queryset = queryset.filter(created_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(created_at__date__lte=parse_date(end_date))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get temple details
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple

        # Use paginated bills for the current page
        bills = context['object_list']
        bill_dataset = []

        for bill in bills:
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            sub_receipt_counter = iter("abcdefghijklmnopqrstuvwxyz")

            # Construct the dataset
            for idx, vazhipadu_bill in enumerate(vazhipadu_list, start=1):
                subreceipt = '-' if len(vazhipadu_list) == 1 else next(sub_receipt_counter)

                bill_entry = {
                    'receipt': bill.id,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': vazhipadu_bill.vazhipadu_offering.name,
                    'name': vazhipadu_bill.person_name,
                    'star': vazhipadu_bill.person_star.name if vazhipadu_bill.person_star else "",
                    'amount': vazhipadu_bill.price,
                }
                bill_dataset.append(bill_entry)

        # Add paginated dataset and filters to the context
        context['bills'] = bill_dataset
        context['search_query'] = self.request.GET.get('q', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')

        return context



@login_required
def submit_billing(request: HttpRequest) -> HttpResponse:
    """Handle billing submission and create associated records for the specified temple."""
    if request.method == 'POST':
        # Retrieve temple from the session
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        # Extract price lists from POST data
        pooja_price_list = list(map(float, request.POST.getlist('pooja_price[]')))
        thing_price_list = list(map(float, request.POST.getlist('thing_price[]')))

        # Retrieve user profile for split bill preference
        user_profile = get_object_or_404(UserProfile, user=request.user, temples__id=temple_id)

        # Begin transaction to ensure atomicity
        try:
            with transaction.atomic():
                if user_profile.is_split_bill:
                    # Create separate bills for each offering or item
                    if request.POST.getlist('pooja[]'):
                        names = request.POST.getlist('name[]')
                        vazhipadu_list = request.POST.getlist('pooja[]')
                        stars = request.POST.getlist('nakshatram[]')
                        vazhipadu_prices = request.POST.getlist('pooja_price[]')

                        for index, vazhipadu_name in enumerate(vazhipadu_list):
                            if vazhipadu_name.strip():
                                vazhipadu_offering = get_object_or_404(
                                    VazhipaduOffering, name=vazhipadu_name, temple=temple)
                                price = Decimal(vazhipadu_prices[index])
                                customer_star = get_object_or_404(Star, name=stars[index])

                                # Create a new bill for this offering
                                bill = Bill.objects.create(
                                    user=request.user,
                                    temple=temple,
                                    total_amount=price
                                )

                                # Create associated BillVazhipaduOffering record
                                BillVazhipaduOffering.objects.create(
                                    bill=bill,
                                    vazhipadu_offering=vazhipadu_offering,
                                    person_name=names[index],
                                    person_star=customer_star,
                                    quantity=1,
                                    price=price
                                )

                    if request.POST.getlist('thing[]'):
                        thing_names = request.POST.getlist('thing[]')
                        thing_quantities = request.POST.getlist('quantity[]')
                        thing_prices = request.POST.getlist('thing_price[]')

                        for index, thing_name in enumerate(thing_names):
                            if thing_name.strip():
                                inventory_item = get_object_or_404(
                                    InventoryItem, name=thing_name, temple=temple)
                                quantity = int(thing_quantities[index])
                                price = Decimal(thing_prices[index])

                                # Create a new bill for this inventory item
                                bill = Bill.objects.create(
                                    user=request.user,
                                    temple=temple,
                                    total_amount=price * quantity
                                )

                                # Create associated BillInventoryItem record
                                BillInventoryItem.objects.create(
                                    bill=bill,
                                    inventory_item=inventory_item,
                                    quantity=quantity,
                                    price=price
                                )

                    messages.success(request, "Separate bills have been successfully recorded.")
                    return redirect('bill-list')

                else:
                    # Create a single consolidated bill
                    total_pooja_price = sum(pooja_price_list)
                    total_thing_price = sum(thing_price_list)
                    bill = Bill.objects.create(
                        user=request.user,
                        temple=temple,
                        total_amount=Decimal(total_pooja_price + total_thing_price)
                    )

                    # Add offerings to the single bill
                    if request.POST.getlist('pooja[]'):
                        names = request.POST.getlist('name[]')
                        vazhipadu_list = request.POST.getlist('pooja[]')
                        stars = request.POST.getlist('nakshatram[]')
                        vazhipadu_prices = request.POST.getlist('pooja_price[]')

                        for index, vazhipadu_name in enumerate(vazhipadu_list):
                            if vazhipadu_name.strip():
                                vazhipadu_offering = get_object_or_404(
                                    VazhipaduOffering, name=vazhipadu_name, temple=temple)
                                price = Decimal(vazhipadu_prices[index])
                                customer_star = get_object_or_404(Star, name=stars[index])

                                BillVazhipaduOffering.objects.create(
                                    bill=bill,
                                    vazhipadu_offering=vazhipadu_offering,
                                    person_name=names[index],
                                    person_star=customer_star,
                                    quantity=1,
                                    price=price
                                )

                    # Add inventory items to the single bill
                    if request.POST.getlist('thing[]'):
                        thing_names = request.POST.getlist('thing[]')
                        thing_quantities = request.POST.getlist('quantity[]')
                        thing_prices = request.POST.getlist('thing_price[]')

                        for index, thing_name in enumerate(thing_names):
                            if thing_name.strip():
                                inventory_item = get_object_or_404(
                                    InventoryItem, name=thing_name, temple=temple)
                                quantity = int(thing_quantities[index])
                                price = Decimal(thing_prices[index])

                                BillInventoryItem.objects.create(
                                    bill=bill,
                                    inventory_item=inventory_item,
                                    quantity=quantity,
                                    price=price
                                )

                    messages.success(request, "Billing details have been successfully recorded.")
                    return redirect(reverse('bill-detail', kwargs={'pk': bill.id}))

        except Exception as e:
            # Rollback transaction on error
            messages.error(request, f"An error occurred while processing the billing: {e}")
            return redirect('add-bill')

    messages.error(request, "Invalid request method.")
    return redirect('add-bill')




class BillDetailView(LoginRequiredMixin, DetailView):
    model = Bill
    template_name = "billing_manager/bill_detail.html"
    context_object_name = "bill"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional data if necessary
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
            return ["billing_manager/receipt.html"]
        else:
            # Otherwise, return the standard receipt template
            return ["billing_manager/receipt.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Retrieve the current temple from the session
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        # Add any additional data if necessary
        context["temple"] = temple
        return context