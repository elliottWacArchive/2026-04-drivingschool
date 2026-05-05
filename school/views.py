from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView, View,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q

from .models import (
    CustomUser, StudentProfile, InstructorProfile,
    HourPackage, Vehicle, Lesson, Exam,
)
from .forms import (
    StudentCreateForm, StudentUpdateForm,
    InstructorCreateForm, InstructorUpdateForm,
    SecretaryCreateForm, SecretaryUpdateForm,
    HourPackageForm, LessonForm,
    ExamForm, VehicleForm,
)


# mixins de role

class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class StaffMixin(LoginRequiredMixin):
    """Moniteur, secrétaire ou admin."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in (
            CustomUser.ROLE_INSTRUCTOR,
            CustomUser.ROLE_SECRETARY,
            CustomUser.ROLE_ADMIN,
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class SecretaryOrAdminMixin(RoleRequiredMixin):
    allowed_roles = [CustomUser.ROLE_SECRETARY, CustomUser.ROLE_ADMIN]


class AdminOnlyMixin(RoleRequiredMixin):
    allowed_roles = [CustomUser.ROLE_ADMIN]


# dashboard

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'school/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_student:
            profile = get_object_or_404(StudentProfile, user=user)
            ctx['profile'] = profile
            ctx['upcoming_lessons'] = profile.lessons.filter(
                status='scheduled'
            ).select_related('instructor__user', 'vehicle').order_by('date')[:5]
            ctx['available_minutes'] = profile.available_minutes()
            ctx['total_purchased'] = profile.total_minutes_purchased()
            ctx['total_used'] = profile.total_minutes_used()

        elif user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=user)
            ctx['profile'] = profile
            ctx['upcoming_lessons'] = profile.lessons.filter(
                status='scheduled'
            ).select_related('student__user', 'vehicle').order_by('date')[:10]
            ctx['student_count'] = StudentProfile.objects.filter(
                lessons__instructor=profile
            ).distinct().count()

        else:
            ctx['student_count'] = StudentProfile.objects.count()
            ctx['instructor_count'] = InstructorProfile.objects.count()
            ctx['upcoming_lessons'] = Lesson.objects.filter(
                status='scheduled'
            ).select_related('student__user', 'instructor__user').order_by('date')[:10]
            ctx['recent_exams'] = Exam.objects.select_related('student__user').order_by('-date')[:5]

        return ctx


# eleves

class StudentListView(StaffMixin, ListView):
    model = StudentProfile
    template_name = 'school/student_list.html'
    context_object_name = 'students'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q) |
                Q(neph_number__icontains=q)
            )
        return qs


class StudentDetailView(StaffMixin, DetailView):
    model = StudentProfile
    template_name = 'school/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['lessons'] = self.object.lessons.select_related(
            'instructor__user', 'vehicle'
        ).order_by('-date')
        ctx['exams'] = self.object.exams.order_by('-date')
        ctx['packages'] = self.object.hour_packages.select_related('added_by')
        ctx['available_minutes'] = self.object.available_minutes()
        ctx['total_purchased'] = self.object.total_minutes_purchased()
        ctx['total_used'] = self.object.total_minutes_used()
        return ctx


class StudentCreateView(SecretaryOrAdminMixin, View):
    template_name = 'school/student_form.html'

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, {'form': StudentCreateForm(), 'title': 'Nouvel élève'})

    def post(self, request):
        from django.shortcuts import render
        form = StudentCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte élève créé avec succès.")
            return redirect('student-list')
        return render(request, self.template_name, {'form': form, 'title': 'Nouvel élève'})


class StudentUpdateView(SecretaryOrAdminMixin, View):
    template_name = 'school/student_form.html'

    def get_profile(self, pk):
        return get_object_or_404(StudentProfile, pk=pk)

    def get(self, request, pk):
        from django.shortcuts import render
        profile = self.get_profile(pk)
        form = StudentUpdateForm(student_profile=profile)
        return render(request, self.template_name, {'form': form, 'object': profile, 'title': f'Modifier {profile}'})

    def post(self, request, pk):
        from django.shortcuts import render
        profile = self.get_profile(pk)
        form = StudentUpdateForm(request.POST, student_profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('student-detail', pk=pk)
        return render(request, self.template_name, {'form': form, 'object': profile, 'title': f'Modifier {profile}'})


class StudentDeleteView(SecretaryOrAdminMixin, View):
    template_name = 'school/confirm_delete.html'

    def get(self, request, pk):
        from django.shortcuts import render
        profile = get_object_or_404(StudentProfile, pk=pk)
        return render(request, self.template_name, {'object': profile})

    def post(self, request, pk):
        profile = get_object_or_404(StudentProfile, pk=pk)
        profile.user.delete()
        messages.success(request, "Compte élève supprimé.")
        return redirect('student-list')


# moniteurs

class InstructorListView(SecretaryOrAdminMixin, ListView):
    model = InstructorProfile
    template_name = 'school/instructor_list.html'
    context_object_name = 'instructors'
    paginate_by = 15

    def get_queryset(self):
        return super().get_queryset().select_related('user')


class InstructorDetailView(SecretaryOrAdminMixin, DetailView):
    model = InstructorProfile
    template_name = 'school/instructor_detail.html'
    context_object_name = 'instructor'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['lessons'] = self.object.lessons.select_related(
            'student__user', 'vehicle'
        ).order_by('-date')[:20]
        return ctx


class InstructorCreateView(SecretaryOrAdminMixin, View):
    template_name = 'school/instructor_form.html'

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, {'form': InstructorCreateForm(), 'title': 'Nouveau moniteur'})

    def post(self, request):
        from django.shortcuts import render
        form = InstructorCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte moniteur créé avec succès.")
            return redirect('instructor-list')
        return render(request, self.template_name, {'form': form, 'title': 'Nouveau moniteur'})


class InstructorUpdateView(SecretaryOrAdminMixin, View):
    template_name = 'school/instructor_form.html'

    def get_profile(self, pk):
        return get_object_or_404(InstructorProfile, pk=pk)

    def get(self, request, pk):
        from django.shortcuts import render
        profile = self.get_profile(pk)
        form = InstructorUpdateForm(instructor_profile=profile)
        return render(request, self.template_name, {'form': form, 'object': profile, 'title': f'Modifier {profile}'})

    def post(self, request, pk):
        from django.shortcuts import render
        profile = self.get_profile(pk)
        form = InstructorUpdateForm(request.POST, instructor_profile=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour.")
            return redirect('instructor-detail', pk=pk)
        return render(request, self.template_name, {'form': form, 'object': profile, 'title': f'Modifier {profile}'})


class InstructorDeleteView(SecretaryOrAdminMixin, View):
    template_name = 'school/confirm_delete.html'

    def get(self, request, pk):
        from django.shortcuts import render
        profile = get_object_or_404(InstructorProfile, pk=pk)
        return render(request, self.template_name, {'object': profile})

    def post(self, request, pk):
        profile = get_object_or_404(InstructorProfile, pk=pk)
        profile.user.delete()
        messages.success(request, "Compte moniteur supprimé.")
        return redirect('instructor-list')


# secretaires

class SecretaryListView(AdminOnlyMixin, ListView):
    template_name = 'school/secretary_list.html'
    context_object_name = 'secretaries'
    paginate_by = 15

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.ROLE_SECRETARY).order_by('last_name')


class SecretaryCreateView(AdminOnlyMixin, View):
    template_name = 'school/secretary_form.html'

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, {'form': SecretaryCreateForm(), 'title': 'Nouvelle secrétaire'})

    def post(self, request):
        from django.shortcuts import render
        form = SecretaryCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte secrétaire créé.")
            return redirect('secretary-list')
        return render(request, self.template_name, {'form': form, 'title': 'Nouvelle secrétaire'})


class SecretaryUpdateView(AdminOnlyMixin, UpdateView):
    model = CustomUser
    form_class = SecretaryUpdateForm
    template_name = 'school/secretary_form.html'
    success_url = reverse_lazy('secretary-list')

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.ROLE_SECRETARY)


class SecretaryDeleteView(AdminOnlyMixin, View):
    template_name = 'school/confirm_delete.html'

    def get(self, request, pk):
        from django.shortcuts import render
        user = get_object_or_404(CustomUser, pk=pk, role=CustomUser.ROLE_SECRETARY)
        return render(request, self.template_name, {'object': user})

    def post(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk, role=CustomUser.ROLE_SECRETARY)
        user.delete()
        messages.success(request, "Compte secrétaire supprimé.")
        return redirect('secretary-list')


# heures

class HourPackageCreateView(SecretaryOrAdminMixin, View):
    template_name = 'school/hour_package_form.html'

    def get_student(self, pk):
        return get_object_or_404(StudentProfile, pk=pk)

    def get(self, request, pk):
        from django.shortcuts import render
        student = self.get_student(pk)
        return render(request, self.template_name, {'form': HourPackageForm(), 'student': student})

    def post(self, request, pk):
        from django.shortcuts import render
        student = self.get_student(pk)
        form = HourPackageForm(request.POST)
        if form.is_valid():
            pkg = form.save(student_profile=student, added_by=request.user)
            messages.success(request, f"{form.cleaned_data['hours']}h ajoutées au forfait de {student}.")
            return redirect('student-detail', pk=pk)
        return render(request, self.template_name, {'form': form, 'student': student})


# lecons

class LessonListView(LoginRequiredMixin, ListView):
    model = Lesson
    template_name = 'school/lesson_list.html'
    context_object_name = 'lessons'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Lesson.objects.select_related('student__user', 'instructor__user', 'vehicle')

        if user.is_student:
            qs = qs.filter(student__user=user)
        elif user.is_instructor:
            qs = qs.filter(instructor__user=user)

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        return qs.order_by('date')


class LessonCreateView(StaffMixin, CreateView):
    """Secrétaire, admin ou moniteur peut créer une leçon."""
    model = Lesson
    form_class = LessonForm
    template_name = 'school/lesson_form.html'
    success_url = reverse_lazy('lesson-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=self.request.user)
            form.fields['instructor'].initial = profile
            form.fields['instructor'].queryset = InstructorProfile.objects.filter(pk=profile.pk)
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Nouvelle leçon'
        return ctx


class LessonUpdateView(LoginRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'school/lesson_form.html'
    success_url = reverse_lazy('lesson-list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        lesson = self.get_object()
        if request.user.is_student:
            raise PermissionDenied
        # le monit peut edit que ses propres lecons pas celles des autres
        if request.user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=request.user)
            if lesson.instructor != profile:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Modifier la leçon'
        return ctx


class LessonDeleteView(LoginRequiredMixin, View):
    template_name = 'school/confirm_delete.html'

    def get_lesson(self, pk, request):
        lesson = get_object_or_404(Lesson, pk=pk)
        if request.user.is_student:
            raise PermissionDenied
        if request.user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=request.user)
            if lesson.instructor != profile:
                raise PermissionDenied
        return lesson

    def get(self, request, pk):
        from django.shortcuts import render
        lesson = self.get_lesson(pk, request)
        return render(request, self.template_name, {'object': lesson})

    def post(self, request, pk):
        lesson = self.get_lesson(pk, request)
        lesson.delete()
        messages.success(request, "Leçon supprimée.")
        return redirect('lesson-list')


# planning général

class PlanningView(SecretaryOrAdminMixin, ListView):
    model = Lesson
    template_name = 'school/planning.html'
    context_object_name = 'lessons'
    paginate_by = 30

    def get_queryset(self):
        qs = Lesson.objects.select_related(
            'student__user', 'instructor__user', 'vehicle'
        ).filter(status='scheduled').order_by('date')

        instructor_pk = self.request.GET.get('instructor')
        student_pk = self.request.GET.get('student')
        if instructor_pk:
            qs = qs.filter(instructor__pk=instructor_pk)
        if student_pk:
            qs = qs.filter(student__pk=student_pk)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['instructors'] = InstructorProfile.objects.select_related('user').order_by('user__last_name')
        ctx['students'] = StudentProfile.objects.select_related('user').order_by('user__last_name')
        ctx['selected_instructor'] = self.request.GET.get('instructor', '')
        ctx['selected_student'] = self.request.GET.get('student', '')
        return ctx


# examens

class ExamListView(StaffMixin, ListView):
    model = Exam
    template_name = 'school/exam_list.html'
    context_object_name = 'exams'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('student__user')
        result = self.request.GET.get('result')
        if result:
            qs = qs.filter(result=result)
        return qs


class ExamCreateView(StaffMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = 'school/exam_form.html'
    success_url = reverse_lazy('exam-list')


class ExamUpdateView(StaffMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = 'school/exam_form.html'
    success_url = reverse_lazy('exam-list')


class ExamDeleteView(StaffMixin, View):
    template_name = 'school/confirm_delete.html'

    def get(self, request, pk):
        from django.shortcuts import render
        exam = get_object_or_404(Exam, pk=pk)
        return render(request, self.template_name, {'object': exam})

    def post(self, request, pk):
        get_object_or_404(Exam, pk=pk).delete()
        messages.success(request, "Examen supprimé.")
        return redirect('exam-list')


# vehicules

class VehicleListView(SecretaryOrAdminMixin, ListView):
    model = Vehicle
    template_name = 'school/vehicle_list.html'
    context_object_name = 'vehicles'


class VehicleCreateView(SecretaryOrAdminMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'school/vehicle_form.html'
    success_url = reverse_lazy('vehicle-list')


class VehicleUpdateView(SecretaryOrAdminMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'school/vehicle_form.html'
    success_url = reverse_lazy('vehicle-list')


class VehicleDeleteView(SecretaryOrAdminMixin, View):
    template_name = 'school/confirm_delete.html'

    def get(self, request, pk):
        from django.shortcuts import render
        v = get_object_or_404(Vehicle, pk=pk)
        return render(request, self.template_name, {'object': v})

    def post(self, request, pk):
        get_object_or_404(Vehicle, pk=pk).delete()
        messages.success(request, "Véhicule supprimé.")
        return redirect('vehicle-list')
