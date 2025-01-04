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
from temple_auth.views import (
    AdminSubMenu, TempleListView, TempleDetailView, TempleUpdateView, temple_deselect_view,
    UserUpdateView, update_password_view, update_deactivate_view, NoteListView, NoteCreateView,
    NoteUpdateView, NoteDeleteView)


urlpatterns = [
    path('admin/', AdminSubMenu.as_view(), name='admin-sub-menu'),
    path('list_temples/', TempleListView.as_view(), name='list-temples'),
    path('temple/<uuid:temple_id>/', TempleDetailView.as_view(), name='temple-detail'),
    path('temple/update/<uuid:pk>/', TempleUpdateView.as_view(), name='temple-update'),
    path('user/update/<int:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('deselect-temple/', temple_deselect_view, name='deselect-temple'),
    path("update-password/<int:user_id>/", update_password_view, name="update_user_password"),
    path("user_deactivate/<uuid:temple_id>/<int:user_id>/", update_deactivate_view, name="user-deactivate"),

    path('notes/', NoteListView.as_view(), name='note_list'),
    path('notes/create/', NoteCreateView.as_view(), name='note_create'),
    path('note/<uuid:pk>/update/', NoteUpdateView.as_view(), name='note_update'),
    path('note/<uuid:pk>/delete/', NoteDeleteView.as_view(), name='note_delete'),

]
