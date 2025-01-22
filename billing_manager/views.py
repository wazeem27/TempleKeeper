from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from .models import WalletCollection
from decimal import Decimal
import csv
import re
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.http import JsonResponse, Http404
from django.http import HttpResponseBadRequest
from .forms import WalletCollectionForm, ExpenseForm
from .services import WalletService
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseForbidden
from django.core.exceptions import ValidationError
from datetime import datetime, time, date
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from collections import defaultdict
from django.utils.timezone import localtime
from billing_manager.models import Bill, BillOther, BillVazhipaduOffering, PersonDetail, Expense
from typing import Dict, Any
from temple_auth.models import UserProfile
from django.db.models import Sum
from django.utils.dateformat import DateFormat
from billing_manager.decorators import check_temple_session
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from math import ceil

subreceipt_ids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']


@method_decorator(check_temple_session, name='dispatch')
class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/create_bill.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple, is_deleted=False).order_by('order')

    def get_star_queryset(self) -> Any:
        return Star.objects.all().order_by('order')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        
        context['vazhipadu_items'] = self.get_vazhipadu_queryset(temple)
        context['inventory_items'] = self.get_inventory_queryset(temple)
        context['star_items'] = self.get_star_queryset()
        context['temple'] = temple

        multi_support_vazhipadu = [
            vazhipadu.name for vazhipadu in
            VazhipaduOffering.objects.filter(temple=temple, allow_multiple=True, is_deleted=False)
        ]
        context['multi_support_vazhipadu'] = multi_support_vazhipadu
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user is in the 'Central Admin' group
        if request.user.groups.filter(name='Central Admin').exists():
            # Redirect to a different view, for example, to the home page
            return redirect('dashboard')  # Or the URL name of the redirect target
        return super().dispatch(request, *args, **kwargs)


@method_decorator(check_temple_session, name='dispatch')
class BillListView(LoginRequiredMixin, ListView):
    model = Bill
    template_name = 'billing_manager/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 100

    def get(self, request, *args, **kwargs):
        """
        Override the get method to redirect to the last page if 'page' is not specified.
        """
        # Get the total number of bills
        total_bills = self.get_queryset().count()
        if total_bills == 0:
            # If no bills, render the default view
            return super().get(request, *args, **kwargs)

        # Calculate the last page number
        last_page = (total_bills + self.paginate_by - 1) // self.paginate_by  # Ceiling division

        if (
            request.GET.get('start_date') or 
            request.GET.get('end_date') or
            request.GET.get('req_biller') or 
            request.GET.get('req_vazhipadu')
        ):
            return super().get(request, *args, **kwargs)

        # Check if the 'page' parameter is already set
        if not request.GET.get('page'):
            # Redirect to the last page
            url = f"{request.path}?page={last_page}"
            return HttpResponseRedirect(url)

        # Render the page normally if 'page' is set
        return super().get(request, *args, **kwargs)

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
            bills = Bill.objects.filter(temple=temple).order_by('receipt_number')
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
            other_list = bill.bill_other_items.all()
            sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
            counter = 0

            # Construct the dataset
            for vazhipadu_bill in vazhipadu_list:
                subreceipt = '-' if len(vazhipadu_list) + len(other_list) == 1 else sub_receipt_counter[counter]
                vazhipadu_name = vazhipadu_bill.vazhipadu_offering.name
                if vazhipadu_bill.vazhipadu_offering.is_deleted:
                    vazhipadu_name = vazhipadu_name[:vazhipadu_name.rfind('_')]
                
                advance_date = ""
                if bill.advance_booking_date:
                    advance_date = bill.advance_booking_date.strftime("%d-%m-%Y")
                
                bill_entry = {
                    'id': str(bill.id),
                    'is_advance_booking': bill.advance_booking,
                    'receipt': bill.receipt_number,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%d-%m-%Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': vazhipadu_name,
                    'name': ",".join([vazhipadu.person_name for vazhipadu in vazhipadu_bill.person_details.all()]),
                    'star': ",".join([vazhipadu.person_star.name for vazhipadu in vazhipadu_bill.person_details.all()]),
                    'amount': vazhipadu_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'payment_method': bill.payment_method,
                    'cancel_reason': bill.cancel_reason,
                    'advance_date': advance_date
                }
                bill_dataset.append(bill_entry)
                counter +=1
            
            # Construct the dataset
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) + len(other_list) == 1 else sub_receipt_counter[counter]
                advance_date = ""
                if bill.advance_booking_date:
                    advance_date = bill.advance_booking_date.strftime("%d-%m-%Y")
                bill_entry = {
                    'id': str(bill.id),
                    'receipt': bill.receipt_number,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%d-%m-%Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': other_bill.vazhipadu,
                    'name': other_bill.person_name,
                    'star': other_bill.person_star.name if other_bill.person_star.name else "",
                    'amount': other_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'cancel_reason': bill.cancel_reason,
                    'payment_method': bill.payment_method,
                    'advance_date':  advance_date

                }
                bill_dataset.append(bill_entry)       
                counter += 1     

        # Add paginated dataset and filters to the context
        req_vazhipadu = self.request.GET.getlist('req_vazhipadu')
        if req_vazhipadu:
            bill_dataset = [bill for bill in bill_dataset if bill["vazhipadu_name"] == req_vazhipadu[0]]
        
        vazhipadu_items_list = []
        vazhipadu_items = VazhipaduOffering.objects.filter(temple=temple).order_by('order')
        for item in vazhipadu_items:
            if item.is_deleted:
                vazhipadu_items_list.append(item.name[:item.name.rfind('_')])
            else:
                vazhipadu_items_list.append(item.name)

        context["vazhipadu_items"] = vazhipadu_items_list


        context['bills'] = sorted(bill_dataset, key=lambda x: (x["receipt"], x["sub_receipt"]))
        user_profiles = UserProfile.objects.filter(temples__id=temple_id)
        user_profiles = [user for user in user_profiles if not user.user.groups.filter(name='Central Admin').exists()]
        context['user_list'] = [usr_prof.user.username for usr_prof in user_profiles]
        context['search_query'] = self.request.GET.get('q', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['req_vazhipadu'] = req_vazhipadu[0] if req_vazhipadu else ""
        context['end_date'] = self.request.GET.get('end_date', '')
        context['grand_total'] = sum([bill.get('amount', 0) for bill in bill_dataset])
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context["is_central_admin"] = is_central_admin
        context["temple"] = temple
        return context


def parse_nested_querydict(querydict):
    data = querydict.dict()  # Converts QueryDict to a dictionary
    result = {
        "parents": [],
        "payment_method": querydict.get("payment_method", ""),
        "gap_amount": querydict.get("gap_amount", ""),
    }

    # Regex to identify parent keys and child keys
    parent_regex = re.compile(r"parent\[(\d+)\]\[([^\]]+)\]")  # e.g., parent[1][name]
    child_regex = re.compile(r"parent\[(\d+)\]\[children\]\[(\d+)\]\[([^\]]+)\]")  # e.g., parent[1][children][2][name]

    # Containers for parent and child data
    parents = defaultdict(dict)
    children = defaultdict(lambda: defaultdict(dict))  # {parent_id: {child_id: {child_data}}}

    for key, value in data.items():
        # Match parent fields
        parent_match = parent_regex.match(key)
        if parent_match:
            parent_id, field = parent_match.groups()
            parents[parent_id][field] = value

        # Match child fields
        child_match = child_regex.match(key)
        if child_match:
            parent_id, child_id, field = child_match.groups()
            children[parent_id][child_id][field] = value

    # Combine parents and their respective children
    for parent_id, parent_data in parents.items():
        parent_data["children"] = list(children[parent_id].values())
        result["parents"].append(parent_data)

    return result




@method_decorator(check_temple_session, name='dispatch')
class SubmitBill(LoginRequiredMixin, View):
    template_name = "bill/create_bill.html"

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:

            is_central_admin = request.user.groups.filter(name='Central Admin').exists()
            if is_central_admin:
                return redirect('dashboard')

            # Parse and validate input data
            data = parse_nested_querydict(request.POST)
            temple = self._get_temple(request.session)
            parents = self._validate_parents_data(data)
            other_bills = self.validate_other_data(request.POST)

            # Calculate total price
            total_price = sum(float(parent["price"]) * int(parent["quantity"]) for parent in parents)
            
            total_price += float(sum([other['other_price'] for other in other_bills]))


            user_profile = get_object_or_404(UserProfile, user=request.user, temples__id=temple.id)

            if user_profile.is_split_bill:
                person_details = []  # Collect all PersonDetail objects for bulk creation
                # Create separate bills for each offering or item
                bill_objects = []

                for parent in parents:
                    bill = self._create_bill(request, temple, float(parent.get('price')), data.get("payment_method", "cash"))
                    if request.POST.get('advance_booking_date'):
                        # if advance booking date is thr flag this as advance booking
                        # Get the date string from request
                        date_string = request.POST.get('advance_booking_date')  # Example: '2025-01-23'

                        # Convert the string to a date object
                        advance_booking_date = datetime.strptime(date_string, '%Y-%m-%d').date()
                        bill.advance_booking_date = advance_booking_date
                        bill.mobile_number = request.POST.get('mobile_number',"")
                        bill.advance_booking = True
                        bill.is_completed = False
                    bill.save()
                    bill_objects.append(bill)
                    # Save BillVazhipaduOffering (cannot use bulk_create due to unsaved related object)
                    vazhipadu_offering = get_object_or_404(
                        VazhipaduOffering, name=parent["pooja"], temple=temple
                    )
                    # Save vazhipadu offering
                    vazhipadu_bill = BillVazhipaduOffering.objects.create(
                        bill=bill,
                        vazhipadu_offering=vazhipadu_offering,
                        quantity=int(parent["quantity"]),
                        price=parent["price"]
                    )
                    # Add parent person detail
                    person_details.append(
                        PersonDetail(
                            bill_vazhipadu_offering=vazhipadu_bill,
                            person_name=parent["name"],
                            person_star=get_object_or_404(Star, name=parent["nakshatram"])
                        )
                    )

                    # Add child person details
                    for child in parent.get("children", []):
                        person_details.append(
                            PersonDetail(
                                bill_vazhipadu_offering=vazhipadu_bill,
                                person_name=child["name"],
                                person_star=get_object_or_404(Star, name=child["nakshatram"])
                            )
                        )
                # Bulk create PersonDetail objects
                if person_details:
                    PersonDetail.objects.bulk_create(person_details)

                for other in other_bills:
                    bill = self._create_bill(request, temple, float(other.get('other_price')), data.get("payment_method", "cash"))
                    if request.POST.get('advance_booking_date'):
                        # if advance booking date is thr flag this as advance booking
                        # Get the date string from request
                        date_string = request.POST.get('advance_booking_date')  # Example: '2025-01-23'

                        # Convert the string to a date object
                        advance_booking_date = datetime.strptime(date_string, '%Y-%m-%d').date()
                        bill.advance_booking_date = advance_booking_date
                        bill.mobile_number = request.POST.get('mobile_number',"")
                        bill.advance_booking = True
                        bill.is_completed = False
                    bill.save()
                    bill_objects.append(bill)

                    name = other.get("other_name")
                    other_star = get_object_or_404(Star, name=other.get("other_nakshatram"))
                    price = other.get("other_price")
                    vazhipadu = other.get("other_vazhipadu")
                    BillOther.objects.create(
                        bill=bill, person_name=name, 
                        person_star=other_star, vazhipadu=vazhipadu,
                        price=price
                    )


                bill_ids = ",".join([str(bill.id) for bill in bill_objects])
                for bill in bill_objects:
                    bill.related_bills = bill_ids
                    bill.save()

                query_string = f"ids={'&'.join(map(str, [bill.id for bill in bill_objects]))}"
                url = f"{reverse('view_multi_receipt')}?{query_string}"
                return redirect(url)
                
            else:
                # Step 1: Create the main bill
                bill = self._create_bill(request, temple, total_price, data.get("payment_method", "cash"))
                if request.POST.get('advance_booking_date'):
                    # if advance booking date is thr flag this as advance booking
                    # Get the date string from request
                    date_string = request.POST.get('advance_booking_date')  # Example: '2025-01-23'

                    # Convert the string to a date object
                    advance_booking_date = datetime.strptime(date_string, '%Y-%m-%d').date()
                    bill.advance_booking_date = advance_booking_date
                    bill.mobile_number = request.POST.get('mobile_number',"")
                    bill.advance_booking = True
                    bill.is_completed = False
                bill.save()

                # Step 2: Process VazhipaduOfferings and PersonDetails
                person_details = []  # Collect all PersonDetail objects for bulk creation
                for parent in parents:
                    vazhipadu_offering = get_object_or_404(
                        VazhipaduOffering, name=parent["pooja"], temple=temple
                    )

                    # Save BillVazhipaduOffering (cannot use bulk_create due to unsaved related object)
                    vazhipadu_bill = BillVazhipaduOffering.objects.create(
                        bill=bill,
                        vazhipadu_offering=vazhipadu_offering,
                        quantity=int(parent["quantity"]),
                        price=parent["price"]
                    )

                    # Add parent person detail
                    person_details.append(
                        PersonDetail(
                            bill_vazhipadu_offering=vazhipadu_bill,
                            person_name=parent["name"],
                            person_star=get_object_or_404(Star, name=parent["nakshatram"])
                        )
                    )

                    # Add child person details
                    for child in parent.get("children", []):
                        person_details.append(
                            PersonDetail(
                                bill_vazhipadu_offering=vazhipadu_bill,
                                person_name=child["name"],
                                person_star=get_object_or_404(Star, name=child["nakshatram"])
                            )
                        )

                # Bulk create PersonDetail objects
                if person_details:
                    PersonDetail.objects.bulk_create(person_details)

                for other in other_bills:
                    name = other.get("other_name")
                    other_star = get_object_or_404(Star, name=other.get("other_nakshatram"))
                    price = other.get("other_price")
                    vazhipadu = other.get("other_vazhipadu")
                    BillOther.objects.create(
                        bill=bill, person_name=name, 
                        person_star=other_star, vazhipadu=vazhipadu,
                        price=price
                    )
                # Return success response
                return redirect(reverse('receipt', kwargs={'pk': bill.id}))

        except ValidationError as e:
            return JsonResponse({"status": "failure", "error": str(e)}, status=400)
        except ObjectDoesNotExist as e:
            return JsonResponse({"status": "failure", "error": f"Data not found: {str(e)}"}, status=404)
        except Exception as e:
            # Log error for internal debugging
            return JsonResponse({"status": "failure", "error": f"An unexpected error occurred: {str(e)}"}, status=500)

    def _get_temple(self, session):
        temple_id = session.get("temple_id")
        if not temple_id:
            raise ValidationError("Temple ID is missing from the session.")
        return get_object_or_404(Temple, id=temple_id)

    def _validate_parents_data(self, data):
        parents = data.get("parents", [])
        if not parents:
            return []
        for parent in parents:
            if "pooja" not in parent or "price" not in parent or "name" not in parent or "nakshatram" not in parent:
                raise ValidationError("Each parent must include 'pooja', 'price', 'name', and 'nakshatram' fields.")
            if "children" in parent:
                for child in parent["children"]:
                    if "name" not in child or "nakshatram" not in child:
                        raise ValidationError("Each child must include 'name' and 'nakshatram' fields.")
        return parents

    def _create_bill(self, request, temple, total_price, payment_method):
        if total_price <= 0:
            raise ValidationError("Total price must be greater than zero.")
        return Bill(
            user=request.user,
            temple=temple,
            total_amount=Decimal(total_price),
            payment_method=payment_method
        )


    def validate_other_data(self, querydict):
        required_fields = ['other_name[]', 'other_nakshatram[]', 'other_vazhipadu[]', 'other_price[]']

        # Extract values
        other_names = querydict.getlist('other_name[]')
        other_nakshatrams = querydict.getlist('other_nakshatram[]')
        other_vazhipadus = querydict.getlist('other_vazhipadu[]')
        other_prices = querydict.getlist('other_price[]')

        # Ensure consistent lengths across all fields
        if not (len(other_names) == len(other_nakshatrams) == len(other_vazhipadus) == len(other_prices)):
            raise ValidationError("Inconsistent number of items between fields.")

        # Validate and construct the processed data
        processed_data = []
        for name, nakshatram, vazhipadu, price in zip(other_names, other_nakshatrams, other_vazhipadus, other_prices):
            try:
                price_decimal = Decimal(price)
            except:
                raise ValidationError(f"Invalid price value: {price}")

            processed_data.append({
                'other_name': name,
                'other_nakshatram': nakshatram,
                'other_vazhipadu': vazhipadu,
                'other_price': price_decimal,
            })

        return processed_data


@method_decorator(check_temple_session, name='dispatch')
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
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context["is_central_admin"] = is_central_admin
        return context


@method_decorator(check_temple_session, name='dispatch')
class ReceiptView(LoginRequiredMixin, DetailView):
    model = Bill
    context_object_name = "bill"

    def get_template_names(self):
        # Retrieve the current user profile
        user_profile = UserProfile.objects.filter(user=self.request.user)[0]
        if user_profile.is_split_bill:
            # If the user has selected split billing, return the split receipt template
            return ["billing_manager/receipt_template_2.html"]
        else:
            # Otherwise, return the standard receipt template
            return ["billing_manager/receipt_template_2.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Retrieve the current temple from the session
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple

        bill_detail = {"total_amount": self.get_object().total_amount, "vazhipadu_list": []}
        
        for vazhipadu in self.get_object().bill_vazhipadu_offerings.all():
            vazhipadu_name = vazhipadu.vazhipadu_offering.name
            if vazhipadu.vazhipadu_offering.is_deleted:
                vazhipadu_name = vazhipadu_name[:vazhipadu_name.rfind('_')]
            vazhipadu_detail = {
                "vazhipadu": vazhipadu_name,
                "price": vazhipadu.vazhipadu_offering.price,
                "quantity": vazhipadu.quantity,
                "primary_person": None,
                "other_persons": []
            }
            
            # Retrieve all person details for the current vazhipadu
            persons = vazhipadu.person_details.all()
            
            # Separate the first person from the rest
            if persons.exists():
                first_person = persons[0]
                vazhipadu_detail["primary_person"] = {
                    "name": first_person.person_name,
                    "star": first_person.person_star.name
                }
                
                # Handle the remaining persons
                for person in persons[1:]:
                    vazhipadu_detail["other_persons"].append({
                        "name": person.person_name,
                        "star": person.person_star.name
                    })
            
            bill_detail["vazhipadu_list"].append(vazhipadu_detail)
        
        context["bill_detail"] = bill_detail
        return context


@method_decorator(check_temple_session, name='dispatch')
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
        bill_ids = query_string.split('=')[1].split(',') if '=' in query_string else []
        bill_ids = bill_ids[0].split('&')

        # Fetch bills belonging to the temple
        bills = Bill.objects.filter(id__in=bill_ids, temple_id=temple_id)
        bill_list = []

        for bill in bills:
            bill_dict = {
                "receipt_number": bill.receipt_number,
                "date": bill.created_at,
                "vazhipadu_list": []
            }

            # Add vazhipadu offerings for the bill
            for vazhipadu in bill.bill_vazhipadu_offerings.all():
                vazhipadu_name = vazhipadu.vazhipadu_offering.name
                if vazhipadu.vazhipadu_offering.is_deleted:
                    vazhipadu_name = vazhipadu_name[:vazhipadu_name.rfind('_')]
                vazhipadu_detail = {
                    "vazhipadu": vazhipadu_name,
                    "price": float(vazhipadu.vazhipadu_offering.price),
                    "quantity": int(vazhipadu.quantity),
                    "total_price": float(vazhipadu.vazhipadu_offering.price) * int(vazhipadu.quantity),
                    "primary_person": None,
                    "other_persons": []
                }

                bill_dict['total_amount'] = vazhipadu.vazhipadu_offering.price * vazhipadu.quantity

                # Fetch person details
                persons = vazhipadu.person_details.all()
                if persons.exists():
                    # Separate the first person
                    first_person = persons[0]
                    vazhipadu_detail["primary_person"] = {
                        "name": first_person.person_name,
                        "star": first_person.person_star.name
                    }
                    # Add remaining persons
                    for person in persons[1:]:
                        vazhipadu_detail["other_persons"].append({
                            "name": person.person_name,
                            "star": person.person_star.name
                        })

                bill_dict["vazhipadu_list"].append(vazhipadu_detail)

            # If no vazhipadu offerings, handle other items
            if not bill.bill_vazhipadu_offerings.exists():
                for other_item in bill.bill_other_items.all():
                    if isinstance(other_item, BillOther):
                        other_detail = {
                            "vazhipadu": other_item.vazhipadu,
                            "price": other_item.price,
                            "quantity": 1,
                            "primary_person": {
                                "name": other_item.person_name,
                                "star": other_item.person_star.name
                            },
                            "other_persons": []              
                        }
                        bill_dict['total_amount'] = other_item.price
                    else:
                        other_detail = {
                            "vazhipadu": other_item.vazhipadu,
                            "price": other_item.price,
                            "quantity": other_item.quantity,
                            "primary_person": {
                                "name": other_item.person_name,
                                "star": other_item.person_star.name
                            },
                            "other_persons": []
                        }
                    bill_dict["vazhipadu_list"].append(other_detail)
                    

            bill_list.append(bill_dict)

        context['bills'] = bill_list
        return context


@method_decorator(check_temple_session, name='dispatch')
class BillExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Get filter parameters from the request
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        search_query = request.GET.get('q', '')

        # Get the current date and time
        current_datetime = datetime.now()

        # Format it as a string including seconds
        formatted_datetime = current_datetime.strftime('%Y-%m-%d_%H:%M:%S')

        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

        # Filter bills based on the same logic as the get_queryset method
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()
        
        bills = Bill.objects.filter(temple=temple).order_by('receipt_number')

        if is_billing_assistant:
            bills = bills.filter(user=request.user)
        
        if start_date:
            bills = bills.filter(created_at__gte=start_date)
        if end_date:
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59
            bills = bills.filter(created_at__lte=end_date)

        # Prepare the CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="bills_export_{formatted_datetime}.csv"'

        writer = csv.writer(response)
        
        # Write the header row
        writer.writerow([
            'Receipt No', 'Sub Receipt', 'Date',
            'Vazhipadu', 'Customer Name', 'Star', 'Price', "Payment Method",
            "Advance Booking", 'Billed By', 'Reason',
        ])

        # Write the data rows
        sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
        for bill in bills.order_by('receipt_number'):
            counter = 0
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            
            for vazhipadu_bill in vazhipadu_list:

                vazhipadu_name = vazhipadu_bill.vazhipadu_offering.name
                if vazhipadu_bill.vazhipadu_offering.is_deleted:
                    vazhipadu_name = vazhipadu_name[:vazhipadu_name.rfind('_')]

                person_details = vazhipadu_bill.person_details.all()
                names = ",".join([person.person_name for person in person_details])
                stars = ",".join([star.person_star.name for star in person_details])
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.receipt_number,
                    subreceipt,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    vazhipadu_name,
                    names,
                    stars,
                    vazhipadu_bill.price,
                    bill.payment_method,
                    bill.advance_booking_date,
                    bill.user.username,
                    bill.cancel_reason,

                ])
                counter += 1

            other_list = bill.bill_other_items.all()
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) + len(other_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.receipt_number,
                    subreceipt,
                    bill.user.username,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    other_bill.vazhipadu,
                    other_bill.person_name,
                    other_bill.person_star.name if other_bill.person_star else "",
                    other_bill.price,
                    bill.advance_booking_date,
                    bill.payment_method,
                    bill.cancel_reason,
                ])
                counter += 1

        return response


@login_required
@check_temple_session
def cancel_bill(request, bill_id):
    if request.method == "POST":
        bill_id = request.POST.get('bill_id')
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

            messages.success(request, f"Bill with Rceipt No: {bill.receipt_number} was successfully cancelled.")

        except Bill.DoesNotExist:
            messages.error(request, "The bill does not exist.")

    return redirect("bill-list")  # Replace with the desired redirect URL


@login_required
@check_temple_session
def update_payment_method(request):
    """
    Update the payment method for a bill.
    Accepts either 'cash' or 'gpay' as valid payment methods.
    Ensures that if the payment method is 'gpay', the amount must equal the bill's total amount.
    """
    # Get the bill object by receipt number

    # Only process the form if it's a POST request
    if request.method == 'POST':
        bill_id = request.POST.get('bill_id')
        bill = get_object_or_404(Bill, id=bill_id)
        # Get the new payment method from the POST data
        new_payment_method = request.POST.get('payment_method')
        online_payment_amount = request.POST.get('online_payment_amount')  # Assuming online amount is passed

        # Validate the payment method
        if new_payment_method not in ['Cash', 'Online', "Both", "Not Paid"]:
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


@method_decorator(check_temple_session, name='dispatch')
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
            data['title'] = str(collec.__sum__())
            wallet_dataset.append(data)
        
        context['events'] = wallet_dataset
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context["is_central_admin"] = is_central_admin
        return context


@method_decorator(check_temple_session, name='dispatch')
class WalletCollectionCreateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Get the 'date' query parameter
        date = request.GET.get('date')
        temple_id = self.request.session.get('temple_id')


        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise Http404("Invalid date format")
        if not date:
            raise Http404("Date parameter is required")

        # Try to retrieve the existing WalletCollection for the provided date
        wallet_collection = WalletCollection.objects.filter(date=date, temple=temple_id, user=self.request.user).first()
        coin_list = [1, 2, 5, 10, 20]
        note_list = [1, 5, 10, 20, 50, 100, 200, 500]

        # Initialize default data with 0
        initial_coin_data = {f"coin_{denomination}": 0 for denomination in coin_list}
        initial_note_data = {f"note_{denomination}": 0 for denomination in note_list}

        # If a WalletCollection exists for that date, populate the form with its data
        if wallet_collection:
            for coin in coin_list:
                field_name = f"coin_{coin}"
                initial_coin_data[field_name] = getattr(wallet_collection, field_name, 0)

            for note in note_list:
                field_name = f"note_{note}"
                initial_note_data[field_name] = getattr(wallet_collection, field_name, 0)

        # Combine the initial coin and note data
        initial_data = {**initial_coin_data, **initial_note_data}
        is_central_admin = request.user.groups.filter(name='Central Admin').exists()
        temple = get_object_or_404(Temple, id=temple_id)
        # Pass data to the context
        context = {
            'coin_list': coin_list,
            'note_list': note_list,
            'initial_data': initial_data,
            'date': date.strftime("%d-%m-%Y"),
            'is_central_admin': is_central_admin,
            'temple': temple
        }
        return render(request, 'billing_manager/interim.html', context)

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
        wallet_collection = WalletCollection.objects.filter(date=date, user=self.request.user, temple=temple_id).first()

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


@method_decorator(check_temple_session, name='dispatch')
class WalletOveralCollectionCalendar(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/wallet_overall_calendar.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temple_id = self.request.session.get('temple_id')
        date = self.request.GET.get('date')
        collections = WalletCollection.objects.filter(temple_id=temple_id).exclude(user__username="central_admin")

        # Group by date and sum the amounts for each date
        date_grouped_data = defaultdict(int)
        for collec in collections:
            date_str = collec.date.strftime("%Y-%m-%d")
            # Sum the values for each date
            date_grouped_data[date_str] += collec.__sum__()

        # Prepare the dataset for the calendar
        wallet_dataset = []
        for date, total in date_grouped_data.items():
            data = {
                'start': date,
                'title': str(total)  # Total amount for that date
            }
            wallet_dataset.append(data)

        context['events'] = wallet_dataset
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context["is_central_admin"] = is_central_admin
        return context


@method_decorator(check_temple_session, name='dispatch')
class WalletOveralCollectionView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/overall_wallet.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the date parameter from the URL query string
        date = self.request.GET.get('date')
        temple_id = self.request.session.get('temple_id')

        try:
            # Try to parse the date parameter
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise Http404("Invalid date format")
        
        if not date:
            raise Http404("Date parameter is required")

        # Fetch all WalletCollections for the given date and temple
        collections = WalletCollection.objects.filter(date=date, temple_id=temple_id)
        
        # Fetch user profiles associated with the temple
        user_profiles = UserProfile.objects.filter(temples__id=temple_id)

        # Denominations for coins and notes
        coin_list = [1, 2, 5, 10, 20]
        note_list = [1, 5, 10, 20, 50, 100, 200, 500]

        wallet_details = []

        # Initialize accumulators for total sums
        total_coin_sum = 0
        total_note_sum = 0

        # Iterate over all user profiles for the temple
        user_exp_detail = {}
        for profile in user_profiles:
            if profile.user.username == 'central_admin':
                continue
            total = 0
            user_coin_sum = 0
            user_note_sum = 0
            # Initialize wallet data with default 0 for each coin and note
            wallet_coin = {f"{denomination}": {"count": 0, "value": 0} for denomination in coin_list}
            wallet_note = {f"{denomination}": {"count": 0, "value": 0} for denomination in note_list}
            
            # Get all collections for this user on the specific date
            user_collection = collections.filter(user=profile.user).first()

            if user_collection:
                for coin in coin_list:
                    field_name = f"coin_{coin}"
                    count = getattr(user_collection, field_name, 0)
                    wallet_coin[f"{coin}"]["count"] = count
                    wallet_coin[f"{coin}"]["value"] = int(count) * int(coin)
                    total_coin_sum += wallet_coin[f"{coin}"]["value"]
                    user_coin_sum += wallet_coin[f"{coin}"]["value"]

                for note in note_list:
                    field_name = f"note_{note}"
                    count = getattr(user_collection, field_name, 0)
                    wallet_note[f"{note}"]["count"] = count
                    wallet_note[f"{note}"]["value"] = int(count) * int(note)
                    total_note_sum += wallet_note[f"{note}"]["value"]
                    user_note_sum += wallet_note[f"{note}"]["value"]

                total = user_collection.__sum__()

            # Add the total sum to the wallet data for the user
            wallet_details.append({
                'username': profile.user.username,
                'wallet_coin': wallet_coin,
                'wallet_note': wallet_note,
                'sum': total,
                'coin_value': user_coin_sum,
                'note_value': user_note_sum
            })
        
        # Add the wallet details and total sums to the context
        context['wallet_details'] = wallet_details
        context['total_coin_sum'] = total_coin_sum
        context['total_note_sum'] = total_note_sum
        context['total'] = total_coin_sum + total_note_sum
        context['date'] = date
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context["is_central_admin"] = is_central_admin
        return context



@method_decorator(check_temple_session, name='dispatch')
class ExpenseView(LoginRequiredMixin, View):
    template_name = 'billing_manager/expense_list.html'

    def get(self, request, *args, **kwargs):
        """
        Handle GET request to list all expenses for the logged-in user.
        """
        date = request.GET.get('date')
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise Http404("Invalid date format")
        if not date:
            raise Http404("Date parameter is required")

        # Try to retrieve the existing WalletCollection for the provided date
        expenses = Expense.objects.filter(expense_date=date, temple=temple_id, created_by=request.user).order_by
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context = {
            'expenses': expenses, 'date': date, 'is_central_admin': is_central_admin,
            'temple': temple
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new expense.
        """
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.temple = temple
            expense.created_by = request.user
            expense.save()
            messages.success(request, f"Expense '{expense.item_name}' added successfully.")
        else:
            messages.error(request, "Failed to add expense. Please correct the errors.")
            return redirect(reverse('receipt', kwargs={'pk': bill.id}))
        exp_url = f"{reverse('expense-list')}?date={self.request.POST['expense_date']}"
        return redirect(exp_url)


@method_decorator(check_temple_session, name='dispatch')
class ExpenseDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        expense = get_object_or_404(Expense, id=kwargs.get('pk'), temple=temple)
        expense.delete()
        exp_date = expense.expense_date.date().__str__()
        messages.success(request, f"Offering '{expense.item_name}' successfully deleted from expense date: {exp_date}.")
        return redirect('expense-calendar')

@method_decorator(check_temple_session, name='dispatch')
class ExpenseUpdateView(LoginRequiredMixin, View):
    template_name = 'billing_manager/expense_edit.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        expense = get_object_or_404(Expense, id=kwargs.get('pk'), temple=temple)
        form = ExpenseForm(instance=expense)
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context = {'form': form, 'expense': expense, 'temple': temple, 'is_central_admin': is_central_admin}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        expense = get_object_or_404(Expense, id=kwargs.get('pk'), temple=temple)
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f"Expense '{expense.item_name}' successfully updated.")
        else:
            messages.error(request, "Invalid data, please correct the errors.")
        return redirect('expense-calendar')


@method_decorator(check_temple_session, name='dispatch')
class ExpenseCalendarView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/expense_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temple_id = self.request.session.get('temple_id')
        
        # Filter expenses for the current user and temple
        expenses = Expense.objects.filter(created_by=self.request.user, temple_id=temple_id)
        
        # Group by expense_date and calculate the total expense for each date
        grouped_expenses = (
            expenses
            .values('expense_date__date')  # Extract the date part of expense_date
            .annotate(total_expense=Sum('price'))  # Calculate the sum of the price for each date
            .order_by('expense_date__date')  # Optional: order by date
        )
        
        # Prepare the data for the calendar
        expense_list = []
        for expense in grouped_expenses:
            expense_list.append({
                'start': expense['expense_date__date'].strftime("%Y-%m-%d"),
                'title': f"Total: {expense['total_expense']}",
            })
        
        # Add to context
        context['events'] = expense_list
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple
        return context


@method_decorator(check_temple_session, name='dispatch')
class ExpenseOverallCalendarView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/overall_expense_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temple_id = self.request.session.get('temple_id')
        
        # Filter expenses for the current user and temple
        expenses = Expense.objects.filter(temple_id=temple_id)
        
        # Group by expense_date and calculate the total expense for each date
        grouped_expenses = (
            expenses
            .values('expense_date__date')  # Extract the date part of expense_date
            .annotate(total_expense=Sum('price'))  # Calculate the sum of the price for each date
            .order_by('expense_date__date')  # Optional: order by date
        )
        
        # Prepare the data for the calendar
        expense_list = []
        for expense in grouped_expenses:
            expense_list.append({
                'start': expense['expense_date__date'].strftime("%Y-%m-%d"),
                'title': f"Total: {expense['total_expense']}",
            })
        
        # Add to context
        context['events'] = expense_list
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        context["temple"] = temple_id
        return context


@method_decorator(check_temple_session, name='dispatch')
class OverallExpenseList(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'billing_manager/overall_expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 100

    def get_queryset(self):
        """
        Returns a filtered queryset for expenses. By default, it shows the current month's expenses.
        Validates start_date and end_date if provided.
        """
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        self.temple = temple

        # Get filter parameters
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')

        # Parse dates if provided
        self.start_date = parse_date(start_date_str) if start_date_str else None
        self.end_date = parse_date(end_date_str) if end_date_str else None

        # Validate dates
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return []

        # Convert dates to timezone-aware datetimes
        if self.start_date:
            start_date = timezone.make_aware(datetime.combine(self.start_date, datetime.min.time()))  # 00:00:00
        if self.end_date:
            self.end_date = timezone.make_aware(datetime.combine(self.end_date, datetime.max.time()))  # 23:59:59

        # Default to the current month's expenses if no start_date and end_date are provided
        if not self.start_date and not self.end_date:
            today = date.today()
            self.start_date = today.replace(day=1)  # First day of the current month
            self.end_date = today.replace(month=today.month + 1, day=1) if today.month < 12 else today.replace(month=1, year=today.year + 1, day=1)

        # Query expenses based on the calculated or provided dates
        self.start_date = self.start_date
        self.end_date = self.end_date
        queryset = Expense.objects.filter(
            expense_date__gte=self.start_date,
            expense_date__lt=self.end_date,
            temple_id=temple_id
        ).order_by('expense_date')
        return queryset

    def get_context_data(self, **kwargs):
        """
        Add additional context data to the template, including current month info.
        """
        context = super().get_context_data(**kwargs)
        today = date.today()
        context['expense_amount'] = sum([expense.price for expense in self.get_queryset()])
        context['current_month'] = today.strftime("%B %Y")  # e.g., "October 2024"
        context['start_date'] = self.start_date
        context['end_date'] = self.end_date
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context['is_central_admin'] = is_central_admin
        context["temple"] = self.temple
        return context


@method_decorator(check_temple_session, name='dispatch')
class ExpenseExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):


        # Get the current date and time
        current_datetime = datetime.now()

        # Format it as a string including seconds
        formatted_datetime = current_datetime.strftime('%Y-%m-%d_%H:%M:%S')

        # Get filter parameters from the request
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')


        # Convert to date objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        # Filter bills based on the same logic as the get_queryset method
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()
        
        expenses = Expense.objects.filter(temple_id=temple_id).order_by('expense_date')
        
        if start_date:
            expenses = expenses.filter(expense_date__gte=start_date)
        if end_date:
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59
            expenses = expenses.filter(expense_date__lte=end_date)

        # Prepare the CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="expenses_export_{formatted_datetime}.csv"'

        writer = csv.writer(response)
        
        # Write the header row
        writer.writerow([
            'Sl No', 'Expense Date', 'Item', 'Quantity', 
            'Total Amount', 'Added By'
        ])

        # Write the data rows
        counter = 1
        for expense in expenses:
            
            writer.writerow([
                counter,
                expense.expense_date.strftime("%d-%m-%Y"),
                expense.item_name,
                expense.quantity,
                expense.price,
                expense.created_by.username,
            ])
            counter += 1

        return response


@method_decorator(check_temple_session, name='dispatch')
class AdvanceBookingBillView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/advance_booking.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple, is_deleted=False).order_by('order')

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

        multi_support_vazhipadu = [
            vazhipadu.name for vazhipadu in
            VazhipaduOffering.objects.filter(temple=temple, allow_multiple=True, is_deleted=False)
        ]
        context['multi_support_vazhipadu'] = multi_support_vazhipadu
        return context

    def dispatch(self, request, *args, **kwargs):
        # Check if user is in the 'Central Admin' group
        if request.user.groups.filter(name='Central Admin').exists():
            # Redirect to a different view, for example, to the home page
            return redirect('dashboard')  # Or the URL name of the redirect target
        return super().dispatch(request, *args, **kwargs)