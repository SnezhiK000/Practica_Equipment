from django.db import models

# --------------------------------------------------------------
# РОЛЬ
class Role(models.Model):
    ROLE_CHOICES = [
        ('technician', 'Техник'),
        ('employee', 'Сотрудник'),
    ]
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    role_name = models.CharField(max_length=250, choices=ROLE_CHOICES, unique=True, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.get_role_name_display()

# --------------------------------------------------------------
# ДОЛЖНОСТЬ
class Position(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ОТДЕЛ
class Department(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование отдела")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# КОРПУСА
class Building(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование корпуса")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# КАБИНЕТ
class Office(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    number = models.CharField(max_length=50, verbose_name="Номер кабинета")
    building = models.ForeignKey(Building, on_delete=models.CASCADE, verbose_name="Корпус")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"Кабинет {self.number}"

# --------------------------------------------------------------
# ПРОИЗВОДИТЕЛИ
class Manufacturer(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# МОДЕЛИ ОБОРУДОВАНИЯ
class EquipmentModel(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование модели")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, verbose_name="Производитель")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ТИП ОБОРУДОВАНИЯ
class EquipmentType(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование типа")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# СТАТУСЫ ОБОРУДОВАНИЯ
class EquipmentStatus(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование статуса")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ГАРАНТИИ
class Warranty(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"Гарантия до {self.end_date}"

# --------------------------------------------------------------
# ФОТОГРАФИИ
class Photos(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Название фото")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ОБОРУДОВАНИЕ
class Equipment(models.Model):
    inventory_number = models.IntegerField(primary_key=True, verbose_name="Инвентарный номер")
    assigned_office = models.ForeignKey(Office, on_delete=models.CASCADE, verbose_name="Закрепленный кабинет")
    model = models.ForeignKey(EquipmentModel, on_delete=models.CASCADE, verbose_name="Модель")
    type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE, verbose_name="Тип оборудования")
    status = models.ForeignKey(EquipmentStatus, on_delete=models.CASCADE, verbose_name="Статус")
    configuration = models.CharField(max_length=255, verbose_name="Комплектация")
    warranty = models.ForeignKey(Warranty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Гарантия")
    purchase_date = models.DateField(verbose_name="Дата приобретения")
    photo = models.ForeignKey(Photos, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Фото")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"{self.model.name} ({self.inventory_number})"

# --------------------------------------------------------------
# КАТЕГОРИИ ЗАЯВОК
class RequestCategory(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ЭТАПЫ РЕМОНТА
class RepairStage(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ПРИОРИТЕТЫ
class Priority(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# ЗАПЧАСТИ
class SparePart(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=250, verbose_name="Наименование")
    quantity = models.IntegerField(verbose_name="Количество")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Стоимость")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return self.name

# --------------------------------------------------------------
# СОТРУДНИК
class Employee(models.Model):
    id = models.IntegerField(primary_key=True, verbose_name="ID")
    login = models.CharField(max_length=250, unique=True, verbose_name="Почта (Логин)")
    phone_number = models.CharField(max_length=20, verbose_name="Номер телефона")
    last_name = models.CharField(max_length=250, verbose_name="Фамилия")
    first_name = models.CharField(max_length=250, verbose_name="Имя")
    middle_name = models.CharField(max_length=250, verbose_name="Отчество")
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name="Должность")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="Отдел")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name="Роль")
    password = models.CharField(max_length=250, verbose_name="Пароль")
    last_login = models.DateTimeField(null=True, blank=True, verbose_name="Время последнего захода")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Кабинет")

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

# --------------------------------------------------------------
# ЗАЯВКА
class RequestFix(models.Model):
    act_number = models.IntegerField(primary_key=True, verbose_name="Номер акта")
    requester = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="requests_made", verbose_name="Заказчик")
    assigned_technician = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_assigned", verbose_name="Назначенный исполнитель")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name="Оборудование")
    category = models.ForeignKey(RequestCategory, on_delete=models.CASCADE, verbose_name="Категория")
    repair_stage = models.ForeignKey(RepairStage, on_delete=models.CASCADE, verbose_name="Этап ремонта")
    priority = models.ForeignKey(Priority, on_delete=models.CASCADE, verbose_name="Приоритет")
    problem_description = models.CharField(max_length=500, verbose_name="Описание неисправности")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    comment_technician = models.TextField(blank=True, null=True, verbose_name="Комментарий техника")
    spare_parts = models.ManyToManyField(SparePart, blank=True, verbose_name="Запчасти")
    delete_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    def __str__(self):
        return f"Заявка №{self.act_number}"