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
from django.conf import settings
from django.utils import timezone

from .models import (
    CustomUser, StudentProfile, InstructorProfile,
    HourPackage, Vehicle, Lesson, Exam, AppointmentRequest,
    CodeSeries, CodeQuestion, CodeAnswer, Payment,
)

from .forms import (
    StudentCreateForm, StudentUpdateForm,
    InstructorCreateForm, InstructorUpdateForm,
    SecretaryCreateForm, SecretaryUpdateForm,
    HourPackageForm, LessonForm,
    ExamForm, VehicleForm,
    AppointmentRequestForm, AppointmentCounterForm,
    CodeSeriesForm, CodeQuestionForm, CodeAnswerForm, HourPurchaseForm,
    StripeHourPurchaseForm,
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
                Q(phone__icontains=q)
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
    
class AppointmentRequestCreateView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_STUDENT]
    template_name = 'school/appointment_request_form.html'

    def get(self, request):
        from django.shortcuts import render

        form = AppointmentRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        from django.shortcuts import render

        form = AppointmentRequestForm(request.POST)

        if form.is_valid():
            profile = get_object_or_404(StudentProfile, user=request.user)

            request_type = form.cleaned_data['request_type']
            duration = form.cleaned_data.get('duration', 60)

            if request_type == 'lesson' and profile.available_minutes() < duration:
                messages.error(
                    request,
                    "Votre forfait est insuffisant pour demander ce rendez-vous. Contactez une secrétaire pour acheter des heures."
                )
                return render(request, self.template_name, {'form': form})

            if request_type == 'hours':
                hours_requested = form.cleaned_data.get('hours_requested')

                if hours_requested:
                    message = (
                        f"Demande d'achat de {hours_requested}h. "
                        f"{form.cleaned_data.get('message', '')}"
                    )
                else:
                    message = form.cleaned_data.get('message', '')
            else:
                message = form.cleaned_data.get('message', '')

            AppointmentRequest.objects.create(
                student=profile,
                request_type=request_type,
                instructor=form.cleaned_data.get('instructor'),
                secretary=form.cleaned_data.get('secretary'),
                proposed_date=form.cleaned_data['proposed_date'],
                duration=duration,
                message=message,
                status='pending_instructor'
                if request_type == 'lesson'
                else 'pending_secretary',
                last_proposed_by=request.user,
            )

            if request_type == 'lesson':
                messages.success(
                    request,
                    "Demande de rendez-vous envoyée au moniteur."
                )

            elif request_type == 'hours':
                messages.success(
                    request,
                    "Demande d'achat d'heures envoyée à la secrétaire."
                )

            elif request_type == 'secretary_meeting':
                messages.success(
                    request,
                    "Demande de rendez-vous envoyée à la secrétaire."
                )

            return redirect('appointment-request-list')

        return render(request, self.template_name, {'form': form})


class AppointmentRequestListView(LoginRequiredMixin, ListView):
    model = AppointmentRequest
    template_name = 'school/appointment_request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        user = self.request.user

        qs = AppointmentRequest.objects.select_related(
            'student__user',
            'instructor__user',
            'last_proposed_by',
        ).order_by('-updated_at')

        if user.is_student:
            return qs.filter(student__user=user)

        if user.is_instructor:
            return qs.filter(instructor__user=user)

        if user.is_secretary or user.is_admin_role:
            return qs

        return AppointmentRequest.objects.none()


class AppointmentRequestActionView(LoginRequiredMixin, View):
    def post(self, request, pk, action):
        req = get_object_or_404(AppointmentRequest, pk=pk)

        is_student_owner = (
            request.user.is_student
            and req.student.user == request.user
        )

        is_instructor_owner = (
            request.user.is_instructor
            and req.instructor
            and req.instructor.user == request.user
        )

        is_secretary = request.user.role in ['secretary', 'admin']

        if not is_student_owner and not is_instructor_owner and not is_secretary:
            raise PermissionDenied

        if action == 'accept':
            req.status = 'accepted'
            req.save()

            if req.request_type == 'lesson':
                Lesson.objects.create(
                    student=req.student,
                    instructor=req.instructor,
                    date=req.proposed_date,
                    duration=req.duration,
                    status='scheduled',
                    notes=f"Créée depuis une demande de RDV acceptée. {req.message}",
                )

                messages.success(
                    request,
                    "Demande acceptée. Le rendez-vous a été créé."
                )

            elif req.request_type == 'hours':
                import re

                hours = 0

                match = re.search(r'(\d+)h', req.message)

                if match:
                    hours = int(match.group(1))

                if hours > 0:
                    HourPackage.objects.create(
                        student=req.student,
                        minutes=hours * 60,
                        notes="Ajout depuis une demande d'achat d'heures acceptée",
                        added_by=request.user,
                    )

                    messages.success(
                        request,
                        f"{hours}h ont été ajoutées au forfait de l'élève."
                    )
                else:
                    messages.warning(
                        request,
                        "Impossible de récupérer le nombre d'heures demandé."
                    )

            return redirect('appointment-request-list')

        if action == 'refuse':
            req.status = 'refused'
            req.save()

            messages.success(request, "Demande refusée.")
            return redirect('appointment-request-list')

        raise PermissionDenied


class AppointmentRequestCounterView(LoginRequiredMixin, View):
    template_name = 'school/appointment_request_counter.html'

    def get_request(self, request, pk):
        req = get_object_or_404(AppointmentRequest, pk=pk)

        if request.user.is_student and req.student.user == request.user:
            return req

        if request.user.is_instructor and req.instructor.user == request.user:
            return req

        raise PermissionDenied

    def get(self, request, pk):
        from django.shortcuts import render
        req = self.get_request(request, pk)

        form = AppointmentCounterForm(initial={
            'proposed_date': req.proposed_date,
            'duration': req.duration,
            'message': req.message,
        })

        return render(request, self.template_name, {'form': form, 'request_obj': req})

    def post(self, request, pk):
        from django.shortcuts import render
        req = self.get_request(request, pk)
        form = AppointmentCounterForm(request.POST)

        if form.is_valid():
            req.proposed_date = form.cleaned_data['proposed_date']
            req.duration = form.cleaned_data['duration']
            req.message = form.cleaned_data['message']
            req.last_proposed_by = request.user

            if request.user.is_student:
                req.status = 'pending_instructor'
            elif request.user.is_instructor:
                req.status = 'pending_student'

            req.save()
            messages.success(request, "Contre-proposition envoyée.")
            return redirect('appointment-request-list')

        return render(request, self.template_name, {'form': form, 'request_obj': req})
    
# entrainement code

class CodeSeriesListView(LoginRequiredMixin, ListView):
    model = CodeSeries
    template_name = 'school/code_series_list.html'
    context_object_name = 'series_list'

    def get_queryset(self):
        qs = CodeSeries.objects.select_related('instructor__user').prefetch_related('questions')

        if self.request.user.is_student:
            return qs.filter(is_published=True).order_by('-created_at')

        if self.request.user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=self.request.user)
            return qs.filter(instructor=profile).order_by('-created_at')

        if self.request.user.is_secretary or self.request.user.is_admin_role:
            return qs.order_by('-created_at')

        return CodeSeries.objects.none()


class CodeSeriesCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]
    model = CodeSeries
    form_class = CodeSeriesForm
    template_name = 'school/code_series_form.html'
    success_url = reverse_lazy('code-series-list')

    def form_valid(self, form):
        form.instance.instructor = get_object_or_404(
            InstructorProfile,
            user=self.request.user
        )
        messages.success(self.request, "Série de questions créée.")
        return super().form_valid(form)


class CodeSeriesUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]
    model = CodeSeries
    form_class = CodeSeriesForm
    template_name = 'school/code_series_form.html'
    success_url = reverse_lazy('code-series-list')

    def get_queryset(self):
        profile = get_object_or_404(InstructorProfile, user=self.request.user)
        return CodeSeries.objects.filter(instructor=profile)

    def form_valid(self, form):
        messages.success(self.request, "Série mise à jour.")
        return super().form_valid(form)


class CodeQuestionCreateView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]
    template_name = 'school/code_question_form.html'

    def get_series(self, request, pk):
        profile = get_object_or_404(InstructorProfile, user=request.user)
        return get_object_or_404(CodeSeries, pk=pk, instructor=profile)

    def get(self, request, pk):
        from django.shortcuts import render

        series = self.get_series(request, pk)
        return render(request, self.template_name, {
            'series': series,
            'question_form': CodeQuestionForm(),
            'answer_forms': [CodeAnswerForm(prefix=str(i)) for i in range(4)],
        })

    def post(self, request, pk):
        from django.shortcuts import render

        series = self.get_series(request, pk)
        question_form = CodeQuestionForm(request.POST)
        answer_forms = [CodeAnswerForm(request.POST, prefix=str(i)) for i in range(4)]

        if question_form.is_valid() and all(form.is_valid() for form in answer_forms):
            correct_count = sum(1 for form in answer_forms if form.cleaned_data.get('is_correct'))

            if correct_count == 0:
                messages.error(request, "Il faut cocher au moins une bonne réponse.")
                return render(request, self.template_name, {
                    'series': series,
                    'question_form': question_form,
                    'answer_forms': answer_forms,
                })

            question = question_form.save(commit=False)
            question.series = series
            question.save()

            for form in answer_forms:
                text = form.cleaned_data.get('text')
                if text:
                    answer = form.save(commit=False)
                    answer.question = question
                    answer.save()

            messages.success(request, "Question ajoutée à la série.")
            return redirect('code-series-list')

        return render(request, self.template_name, {
            'series': series,
            'question_form': question_form,
            'answer_forms': answer_forms,
        })


class CodeTrainingView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_STUDENT]
    template_name = 'school/code_training.html'

    def get(self, request, pk):
        from django.shortcuts import render

        series = get_object_or_404(
            CodeSeries.objects.prefetch_related('questions__answers'),
            pk=pk,
            is_published=True,
        )

        return render(request, self.template_name, {'series': series})

    def post(self, request, pk):
        from django.shortcuts import render

        series = get_object_or_404(
            CodeSeries.objects.prefetch_related('questions__answers'),
            pk=pk,
            is_published=True,
        )

        questions = series.questions.all()
        total = questions.count()
        score = 0
        corrections = []

        for question in questions:
            selected_ids = set(
                int(answer_id)
                for answer_id in request.POST.getlist(f'question_{question.pk}')
            )

            correct_ids = set(
                question.answers.filter(is_correct=True).values_list('pk', flat=True)
            )

            is_correct = selected_ids == correct_ids

            if is_correct:
                score += 1

            corrections.append({
                'question': question,
                'selected_ids': selected_ids,
                'correct_answers': question.answers.filter(is_correct=True),
                'is_correct': is_correct,
            })

        return render(request, 'school/code_result.html', {
            'series': series,
            'score': score,
            'total': total,
            'corrections': corrections,
        })
    
class CodeSeriesDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]

    model = CodeSeries
    template_name = 'school/confirm_delete.html'
    success_url = reverse_lazy('code-series-list')

    def get_queryset(self):
        profile = get_object_or_404(
            InstructorProfile,
            user=self.request.user
        )

        return CodeSeries.objects.filter(instructor=profile)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Série supprimée.")
        return super().delete(request, *args, **kwargs)

class CodeSeriesDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = [
        CustomUser.ROLE_INSTRUCTOR,
        CustomUser.ROLE_SECRETARY,
        CustomUser.ROLE_ADMIN,
    ]

    model = CodeSeries
    template_name = 'school/code_series_detail.html'
    context_object_name = 'series'

    def get_queryset(self):
        qs = CodeSeries.objects.prefetch_related('questions__answers')

        if self.request.user.is_instructor:
            profile = get_object_or_404(InstructorProfile, user=self.request.user)
            return qs.filter(instructor=profile)

        return qs


class CodeQuestionUpdateView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]
    template_name = 'school/code_question_form.html'

    def get_question(self, request, pk):
        profile = get_object_or_404(InstructorProfile, user=request.user)

        return get_object_or_404(
            CodeQuestion.objects.select_related('series__instructor'),
            pk=pk,
            series__instructor=profile,
        )

    def get(self, request, pk):
        from django.shortcuts import render

        question = self.get_question(request, pk)
        answers = list(question.answers.all())

        while len(answers) < 4:
            answers.append(None)

        return render(request, self.template_name, {
            'series': question.series,
            'question': question,
            'question_form': CodeQuestionForm(instance=question),
            'answer_forms': [
                CodeAnswerForm(instance=answer, prefix=str(i))
                for i, answer in enumerate(answers)
            ],
        })

    def post(self, request, pk):
        from django.shortcuts import render

        question = self.get_question(request, pk)
        answers = list(question.answers.all())

        while len(answers) < 4:
            answers.append(None)

        question_form = CodeQuestionForm(request.POST, instance=question)

        answer_forms = [
            CodeAnswerForm(request.POST, instance=answer, prefix=str(i))
            for i, answer in enumerate(answers)
        ]

        if question_form.is_valid() and all(form.is_valid() for form in answer_forms):
            correct_count = sum(
                1 for form in answer_forms
                if form.cleaned_data.get('text') and form.cleaned_data.get('is_correct')
            )

            if correct_count == 0:
                messages.error(request, "Il faut cocher au moins une bonne réponse.")
                return render(request, self.template_name, {
                    'series': question.series,
                    'question': question,
                    'question_form': question_form,
                    'answer_forms': answer_forms,
                })

            question_form.save()

            for form in answer_forms:
                text = form.cleaned_data.get('text')

                if text:
                    answer = form.save(commit=False)
                    answer.question = question
                    answer.save()
                elif form.instance.pk:
                    form.instance.delete()

            messages.success(request, "Question modifiée.")
            return redirect('code-series-detail', pk=question.series.pk)

        return render(request, self.template_name, {
            'series': question.series,
            'question': question,
            'question_form': question_form,
            'answer_forms': answer_forms,
        })


class CodeQuestionDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = [CustomUser.ROLE_INSTRUCTOR]
    model = CodeQuestion
    template_name = 'school/confirm_delete.html'

    def get_queryset(self):
        profile = get_object_or_404(InstructorProfile, user=self.request.user)
        return CodeQuestion.objects.filter(series__instructor=profile)

    def get_success_url(self):
        return reverse_lazy('code-series-detail', kwargs={'pk': self.object.series.pk})
    
class StripeHourPurchaseView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_STUDENT]
    template_name = 'school/stripe_hour_purchase.html'

    def get(self, request):
        from django.shortcuts import render

        price_per_hour = settings.STRIPE_PRICE_PER_HOUR_CENTS

        packs = [
            {
                'hours': 1,
                'price_cents': price_per_hour,
                'price_euros': price_per_hour / 100,
            },
            {
                'hours': 5,
                'price_cents': price_per_hour * 5,
                'price_euros': (price_per_hour * 5) / 100,
            },
            {
                'hours': 10,
                'price_cents': price_per_hour * 10,
                'price_euros': (price_per_hour * 10) / 100,
            },
            {
                'hours': 20,
                'price_cents': price_per_hour * 20,
                'price_euros': (price_per_hour * 20) / 100,
            },
        ]

        return render(request, self.template_name, {
            'form': StripeHourPurchaseForm(),
            'packs': packs,
            'price_per_hour': price_per_hour,
        })

    def post(self, request):
        import stripe

        form = StripeHourPurchaseForm(request.POST)

        if not form.is_valid():
            from django.shortcuts import render
            return render(request, self.template_name, {'form': form})

        profile = get_object_or_404(StudentProfile, user=request.user)

        hours = int(form.cleaned_data['hours'])
        amount_cents = hours * settings.STRIPE_PRICE_PER_HOUR_CENTS

        payment = Payment.objects.create(
            student=profile,
            hours=hours,
            amount_cents=amount_cents,
            currency='eur',
            status='pending',
        )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Forfait auto-école - {hours}h de conduite',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }
            ],
            success_url=request.build_absolute_uri(
                reverse('stripe-hour-purchase-success')
            ) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(
                reverse('stripe-hour-purchase-cancel')
            ),
            metadata={
                'payment_id': payment.pk,
                'student_id': profile.pk,
                'hours': hours,
            },
        )

        payment.stripe_session_id = session.id
        payment.save()

        return redirect(session.url)


class StripeHourPurchaseSuccessView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_STUDENT]

    def get(self, request):
        import stripe

        session_id = request.GET.get('session_id')

        if not session_id:
            messages.error(request, "Session Stripe introuvable.")
            return redirect('hour-purchase')

        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)

        payment = get_object_or_404(
            Payment,
            stripe_session_id=session_id,
            student__user=request.user,
        )

        if payment.status == 'paid':
            messages.info(request, "Ce paiement a déjà été validé.")
            return redirect('dashboard')

        if session.payment_status == 'paid':
            payment.status = 'paid'
            payment.stripe_payment_intent = session.payment_intent or ''
            payment.paid_at = timezone.now()
            payment.save()

            HourPackage.objects.create(
                student=payment.student,
                minutes=payment.hours * 60,
                added_by=request.user,
                notes=f"Achat Stripe Checkout - {payment.amount_display()}",
            )

            messages.success(
                request,
                f"Paiement validé : {payment.hours}h ajoutées à votre forfait."
            )
            return redirect('dashboard')

        messages.error(request, "Le paiement n'a pas encore été confirmé.")
        return redirect('hour-purchase')


class StripeHourPurchaseCancelView(RoleRequiredMixin, View):
    allowed_roles = [CustomUser.ROLE_STUDENT]

    def get(self, request):
        messages.warning(request, "Paiement annulé.")
        return redirect('hour-purchase')
