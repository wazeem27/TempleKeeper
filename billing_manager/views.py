from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from .models import WalletCollection
from decimal import Decimal
import csv
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.http import JsonResponse, Http404
from .forms import WalletCollectionForm
from .services import WalletService
from django.http import HttpResponseForbidden
from django.core.exceptions import ValidationError
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
    paginate_by = 100


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
        requested_biller = self.request.GET.getlist('req_biller')


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
            bills = Bill.objects.filter(temple=temple, user=self.request.user).order_by('id')
            if start_date:
                bills = bills.filter(created_at__gte=start_date)
            if end_date:
                bills = bills.filter(created_at__lte=end_date)

        else:
            # All bills if not a Billing Assistant
            bills = Bill.objects.filter(temple=temple).order_by('id')
            if requested_biller:
                bills = bills.filter(user__username=requested_biller[0])

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
                    'payment_method': bill.payment_method,
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
                    'cancel_reason': bill.cancel_reason,
                    'payment_method': bill.payment_method

                }
                bill_dataset.append(bill_entry)       
                counter += 1     

        # Add paginated dataset and filters to the context
        req_vazhipadu = self.request.GET.getlist('req_vazhipadu')
        if req_vazhipadu:
            bill_dataset = [bill for bill in bill_dataset if bill["vazhipadu_name"] == req_vazhipadu[0]]

        vazhipadu_items = VazhipaduOffering.objects.filter(temple=temple).order_by('order')
        context["vazhipadu_items"] = [i.name for i in vazhipadu_items]


        context['bills'] = bill_dataset
        user_profiles = UserProfile.objects.filter(temples__id=temple_id)
        context['user_list'] = [usr_prof.user.username for usr_prof in user_profiles]
        context['search_query'] = self.request.GET.get('q', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['req_vazhipadu'] = req_vazhipadu[0] if req_vazhipadu else ""
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
            payment_method = request.POST.get('payment_method')
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
                                    total_amount=price,
                                    payment_method=payment_method
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
                        total_amount=Decimal(total_pooja_price + total_other_price),
                        payment_method=payment_method
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
                                    price=price,
                                    payment_method=payment_method
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
        
        bills = Bill.objects.all().order_by('id')

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


@login_required
def update_payment_method(request):
    """
    Update the payment method for a bill.
    Accepts either 'cash' or 'gpay' as valid payment methods.
    Ensures that if the payment method is 'gpay', the amount must equal the bill's total amount.
    """
    # Get the bill object by receipt number

    # Only process the form if it's a POST request
    if request.method == 'POST':
        bill_id = int(request.POST.get('bill_id'))
        bill = get_object_or_404(Bill, id=bill_id)
        # Get the new payment method from the POST data
        new_payment_method = request.POST.get('payment_method')
        online_payment_amount = request.POST.get('online_payment_amount')  # Assuming online amount is passed

        # Validate the payment method
        if new_payment_method not in ['Cash', 'Online']:
            raise ValidationError("Invalid payment method selected.")
        
        # If the payment method is 'gpay', validate that the online payment amount matches the total bill amount
        # if new_payment_method == 'Online'
        #     try:
        #         online_payment_amount = float(online_payment_amount)
        #     except ValueError:
        #         raise ValidationError("Invalid online payment amount.")

        #     if online_payment_amount != bill.total_amount:
        #         raise ValidationError("For Online method, the Online amount must equal the total amount.")

        # Update the bill's payment method and save the bill
        bill.payment_method = new_payment_method

        # If the payment method is 'gpay', save the online payment amount
        # if new_payment_method == 'Online':
            # bill.online_payment_amount = online_payment_amount

        bill.save()

        # Display success message and redirect to the receipt page
        messages.success(request, f"Payment method successfully updated to {new_payment_method.capitalize()}.")
        return redirect('bill-list')

    # If the request is not POST, just redirect to the bill's receipt page
    return redirect('receipt', receipt=bill.id)


class WalletCalendar(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/wallet_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temple_id = self.request.session.get('temple_id')
        collections = WalletCollection.objects.filter(user_id=self.request.user.id, temple_id=temple_id)
        wallet_dataset = []
        for collec in collections:
            data = {}
            data['start'] = collec.date.strftime("%Y-%m-%d")
            data['title'] = str(collec.counter_cash)
            wallet_dataset.append(data)
        
        context['events'] = wallet_dataset
        return context


class WalletCollectionCreateView(View):
    def get(self, request, *args, **kwargs):
        # Get the 'date' query parameter
        date = request.GET.get('date')

        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise Http404("Invalid date format")
        if not date:
            raise Http404("Date parameter is required")

        # Try to retrieve the existing WalletCollection for the provided date
        wallet_collection = WalletCollection.objects.filter(date=date).first()

        # If a WalletCollection exists for that date, populate the form with its data
        if wallet_collection:
            form = WalletCollectionForm(instance=wallet_collection)
        else:
            # Otherwise, create an empty form with default values
            form = WalletCollectionForm(initial={
                'counter_cash': 0,
                'coin_counts': {'1': 0, '2': 0, '5': 0, '10': 0, '20': 0},
                'note_counts': {'10': 0, '5': 0, '20': 0}
            })
        
        return render(request, 'billing_manager/interim.html', {'form': form, 'date': date})

    def post(self, request, *args, **kwargs):
        # Get the 'date' query parameter
        date = request.GET.get('date')
        temple_id = request.session.get('temple_id')
        if not date:
            raise Http404("Date parameter is required")

        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise Http404("Invalid date format")

        # Check if the WalletCollection for this date already exists
        wallet_collection = WalletCollection.objects.filter(date=date).first()

        # If a WalletCollection exists for that date, update it; otherwise, create a new one
        if wallet_collection:
            form = WalletCollectionForm(request.POST or None, instance=wallet_collection)
        else:
            form = WalletCollectionForm(request.POST or None)

        if request.method == 'POST':
            if form.is_valid():
                # Set the date explicitly on the form instance (whether it's a new or updated form)
                wallet_collection = form.save(commit=False)
                wallet_collection.date = date  # Ensure date is saved as well
                wallet_collection.temple_id = temple_id
                wallet_collection.user_id = request.user.id
                wallet_collection.save()
                return redirect('wallet-info')  # Redirect to the same page after saving, or you can redirect to another view

        return render(request, 'billing_manager/wallet_calendar.html', {'form': form, 'date': date})