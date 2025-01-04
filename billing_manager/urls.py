"""
URL configuration for TempleKeeper project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from billing_manager.views import (
    BillingView, BillListView, BillDetailView, ReceiptView, SubmitBill,
    ViewMultiReceipt, BillExportView, cancel_bill, update_payment_method,
    WalletCalendar, WalletCollectionCreateView, WalletOveralCollectionCalendar,
    WalletOveralCollectionView, ExpenseView, ExpenseDeleteView, ExpenseUpdateView,
    ExpenseCalendarView, ExpenseCalendarView, OverallExpenseList, ExpenseOverallCalendarView,
    ExpenseExportView, AdvanceBookingBillView)


urlpatterns = [
    path('add_bill/', BillingView.as_view(), name='add-bill'),
    path('submit_billing/', SubmitBill.as_view(), name='submit-billing'),
    path('bill_list/', BillListView.as_view(), name='bill-list'),
    path("bill/<uuid:pk>/", BillDetailView.as_view(), name="bill-detail"),
    path("receipt/<uuid:pk>/", ReceiptView.as_view(), name="receipt"),
    path('view-multi-receipt/', ViewMultiReceipt.as_view(), name='view_multi_receipt'),
    path('export_csv/', BillExportView.as_view(), name='export-csv'),
    path('cancel_bill/<uuid:bill_id>/', cancel_bill, name='cancel-bill'),
    path('update-payment-method/', update_payment_method, name='update-payment-method'),
    path('wallet_calendar/', WalletCalendar.as_view(), name='wallet-info'),
    path('wallet/add/', WalletCollectionCreateView.as_view(), name='wallet_add'),
    path('overall_wallet_calendar/', WalletOveralCollectionCalendar.as_view(), name='overall-wallet-calendar'),
    path('wallet/overall/', WalletOveralCollectionView.as_view(), name='wallet-overall'),
    path('expenses/', ExpenseView.as_view(), name='expense-list'),
    path('expense/delete/<uuid:pk>/', ExpenseDeleteView.as_view(), name='expense-delete'),
    path('expense/edit/<uuid:pk>/', ExpenseUpdateView.as_view(), name='expense-edit'),
    path('expense_calendar/', ExpenseCalendarView.as_view(), name='expense-calendar'),
    path('overall_expense_calendar/', ExpenseOverallCalendarView.as_view(), name='overall-expense-calendar'),
    path('overall_expense/', OverallExpenseList.as_view(), name='overall-expense-list'),
    path('export_expenses/', ExpenseExportView.as_view(), name='export-expenses-as-csv'),
    path('advance_booking/', AdvanceBookingBillView.as_view(), name='advance-booking-bill'),
    # path('offerings/edit/<int:pk>/', VazhipaduOfferingUpdateView.as_view(), name='offerings-edit'),

]
