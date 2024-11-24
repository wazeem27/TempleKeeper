from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
import csv
from datetime import datetime, time
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from collections import defaultdict
from django.utils.timezone import localtime
from billing_manager.models import Bill, BillOther, BillVazhipaduOffering
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
        """
        Returns a filtered queryset for the bills. This method is used to provide the base
        queryset for filtering but we will manually construct and paginate the dataset.
        """
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        # Get the filter parameters from the GET request
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')

        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None
        
        is_billing_assistant = self.request.user.groups.filter(name='Billing Assistant').exists()
        
        # Convert to timezone-aware datetime if needed
        if start_date:
            start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))  # 00:00:00
        if end_date:
            # Set end_date to the last moment of the day (23:59:59)
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59

        if is_billing_assistant:
            # Only bills related to the current user (Billing Assistant)
            bills = Bill.objects.filter(user=self.request.user).order_by('id')
            if start_date:
                bills = bills.filter(created_at__gte=start_date)
            if end_date:
                bills = bills.filter(created_at__lte=end_date)
        else:
            # All bills if not a Billing Assistant
            bills = Bill.objects.all().order_by('id')

            if start_date:
                bills = bills.filter(created_at__gte=start_date)
            if end_date:
                bills = bills.filter(created_at__lte=end_date)

        return bills


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get temple details
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple

        # Use paginated bills for the current page
        bill_dataset = []
        bills = []
        is_billing_assistant = self.request.user.groups.filter(name='Billing Assistant').exists()
        context['is_billing_assistant'] = is_billing_assistant

        
        for bill in context['bills']:
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
            counter = 0

            # Construct the dataset
            for vazhipadu_bill in vazhipadu_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]

                bill_entry = {
                    'receipt': bill.id,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': vazhipadu_bill.vazhipadu_offering.name,
                    'name': vazhipadu_bill.person_name,
                    'star': vazhipadu_bill.person_star.name if vazhipadu_bill.person_star else "",
                    'amount': vazhipadu_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'cancel_reason': bill.cancel_reason
                }
                bill_dataset.append(bill_entry)
                counter +=1
            other_list = bill.bill_other_items.all()
            # Construct the dataset
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]

                bill_entry = {
                    'receipt': bill.id,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': other_bill.vazhipadu,
                    'name': other_bill.person_name,
                    'star': other_bill.person_star.name if other_bill.person_star.name else "",
                    'amount': other_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'cancel_reason': bill.cancel_reason

                }
                bill_dataset.append(bill_entry)       
                counter += 1     

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
        other_price_list = list(map(float, request.POST.getlist('other_price[]')))


        # Retrieve user profile for split bill preference
        user_profile = get_object_or_404(UserProfile, user=request.user, temples__id=temple_id)

        # Begin transaction to ensure atomicity
        try:
            with transaction.atomic():
                if user_profile.is_split_bill:
                    # Create separate bills for each offering or item
                    bill_objects = []

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
                                bill_objects.append(bill)

                                # Create associated BillVazhipaduOffering record
                                BillVazhipaduOffering.objects.create(
                                    bill=bill,
                                    vazhipadu_offering=vazhipadu_offering,
                                    person_name=names[index],
                                    person_star=customer_star,
                                    quantity=1,
                                    price=price
                                )

                    if request.POST.getlist('other_name[]'):
                        other_names = request.POST.getlist('other_name[]')
                        other_stars = request.POST.getlist('other_nakshatram[]')
                        other_vazhipadugal = request.POST.getlist('other_vazhipadu[]')
                        other_prices = request.POST.getlist('other_price[]')

                        for index, other_name in enumerate(other_names):
                            if other_name.strip():
                                other_star = get_object_or_404(Star, name=other_stars[index])
                                vazhipadu = other_vazhipadugal[index]
                                price = Decimal(other_prices[index])

                                # Create a new bill for this inventory item
                                bill = Bill.objects.create(
                                    user=request.user,
                                    temple=temple,
                                    total_amount=price
                                )
                                bill_objects.append(bill)

                                # Create associated BillInventoryItem record
                                BillOther.objects.create(
                                    bill=bill,
                                    person_name=other_name,
                                    person_star=other_star,
                                    vazhipadu=vazhipadu,
                                    price=price
                                )
                    bill_ids = ",".join([str(bill.id) for bill in bill_objects])
                    for bill in bill_objects:
                        bill.related_bills = bill_ids
                        bill.save()

                    messages.success(request, "Separate bills have been successfully recorded.")
                    query_string = f"ids={'&'.join(map(str, [bill.id for bill in bill_objects]))}"
                    url = f"{reverse('view_multi_receipt')}?{query_string}"
                    return redirect(url)

                else:
                    # Create a single consolidated bill
                    total_pooja_price = sum(pooja_price_list)
                    total_other_price = sum(other_price_list)
                    bill = Bill.objects.create(
                        user=request.user,
                        temple=temple,
                        total_amount=Decimal(total_pooja_price + total_other_price)
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
                    if request.POST.getlist('other_name[]'):
                        other_names = request.POST.getlist('other_name[]')
                        other_stars = request.POST.getlist('other_nakshatram[]')
                        other_vazhipadugal = request.POST.getlist('other_vazhipadu[]')
                        other_prices = request.POST.getlist('other_price[]')

                        for index, other_name in enumerate(other_names):
                            if other_name.strip():
                                other_star = get_object_or_404(Star, name=other_stars[index])
                                vazhipadu = other_vazhipadugal[index]
                                price = Decimal(other_prices[index])

                                BillOther.objects.create(
                                    bill=bill,
                                    person_name=other_name,
                                    person_star=other_star,
                                    vazhipadu=vazhipadu,
                                    price=price
                                )

                    messages.success(request, "Billing details have been successfully recorded.")
                    return redirect(reverse('receipt', kwargs={'pk': bill.id}))

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



class ViewMultiReceipt(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/new_bill_receipt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch the temple based on session data
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple

        # Get the list of bill IDs from query parameters
        query_string = self.request.META.get('QUERY_STRING', '')
        bill_ids = query_string.split('=')[1].split('&') if '=' in query_string else []
        # Fetch bills belonging to the temple
        bills = Bill.objects.filter(id__in=bill_ids, temple_id=temple_id)
        bill_list = []
        for bill in bills:
            bill_dict = {}
            bill_dict['id'] = bill.id
            bill_dict['date'] = bill.created_at
            vazhipadu = bill.bill_vazhipadu_offerings.first()
            if vazhipadu:
                bill_dict['name'] = vazhipadu.person_name
                bill_dict['star'] = vazhipadu.person_star
                bill_dict['vazhipadu'] = vazhipadu.vazhipadu_offering.name
                bill_dict['price'] = vazhipadu.price
                bill_list.append(bill_dict)
            else:
                other = bill.bill_other_items.first()
                bill_dict['name'] = other.person_name
                bill_dict['star'] = other.person_star.name
                bill_dict['vazhipadu'] = other.vazhipadu
                bill_dict['price'] = other.price
                bill_list.append(bill_dict)  
                
        context['bills'] = bill_list

        return context



class BillExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Get filter parameters from the request
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        search_query = request.GET.get('q', '')

        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

        # Filter bills based on the same logic as the get_queryset method
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()
        
        bills = Bill.objects.all()

        if is_billing_assistant:
            bills = bills.filter(user=request.user)
        
        if start_date:
            bills = bills.filter(created_at__gte=start_date)
        if end_date:
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59
            bills = bills.filter(created_at__lte=end_date)

        # Prepare the CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bills_export.csv"'

        writer = csv.writer(response)
        
        # Write the header row
        writer.writerow([
            'Receipt ID', 'Sub Receipt', 'Created At', 'Created By', 
            'Vazhipadu Name', 'Name', 'Star', 'Amount'
        ])

        # Write the data rows
        sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
        for bill in bills:
            counter = 0
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            
            for vazhipadu_bill in vazhipadu_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.id,
                    subreceipt,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    bill.user.username,
                    vazhipadu_bill.vazhipadu_offering.name,
                    vazhipadu_bill.person_name,
                    vazhipadu_bill.person_star.name if vazhipadu_bill.person_star else "",
                    vazhipadu_bill.price,
                ])
                counter += 1

            other_list = bill.bill_other_items.all()
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.id,
                    subreceipt,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    bill.user.username,
                    other_bill.vazhipadu,
                    other_bill.person_name,
                    other_bill.person_star.name if other_bill.person_star else "",
                    other_bill.price,
                ])
                counter += 1

        return response


@login_required
def cancel_bill(request, bill_id):
    if request.method == "POST":
        bill_id = int(request.POST.get('bill_id'))
        reason = request.POST.get("reason")
        if not request.user.groups.filter(name='Temple Admin').exists() and not request.user.groups.filter(name='Central Admin').exists() :
            messages.error(request, "You dont have privilege to cancel the bill.")
            return redirect("bill-list")

        try:
            bill = Bill.objects.get(id=bill_id)

            # Update the cancellation status and reason
            bill.is_cancelled = True
            bill.cancel_reason = reason if reason else ""
            bill.save()

            messages.success(request, f"Bill with Rceipt No: {bill.id} was successfully cancelled.")

        except Bill.DoesNotExist:
            messages.error(request, "The bill does not exist.")

    return redirect("bill-list")  # Replace with the desired redirect URL