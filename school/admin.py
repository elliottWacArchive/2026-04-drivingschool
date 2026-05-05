from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, InstructorProfile, HourPackage, Vehicle, Lesson, Exam


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Rôle', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Rôle', {'fields': ('role',)}),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'available_minutes_display']
    search_fields = ['user__last_name', 'user__first_name']

    def available_minutes_display(self, obj):
        m = obj.available_minutes()
        h, mn = divmod(m, 60)
        return f"{h}h{mn:02d}"
    available_minutes_display.short_description = "Heures disponibles"


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone']
    search_fields = ['user__last_name', 'user__first_name']


@admin.register(HourPackage)
class HourPackageAdmin(admin.ModelAdmin):
    list_display = ['student', 'hours_display', 'purchased_at', 'added_by']
    list_filter = ['purchased_at']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['name', 'transmission']
    list_filter = ['transmission']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['student', 'instructor', 'date', 'duration', 'status']
    list_filter = ['status', 'instructor']
    search_fields = ['student__user__last_name', 'student__user__first_name']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam_type', 'date', 'result', 'score']
    list_filter = ['exam_type', 'result']
