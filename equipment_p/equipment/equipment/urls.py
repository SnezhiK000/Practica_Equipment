from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from equip import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('customer/', views.CustomerRequestListView.as_view(), name='show_customer'),
    path('technician/', views.TechnicianRequestListView.as_view(), name='show_technician'),
    path('new-requests/', views.show_new_requests, name='show_new_requests'),
    path('equipment/', views.EquipmentListView.as_view(), name='show_equipment'),
    path('create-request-customer/', views.create_request_customer, name='create_request_customer'),
    path('create-request-technician/', views.create_request_technician, name='create_request_technician'),
    path('edit-request/<int:request_id>/', views.edit_request, name='edit_request'),
    path('delete-request-customer/<int:request_id>/', views.delete_request_customer, name='delete_request_customer'),
    path('delete-request-technician/<int:request_id>/', views.delete_request_technician, name='delete_request_technician'),
    path('statistics/', views.statistics_view, name='statistics_view'),
    path('equipment-costs/', views.equipment_costs, name='equipment_costs'),
    path('edit-equipment/<int:inventory_number>/', views.edit_equipment, name='edit_equipment'),
    path('deleted-requests/', views.show_deleted_requests, name='show_deleted_requests'),
    path('restore-request/<int:request_id>/', views.restore_request, name='restore_request'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)