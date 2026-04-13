from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from datetime import datetime, timedelta
from django.conf import settings
from .models import (
    Role, Position, Department, Building, Office, Manufacturer,
    EquipmentModel, EquipmentType, EquipmentStatus, Warranty, Photos,
    Equipment, RequestCategory, RepairStage, Priority, SparePart,
    Employee, RequestFix, RequestSparePart, RequestService, ThirdPartyService, File
)

# --------------------------------------------------------------
# ВХОД В СИСТЕМУ (использую русские обозначения сотрудника и техника)
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST.get("username")
        password = request.POST.get("password")
        try:
            user = Employee.objects.get(login=login_input, delete_date__isnull=True)
            if user.password == password:
                request.session['user_id'] = user.id
                request.session['user_login'] = user.login
                role_name = user.role.role_name if user.role else 'Сотрудник'
                request.session['user_role'] = role_name
                request.session['user_name'] = f'{user.last_name} {user.first_name} {user.middle_name}'
                request.session['user_position'] = user.position.name if user.position else None
                request.session['form_open'] = False
                user.last_login = timezone.now()
                user.save()
                if role_name == 'Техник':
                    return redirect('show_technician')
                return redirect('show_customer')
            else:
                messages.error(request, 'Неверный пароль')
        except Employee.DoesNotExist:
            messages.error(request, 'Пользователь с таким логином не найден')
        except Exception as e:
            messages.error(request, f'Ошибка при входе: {str(e)}')
    return render(request, 'login.html')


# --------------------------------------------------------------
# ВЫХОД
def logout_view(request):
    try:
        request.session.flush()
        messages.info(request, "Вы вышли из системы!")
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('login_view')


# --------------------------------------------------------------
# ЗАЯВКИ СОТРУДНИКА (через listview)
class CustomerRequestListView(ListView):
    model = RequestFix
    template_name = 'show_customer.html'
    context_object_name = 'requests'

# Проверка авторизации
    def dispatch(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        one_employee = Employee.objects.get(id=self.request.session['user_id'], delete_date__isnull=True)
        queryset = RequestFix.objects.filter(
            requester=one_employee,
            delete_date__isnull=True
        ).select_related(
            'equipment', 'equipment__model', 'equipment__type',
            'equipment__status', 'equipment__assigned_office',
            'assigned_technician', 'category', 'repair_stage', 'priority'
        )
        # Поиск по описанию, номеру проблемы и номеру инвентаря
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )

        #Фильтр по статусу
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(equipment__status_id=status_filter)

        #Сортировка по датам, номеру заявки
        sort_by = self.request.GET.get('sort', '-registration_date')
        if sort_by in ['registration_date', '-registration_date', 'act_number', '-act_number']:
            queryset = queryset.order_by(sort_by)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort', '-registration_date')
        context['user_name'] = self.request.session.get('user_name', '')
        context['user_role'] = self.request.session.get('user_role', '')
        return context

#----------------------------------------------------------------
# СОЗДАНИЕ ЗАЯВКИ (СОТРУДНИК)
def create_request_customer(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    try:
        one_employee = Employee.objects.get(id=request.session['user_id'], delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(
            assigned_office=one_employee.office,
            delete_date__isnull=True
        ).select_related('model', 'type', 'status')

        if request.method == 'GET':
            request.session['form_open'] = False

        if request.method == 'POST':
            if request.session.get('form_open', False):
                messages.error(request, 'Форма уже открыта. Обновите страницу.')
                return redirect('create_request_customer')

            try:
                request.session['form_open'] = True
                equipment_inv_num = request.POST.get('equipment')
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')

                if not description or not equipment_inv_num:
                    messages.error(request, 'Заполните обязательные поля')
                    request.session['form_open'] = False
                    return redirect('create_request_customer')

                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None
                last_req = RequestFix.objects.filter(delete_date__isnull=True).order_by('-act_number').first()
                new_act_number = (last_req.act_number + 1) if last_req else 1

                req = RequestFix(
                    act_number=new_act_number,
                    problem_description=description,
                    registration_date=timezone.now(),
                    requester=one_employee,
                    equipment=equipment,
                    category=category,
                    priority=priority,
                    repair_stage=RepairStage.objects.first()
                )
                req.save()
                request.session['form_open'] = False
                messages.success(request, 'Заявка создана!')
                return redirect('show_customer')

            except Exception as e:
                request.session['form_open'] = False
                messages.error(request, f'Ошибка создания: {str(e)}')
                return redirect('create_request_customer')

        context = {
            'employee': one_employee,
            'equipment_list': equipment_list,
            'categories': RequestCategory.objects.filter(delete_date__isnull=True),
            'priorities': Priority.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'create_request_customer.html', context)

    except Exception as e:
        request.session['form_open'] = False
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_customer')

# --------------------------------------------------------------
# ЗАЯВКИ ТЕХНИКА (ListView)
class TechnicianRequestListView(ListView):
    model = RequestFix
    template_name = 'show_technician.html'
    context_object_name = 'requests'

    def dispatch(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.error(request, 'Необходимо авторизоваться')
            return redirect('login_view')
        if request.session.get('user_role') != 'Техник':
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = RequestFix.objects.all().select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status',
            'category', 'repair_stage', 'priority'
        )

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(requester__last_name__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )

        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(equipment__status_id=status_filter)

        employee_filter = self.request.GET.get('employee', '')
        if employee_filter:
            queryset = queryset.filter(
                Q(requester__first_name__icontains=employee_filter) |
                Q(requester__last_name__icontains=employee_filter)
            )

        sort_by = self.request.GET.get('sort', '-registration_date')
        valid_sorts = ['registration_date', '-registration_date', 'act_number', 'requester__last_name',
                       'equipment__status__name']
        if sort_by in valid_sorts or sort_by.replace('-', '') in valid_sorts:
            queryset = queryset.order_by(sort_by)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['employee_filter'] = self.request.GET.get('employee', '')
        context['sort_by'] = self.request.GET.get('sort', '-registration_date')
        context['user_name'] = self.request.session.get('user_name', '')
        context['new_requests_count'] = RequestFix.objects.filter(
            delete_date__isnull=True,
            assigned_technician__isnull=True
        ).count()
        return context


# --------------------------------------------------------------
# НОВЫЕ ЗАЯВКИ
def show_new_requests(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        requests = RequestFix.objects.filter(
            Q(assigned_technician__isnull=True) | Q(completion_date__isnull=True)
        ).select_related(
            'requester', 'assigned_technician', 'equipment', 'equipment__status'
        )
        sort_by = request.GET.get('sort', '-registration_date')
        if sort_by in ['registration_date', '-registration_date', 'act_number']:
            requests = requests.order_by(sort_by)
        context = {
            'requests': requests,
            'sort_by': sort_by,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'show_new_requests.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# СОЗДАНИЕ ЗАЯВКИ ТЕХНИКОМ
def create_request_technician(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='Техник')
        customers = Employee.objects.filter(delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)
        if request.method == 'POST':
            try:
                customer_id = request.POST.get('requester')
                equipment_inv_num = request.POST.get('equipment')
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                status_id = request.POST.get('status')
                date_done_str = request.POST.get('completion_date', '')
                if not description or not equipment_inv_num or not customer_id:
                    messages.error(request, 'Заполните обязательные поля')
                    return redirect('create_request_technician')
                customer = Employee.objects.get(id=customer_id, delete_date__isnull=True)
                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                assigned_tech = Employee.objects.get(id=technician_id) if technician_id else None
                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None
                stage = RepairStage.objects.get(id=stage_id) if stage_id else None
                date_done = None
                if date_done_str:
                    date_done = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%dT%H:%M'))
                last_act = RequestFix.objects.all().order_by('-act_number').first()
                new_act_number = (last_act.act_number + 1) if last_act else 1
                req = RequestFix(
                    act_number=new_act_number,
                    problem_description=description,
                    registration_date=timezone.now(),
                    completion_date=date_done,
                    requester=customer,
                    assigned_technician=assigned_tech,
                    equipment=equipment,
                    category=category,
                    repair_stage=stage,
                    priority=priority
                )
                req.save()
                if status_id:
                    equipment.status = EquipmentStatus.objects.get(id=status_id)
                    equipment.save()
                messages.success(request, 'Заявка создана!')
                return redirect('show_technician')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
        context = {
            'technicians': technicians,
            'customers': customers,
            'equipment_list': equipment_list,
            'statuses': statuses,
            'categories': categories,
            'priorities': priorities,
            'stages': stages,
            'now': timezone.now(),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'create_request_technician.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# РЕДАКТИРОВАНИЕ ЗАЯВКИ
def edit_request(request, request_id):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        req = get_object_or_404(RequestFix, act_number=request_id)
        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='Техник')
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)
        spare_parts_list = SparePart.objects.filter(delete_date__isnull=True)
        services_list = ThirdPartyService.objects.filter(delete_date__isnull=True)

        if request.method == 'POST':
            try:
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                equipment_inv_num = request.POST.get('equipment')
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                status_id = request.POST.get('status')
                date_done_str = request.POST.get('completion_date', '')

                if not description:
                    messages.error(request, 'Описание обязательно')
                    return redirect('edit_request', request_id=request_id)

                req.problem_description = description
                req.equipment = Equipment.objects.get(inventory_number=equipment_inv_num)
                req.assigned_technician = Employee.objects.get(id=technician_id) if technician_id else None
                if category_id:
                    req.category = RequestCategory.objects.get(id=category_id)
                if priority_id:
                    req.priority = Priority.objects.get(id=priority_id)
                if stage_id:
                    req.repair_stage = RepairStage.objects.get(id=stage_id)
                if date_done_str:
                    req.completion_date = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%dT%H:%M'))
                else:
                    req.completion_date = None
                req.save()
                if status_id:
                    req.equipment.status = EquipmentStatus.objects.get(id=status_id)
                    req.equipment.save()

                # Сохранение запчастей
                spare_part_ids = request.POST.getlist('spare_part_id[]')
                spare_part_quantities = request.POST.getlist('spare_part_quantity[]')
                if spare_part_ids:
                    req.used_spare_parts.all().delete()
                    for i, part_id in enumerate(spare_part_ids):
                        if part_id and spare_part_quantities[i]:
                            part = SparePart.objects.get(id=part_id)
                            RequestSparePart.objects.create(
                                request=req,
                                spare_part=part,
                                quantity=int(spare_part_quantities[i]),
                                cost_at_repair=part.cost
                            )

                service_ids = request.POST.getlist('service_id[]')
                service_quantities = request.POST.getlist('service_quantity[]')
                service_files = request.FILES.getlist('service_file[]')
                if service_ids:
                    req.used_services.all().delete()
                    for i, service_id in enumerate(service_ids):
                        if service_id and service_quantities[i]:
                            service = ThirdPartyService.objects.get(id=service_id)
                            receipt_file = None
                            if i < len(service_files) and service_files[i]:
                                file_obj = File.objects.create(file=service_files[i])
                                receipt_file = file_obj
                            RequestService.objects.create(
                                request=req,
                                service=service,
                                quantity=int(service_quantities[i]),
                                cost_at_repair=service.cost,
                                receipt_file=receipt_file
                            )

                messages.success(request, 'Заявка обновлена!')
                return redirect('show_technician')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')

        context = {
            'request_obj': req,
            'technicians': technicians,
            'statuses': statuses,
            'equipment_list': equipment_list,
            'categories': categories,
            'priorities': priorities,
            'stages': stages,
            'spare_parts_list': spare_parts_list,
            'services_list': services_list,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'edit_request.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# МЯГКОЕ УДАЛЕНИЕ
def delete_request_customer(request, request_id):
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    user_role = request.session.get('user_role', '')
    if user_role not in ['Сотрудник', 'Техник']:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    if request.method == 'POST':
        try:
            req = RequestFix.objects.get(act_number=request_id)
            if req.requester.id != request.session['user_id']:
                messages.error(request, 'Это не ваша заявка')
                return redirect('show_customer')
            if not req.completion_date:
                messages.error(request, 'Можно удалить только выполненную заявку')
                return redirect('show_customer')
            req.delete_date = timezone.now()
            req.save()
            messages.success(request, 'Заявка удалена (архивирована)')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_customer')


# --------------------------------------------------------------
# МЯГКО УДАЛЁННЫЕ ЗАЯВКИ (для техника)
def show_deleted_requests(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')

    try:
        requests = RequestFix.objects.filter(
            delete_date__isnull=False
        ).select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status'
        ).order_by('-delete_date')

        context = {
            'requests': requests,
            'user_name': request.session.get('user_name', ''),
            'page_title': 'Мягко удалённые заявки',
        }
        return render(request, 'show_deleted_requests.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# ВОССТАНОВЛЕНИЕ ЗАЯВКИ (для техника)
def restore_request(request, request_id):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')

    if request.method == 'POST':
        try:
            req = RequestFix.objects.get(act_number=request_id)
            req.delete_date = None
            req.save()
            messages.success(request, f'Заявка №{req.act_number} восстановлена!')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')

    return redirect('show_deleted_requests')


# --------------------------------------------------------------
# ПОЛНОЕ УДАЛЕНИЕ
def delete_request_technician(request, request_id):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    if request.method == 'POST':
        try:
            req = RequestFix.objects.get(act_number=request_id)
            req.delete()
            messages.success(request, 'Заявка полностью удалена')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_technician')


# --------------------------------------------------------------
# СТАТИСТИКА
def statistics_view(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        equipment_stats = RequestFix.objects.filter(
            delete_date__isnull=True
        ).values(
            'equipment__inventory_number',
            'equipment__model__name',
            'equipment__type__name'
        ).annotate(
            breakdown_count=Count('act_number')
        ).order_by('-breakdown_count')[:10]
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = RequestFix.objects.filter(
            delete_date__isnull=True,
            registration_date__gte=six_months_ago
        ).extra(
            select={'month': "TO_CHAR(registration_date, 'YYYY-MM')"}
        ).values('month').annotate(
            count=Count('act_number')
        ).order_by('month')
        total = RequestFix.objects.count()
        completed = RequestFix.objects.filter(completion_date__isnull=False).count()
        type_stats = RequestFix.objects.filter(
            delete_date__isnull=True
        ).values('equipment__type__name').annotate(
            count=Count('act_number')
        ).order_by('-count')
        context = {
            'equipment_stats': list(equipment_stats),
            'monthly_stats': list(monthly_stats),
            'total_requests': total,
            'completed_requests': completed,
            'pending_requests': total - completed,
            'type_stats': list(type_stats),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'statistics.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка статистики: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# ОБОРУДОВАНИЕ (ListView)
class EquipmentListView(ListView):
    model = Equipment
    template_name = 'show_equipment.html'
    context_object_name = 'equipment_list'

    def dispatch(self, request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.error(request, 'Нет доступа')
            return redirect('login_view')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Equipment.objects.filter(delete_date__isnull=True).select_related(
            'model', 'model__manufacturer', 'type', 'status',
            'assigned_office', 'assigned_office__building', 'warranty', 'photo'
        )

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(inventory_number__icontains=search_query) |
                Q(model__name__icontains=search_query)
            )

        type_filter = self.request.GET.get('type', '')
        if type_filter:
            queryset = queryset.filter(type_id=type_filter)

        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status_id=status_filter)

        sort_by = self.request.GET.get('sort', 'inventory_number')
        if sort_by in ['inventory_number', '-inventory_number', 'model__name', 'status__name']:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types'] = EquipmentType.objects.filter(delete_date__isnull=True)
        context['statuses'] = EquipmentStatus.objects.filter(delete_date__isnull=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort', 'inventory_number')
        context['user_name'] = self.request.session.get('user_name', '')
        context['MEDIA_URL'] = '/media/'
        return context


# --------------------------------------------------------------
# РЕДАКТИРОВАНИЕ ОБОРУДОВАНИЯ
def edit_equipment(request, inventory_number):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        equipment = get_object_or_404(Equipment, inventory_number=inventory_number, delete_date__isnull=True)

        if request.method == 'POST':
            try:
                equipment.model_id = request.POST.get('model')
                equipment.type_id = request.POST.get('type')
                equipment.status_id = request.POST.get('status')
                equipment.configuration = request.POST.get('configuration', '')
                equipment.assigned_office_id = request.POST.get('assigned_office')

                photo_file = request.FILES.get('photo')
                if photo_file:
                    import os
                    from datetime import datetime
                    from django.conf import settings

                    ext = os.path.splitext(photo_file.name)[1]
                    unique_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"equipment_{equipment.inventory_number}_{unique_id}{ext}"

                    file_path = os.path.join('equipment', filename)
                    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    with open(full_path, 'wb+') as destination:
                        for chunk in photo_file.chunks():
                            destination.write(chunk)

                    photo = Photos.objects.create(name=filename)
                    if equipment.photo and equipment.photo.id != photo.id:
                        equipment.photo.delete_date = timezone.now()
                        equipment.photo.save()

                    equipment.photo = photo

                equipment.save()
                messages.success(request, 'Оборудование обновлено!')
                return redirect('show_equipment')

            except Exception as e:
                messages.error(request, f'Ошибка при обновлении: {str(e)}')
        context = {
            'equipment': equipment,
            'models': EquipmentModel.objects.filter(delete_date__isnull=True),
            'types': EquipmentType.objects.filter(delete_date__isnull=True),
            'statuses': EquipmentStatus.objects.filter(delete_date__isnull=True),
            'offices': Office.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'edit_equipment.html', context)

    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')


# --------------------------------------------------------------
# ЗАТРАТЫ НА ОБОРУДОВАНИЕ
def equipment_costs(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        equipment_id = request.GET.get('equipment_id')
        equipment = None

        if equipment_id:
            equipment = get_object_or_404(Equipment, inventory_number=int(equipment_id), delete_date__isnull=True)
            requests = RequestFix.objects.filter(equipment=equipment, delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )
        else:
            requests = RequestFix.objects.filter(delete_date__isnull=True).prefetch_related(
                'used_spare_parts', 'used_services'
            )

        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        if date_from:
            requests = requests.filter(registration_date__gte=date_from)
        if date_to:
            requests = requests.filter(registration_date__lte=date_to)

        total_cost = 0
        for req in requests:
            spare_parts_cost = sum(item.total_cost for item in req.used_spare_parts.filter(delete_date__isnull=True))
            services_cost = sum(item.total_cost for item in req.used_services.filter(delete_date__isnull=True))
            req.total_cost = spare_parts_cost + services_cost
            req.spare_parts_cost = spare_parts_cost
            req.services_cost = services_cost
            total_cost += req.total_cost

        avg_cost = total_cost / requests.count() if requests.count() > 0 else 0

        context = {
            'equipment': equipment,
            'requests': requests,
            'total_cost': total_cost,
            'avg_cost': round(avg_cost, 2),
            'date_from': date_from,
            'date_to': date_to,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'equipment_costs.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_equipment')


# --------------------------------------------------------------
# ГЛАВНАЯ
def index(request):
    if 'user_id' in request.session:
        if request.session.get('user_role') == 'Техник':
            return redirect('show_technician')
        return redirect('show_customer')
    return redirect('login_view')