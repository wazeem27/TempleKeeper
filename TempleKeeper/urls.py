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
from django.contrib import admin
from django.urls import path, include
from temple_auth.views import CustomLoginView, logout_view, temple_selection_view, dashboard_view, whats_new_page, settings_view, update_temple_bill, update_split_receipt

urlpatterns = [
    path('', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('temple-selection/', temple_selection_view, name='temple_selection'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('offering/',include('offering_services.urls')),
    path('inventory/',include('temple_inventory.urls')),
    path('billing/',include('billing_manager.urls')),
    path('admin/', admin.site.urls),
    path('updates/', whats_new_page, name='updates'),
    path('settings/', settings_view, name='settings'),
    path('update_bill_detail/', update_temple_bill, name="update_temple_bill"),
    path('update_split_receipt/', update_split_receipt, name="update_split_receipt"),
    
]
