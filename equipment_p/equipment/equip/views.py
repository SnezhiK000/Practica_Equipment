
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, timedelta
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.shortcuts import render, redirect
from datetime import timedelta
from .models import RequestFix, EquipmentType
from .models import (
    Role, Position, Department, Building, Office, Manufacturer,
    EquipmentModel, EquipmentType, EquipmentStatus, Warranty, Photos,
    Equipment, RequestCategory, RepairStage, Priority, SparePart,
    Employee, RequestFix
)

# --------------------------------------------------------------
# ВХОД В СИСТЕМУ
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
# ЗАЯВКИ СОТРУДНИКА
def show_customer(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')
    try:
        request.session['form_open'] = False
        one_employee = Employee.objects.get(id=request.session['user_id'], delete_date__isnull=True)

        requests = RequestFix.objects.filter(
            requester=one_employee,
            delete_date__isnull=True
        ).select_related(
            'equipment',
            'equipment__model',
            'equipment__type',
            'equipment__status',
            'equipment__assigned_office',
            'equipment__assigned_office__building',
            'assigned_technician',
            'category',
            'repair_stage',
            'priority'
        )

        search_query = request.GET.get('search', '')
        if search_query:
            requests = requests.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )

        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        status_filter = request.GET.get('status', '')
        if status_filter:
            requests = requests.filter(equipment__status_id=status_filter)

        sort_by = request.GET.get('sort', '-registration_date')
        if sort_by in ['registration_date', '-registration_date', 'act_number', '-act_number']:
            requests = requests.order_by(sort_by)

        context = {
            'requests': requests,
            'statuses': statuses,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'user_name': request.session.get('user_name', ''),
            'user_role': request.session.get('user_role', ''),
        }
        return render(request, 'show_customer.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('login_view')


# --------------------------------------------------------------
# СОЗДАНИЕ ЗАЯВКИ СОТРУДНИКОМ
def create_request_customer(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')

    if request.session.get('form_open', False):
        messages.error(request, 'Форма уже открыта!')
        return redirect('show_customer')

    try:
        one_employee = Employee.objects.get(id=request.session['user_id'], delete_date__isnull=True)

        # Фильтруем оборудование только для кабинета сотрудника
        equipment_list = Equipment.objects.filter(
            assigned_office=one_employee.office,
            delete_date__isnull=True
        ).select_related('model', 'type', 'status')

        if request.method == 'POST':
            try:
                request.session['form_open'] = False

                equipment_inv_num = request.POST.get('equipment')  # Получаем инв. номер
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')

                if not description or not equipment_inv_num:
                    messages.error(request, 'Заполните обязательные поля')
                    return redirect('create_request_customer')

                # ИСПРАВЛЕНИЕ: Ищем по inventory_number, так как это primary_key
                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)

                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None

                # Генерация нового номера акта
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
                    repair_stage=RepairStage.objects.first()  # Ставим первый этап по умолчанию
                )
                req.save()

                messages.success(request, 'Заявка создана!')
                return redirect('show_customer')

            except Equipment.DoesNotExist:
                messages.error(request, 'Выбранное оборудование не найдено в базе.')
            except Exception as e:
                messages.error(request, f'Ошибка при создании: {str(e)}')
                request.session['form_open'] = False

        request.session['form_open'] = True
        context = {
            'employee': one_employee,
            'equipment_list': equipment_list,
            'categories': RequestCategory.objects.filter(delete_date__isnull=True),
            'priorities': Priority.objects.filter(delete_date__isnull=True),
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'create_request_customer.html', context)

    except Employee.DoesNotExist:
        messages.error(request, 'Сотрудник не найден.')
        return redirect('login_view')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        request.session['form_open'] = False
        return redirect('show_customer')

# --------------------------------------------------------------
# ЗАЯВКИ ТЕХНИКА
def show_technician(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        requests = RequestFix.objects.filter(delete_date__isnull=True).select_related(
            'requester', 'assigned_technician', 'equipment',
            'equipment__model', 'equipment__type', 'equipment__status',
            'category', 'repair_stage', 'priority'
        )

        search_query = request.GET.get('search', '')
        if search_query:
            requests = requests.filter(
                Q(problem_description__icontains=search_query) |
                Q(act_number__icontains=search_query) |
                Q(requester__last_name__icontains=search_query) |
                Q(equipment__inventory_number__icontains=search_query)
            )

        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        status_filter = request.GET.get('status', '')
        if status_filter:
            requests = requests.filter(equipment__status_id=status_filter)

        employee_filter = request.GET.get('employee', '')
        if employee_filter:
            requests = requests.filter(
                Q(requester__first_name__icontains=employee_filter) |
                Q(requester__last_name__icontains=employee_filter)
            )

        sort_by = request.GET.get('sort', '-registration_date')
        valid_sorts = ['registration_date', '-registration_date', 'act_number', 'requester__last_name',
                       'equipment__status__name']
        if sort_by in valid_sorts or sort_by.replace('-', '') in valid_sorts:
            requests = requests.order_by(sort_by)

        context = {
            'requests': requests,
            'statuses': statuses,
            'search_query': search_query,
            'status_filter': status_filter,
            'employee_filter': employee_filter,
            'sort_by': sort_by,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'show_technician.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('login_view')


# --------------------------------------------------------------
# НОВЫЕ ЗАЯВКИ
def show_new_requests(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        requests = RequestFix.objects.filter(
            delete_date__isnull=True
        ).filter(
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
        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='technician')
        customers = Employee.objects.filter(delete_date__isnull=True)
        # ОШИБКА БЫЛА ЗДЕСЬ: Equipment не имеет поля id, используем inventory_number как PK, но filter работает по любому полю.
        # Однако, если вы передадите inventory_number в POST, то get(inventory_number=...) сработает.
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)

        if request.method == 'POST':
            try:
                customer_id = request.POST.get('requester')
                # Получаем inventory_number из формы
                equipment_inv_num = request.POST.get('equipment')
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                date_done_str = request.POST.get('completion_date', '')

                if not description or not equipment_inv_num or not customer_id:
                    messages.error(request, 'Заполните обязательные поля')
                    return redirect('create_request_technician')
                equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                customer = Employee.objects.get(id=customer_id, delete_date__isnull=True)
                assigned_tech = Employee.objects.get(id=technician_id) if technician_id else None
                category = RequestCategory.objects.get(id=category_id) if category_id else None
                priority = Priority.objects.get(id=priority_id) if priority_id else None
                stage = RepairStage.objects.get(id=stage_id) if stage_id else None

                date_done = None
                if date_done_str:
                    date_done = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%dT%H:%M'))

                # Генерация нового номера акта
                last_act = RequestFix.objects.filter(delete_date__isnull=True).order_by('-act_number').first()
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
                messages.success(request, 'Заявка создана!')
                return redirect('show_technician')
            except Equipment.DoesNotExist:
                messages.error(request, 'Оборудование не найдено')
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
        # Ищем заявку по act_number (так как это PK)
        req = get_object_or_404(RequestFix, act_number=request_id, delete_date__isnull=True)

        technicians = Employee.objects.filter(delete_date__isnull=True, role__role_name='technician')
        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        equipment_list = Equipment.objects.filter(delete_date__isnull=True)
        categories = RequestCategory.objects.filter(delete_date__isnull=True)
        priorities = Priority.objects.filter(delete_date__isnull=True)
        stages = RepairStage.objects.filter(delete_date__isnull=True)

        if request.method == 'POST':
            try:
                technician_id = request.POST.get('assigned_technician')
                description = request.POST.get('problem_description', '').strip()
                equipment_inv_num = request.POST.get('equipment')  # Получаем инв. номер
                category_id = request.POST.get('category')
                priority_id = request.POST.get('priority')
                stage_id = request.POST.get('repair_stage')
                date_done_str = request.POST.get('completion_date', '')

                if not description:
                    messages.error(request, 'Описание обязательно')
                    return redirect('edit_request', request_id=request_id)

                # ИСПРАВЛЕНИЕ: Ищем оборудование по inventory_number
                req.equipment = Equipment.objects.get(inventory_number=equipment_inv_num, delete_date__isnull=True)
                req.problem_description = description
                req.assigned_technician = Employee.objects.get(id=technician_id) if technician_id else None

                if category_id: req.category = RequestCategory.objects.get(id=category_id)
                if priority_id: req.priority = Priority.objects.get(id=priority_id)
                if stage_id: req.repair_stage = RepairStage.objects.get(id=stage_id)

                if date_done_str:
                    req.completion_date = timezone.make_aware(datetime.strptime(date_done_str, '%Y-%m-%dT%H:%M'))
                else:
                    req.completion_date = None

                req.save()
                messages.success(request, 'Заявка обновлена!')
                return redirect('show_technician')
            except Equipment.DoesNotExist:
                messages.error(request, 'Оборудование не найдено')
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
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'edit_request.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# МЯГКОЕ УДАЛЕНИЕ ЗАЯВКИ (ДОСТУПНО СОТРУДНИКУ И ТЕХНИКУ)
def delete_request_customer(request, request_id):
    # 1. Проверка авторизации
    if 'user_id' not in request.session:
        messages.error(request, 'Необходимо авторизоваться')
        return redirect('login_view')

    user_role = request.session.get('user_role', '')
    user_id = request.session['user_id']

    if user_role not in ['Сотрудник', 'Техник']:
        messages.error(request, 'У вас нет доступа к удалению заявок')
        return redirect('login_view')

    if request.method == 'POST':
        try:
            req = RequestFix.objects.get(act_number=request_id, delete_date__isnull=True)
            if req.requester.id != user_id:
                messages.error(request, 'Вы можете удалить только свою собственную заявку!')
                return redirect('show_customer')
            if not req.completion_date:
                messages.error(request, 'Можно удалить только выполненную заявку!')
                return redirect('show_customer')
            req.delete_date = timezone.now()
            req.save()

            messages.success(request, f'Заявка №{req.act_number} успешно удалена (архивирована)')

        except RequestFix.DoesNotExist:
            messages.error(request, 'Заявка не найдена или уже удалена')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении: {str(e)}')

    return redirect('show_customer')


# --------------------------------------------------------------
# УДАЛЕНИЕ (ТЕХНИК)
def delete_request_technician(request, request_id):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    if request.method == 'POST':
        try:
            req = RequestFix.objects.get(act_number=request_id, delete_date__isnull=True)
            req.delete()
            messages.success(request, 'Заявка полностью удалена')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    return redirect('show_technician')


# --------------------------------------------------------------
# СТАТИСТИКА (НЕ РАБОТАЕТ)
def statistics_view(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'Техник':
        messages.error(request, 'Нет доступа')
        return redirect('login_view')

    try:
        # Топ оборудования
        equipment_stats = RequestFix.objects.filter(delete_date__isnull=True).values(
            'equipment__inventory_number', 'equipment__model__name', 'equipment__type__name'
        ).annotate(breakdown_count=Count('id')).order_by('-breakdown_count')[:10]

        # По месяцам
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_stats = RequestFix.objects.filter(
            delete_date__isnull=True, registration_date__gte=six_months_ago
        ).extra(select={'month': "DATE_FORMAT(registration_date, '%%Y-%%m')"}).values('month').annotate(count=Count('id')).order_by('month')

        #Общее
        total = RequestFix.objects.filter(delete_date__isnull=True).count()
        completed = RequestFix.objects.filter(delete_date__isnull=True, completion_date__isnull=False).count()

        context = {
            'equipment_stats': list(equipment_stats),
            'monthly_stats': list(monthly_stats),
            'total_requests': total,
            'completed_requests': completed,
            'pending_requests': total - completed,
            'type_stats': [],
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'statistics.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка статистики: {str(e)}')
        return redirect('show_technician')


# --------------------------------------------------------------
# ОБОРУДОВАНИЕ
def show_equipment(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        equipment_list = Equipment.objects.filter(delete_date__isnull=True).select_related(
            'model', 'model__manufacturer', 'type', 'status',
            'assigned_office', 'assigned_office__building', 'warranty', 'photo'
        )

        search_query = request.GET.get('search', '')
        if search_query:
            equipment_list = equipment_list.filter(
                Q(inventory_number__icontains=search_query) |
                Q(model__name__icontains=search_query)
            )

        types = EquipmentType.objects.filter(delete_date__isnull=True)
        type_filter = request.GET.get('type', '')
        if type_filter:
            equipment_list = equipment_list.filter(type_id=type_filter)

        statuses = EquipmentStatus.objects.filter(delete_date__isnull=True)
        status_filter = request.GET.get('status', '')
        if status_filter:
            equipment_list = equipment_list.filter(status_id=status_filter)

        sort_by = request.GET.get('sort', 'inventory_number')
        if sort_by in ['inventory_number', '-inventory_number', 'model__name', 'status__name']:
            equipment_list = equipment_list.order_by(sort_by)

        context = {
            'equipment_list': equipment_list,
            'types': types,
            'statuses': statuses,
            'search_query': search_query,
            'type_filter': type_filter,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'user_name': request.session.get('user_name', ''),
        }
        return render(request, 'show_equipment.html', context)
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
        return redirect('login_view')


# --------------------------------------------------------------
# ЗАТРАТЫ
def equipment_costs(request):
    if 'user_id' not in request.session:
        messages.error(request, 'Нет доступа')
        return redirect('login_view')
    try:
        equipment_id = request.GET.get('equipment_id')
        equipment = None

        if equipment_id:
            # Ищем оборудование по inventory_number (так как это PK)
            equipment = get_object_or_404(Equipment, inventory_number=equipment_id, delete_date__isnull=True)
            requests = RequestFix.objects.filter(equipment=equipment, delete_date__isnull=True)
        else:
            requests = RequestFix.objects.filter(delete_date__isnull=True)

        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        if date_from:
            requests = requests.filter(registration_date__gte=date_from)
        if date_to:
            requests = requests.filter(registration_date__lte=date_to)

        total_cost = 0
        for req in requests:
            req.total_cost = 0  # Заглушка

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