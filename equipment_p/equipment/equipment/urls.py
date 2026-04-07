from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from equip import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('customer/', views.show_customer, name='show_customer'),
    path('technician/', views.show_technician, name='show_technician'),
    path('new-requests/', views.show_new_requests, name='show_new_requests'),
    path('create-request-customer/', views.create_request_customer, name='create_request_customer'),
    path('create-request-technician/', views.create_request_technician, name='create_request_technician'),
    path('edit-request/<int:request_id>/', views.edit_request, name='edit_request'),
    path('delete-request-customer/<int:request_id>/', views.delete_request_customer, name='delete_request_customer'),
    path('delete-request-technician/<int:request_id>/', views.delete_request_technician, name='delete_request_technician'),
    path('statistics/', views.statistics_view, name='statistics_view'),
    path('equipment/', views.show_equipment, name='show_equipment'),
    path('equipment-costs/', views.equipment_costs, name='equipment_costs'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)