from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from .models import CustomUser, StudentProfile, InstructorProfile, HourPackage, Lesson, Exam, Vehicle


def _input():
    return 'form-control'

def _select():
    return 'form-select'


# comptes élèves

class StudentCreateForm(forms.Form):
    username   = forms.CharField(max_length=150, label="Identifiant",      widget=forms.TextInput(attrs={'class': _input()}))
    first_name = forms.CharField(max_length=100, label="Prénom",           widget=forms.TextInput(attrs={'class': _input()}))
    last_name  = forms.CharField(max_length=100, label="Nom",              widget=forms.TextInput(attrs={'class': _input()}))
    email      = forms.EmailField(label="Email",                           widget=forms.EmailInput(attrs={'class': _input()}))
    password1  = forms.CharField(label="Mot de passe",                    widget=forms.PasswordInput(attrs={'class': _input()}))
    password2  = forms.CharField(label="Confirmer le mot de passe",       widget=forms.PasswordInput(attrs={'class': _input()}))
    phone      = forms.CharField(max_length=20, label="Téléphone",        widget=forms.TextInput(attrs={'class': _input()}))
    birth_date = forms.DateField(label="Date de naissance",               widget=forms.DateInput(attrs={'type': 'date', 'class': _input()}))
    address    = forms.CharField(label="Adresse",                         widget=forms.Textarea(attrs={'class': _input(), 'rows': 2}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = CustomUser.objects.create_user(
            username=d['username'], email=d['email'], password=d['password1'],
            first_name=d['first_name'], last_name=d['last_name'], role=CustomUser.ROLE_STUDENT,
        )
        StudentProfile.objects.create(user=user, phone=d['phone'], birth_date=d['birth_date'], address=d['address'])
        return user


class StudentUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Prénom",    widget=forms.TextInput(attrs={'class': _input()}))
    last_name  = forms.CharField(max_length=100, label="Nom",       widget=forms.TextInput(attrs={'class': _input()}))
    email      = forms.EmailField(label="Email",                    widget=forms.EmailInput(attrs={'class': _input()}))
    phone      = forms.CharField(max_length=20, label="Téléphone",  widget=forms.TextInput(attrs={'class': _input()}))
    birth_date = forms.DateField(label="Date de naissance",         widget=forms.DateInput(attrs={'type': 'date', 'class': _input()}))
    address    = forms.CharField(label="Adresse",                   widget=forms.Textarea(attrs={'class': _input(), 'rows': 2}))

    def __init__(self, *args, student_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile = student_profile
        if student_profile:
            self.fields['first_name'].initial = student_profile.user.first_name
            self.fields['last_name'].initial  = student_profile.user.last_name
            self.fields['email'].initial      = student_profile.user.email
            self.fields['phone'].initial      = student_profile.phone
            self.fields['birth_date'].initial = student_profile.birth_date
            self.fields['address'].initial    = student_profile.address

    def save(self):
        d = self.cleaned_data
        user = self._profile.user
        user.first_name, user.last_name, user.email = d['first_name'], d['last_name'], d['email']
        user.save()
        self._profile.phone      = d['phone']
        self._profile.birth_date = d['birth_date']
        self._profile.address    = d['address']
        self._profile.save()
        return self._profile


# comptes moniteurs

class InstructorCreateForm(forms.Form):
    username   = forms.CharField(max_length=150, label="Identifiant",          widget=forms.TextInput(attrs={'class': _input()}))
    first_name = forms.CharField(max_length=100, label="Prénom",               widget=forms.TextInput(attrs={'class': _input()}))
    last_name  = forms.CharField(max_length=100, label="Nom",                  widget=forms.TextInput(attrs={'class': _input()}))
    email      = forms.EmailField(label="Email",                               widget=forms.EmailInput(attrs={'class': _input()}))
    password1  = forms.CharField(label="Mot de passe",                        widget=forms.PasswordInput(attrs={'class': _input()}))
    password2  = forms.CharField(label="Confirmer le mot de passe",           widget=forms.PasswordInput(attrs={'class': _input()}))
    phone      = forms.CharField(max_length=20, label="Téléphone",            widget=forms.TextInput(attrs={'class': _input()}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = CustomUser.objects.create_user(
            username=d['username'], email=d['email'], password=d['password1'],
            first_name=d['first_name'], last_name=d['last_name'], role=CustomUser.ROLE_INSTRUCTOR,
        )
        InstructorProfile.objects.create(user=user, phone=d['phone'])
        return user


class InstructorUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Prénom",   widget=forms.TextInput(attrs={'class': _input()}))
    last_name  = forms.CharField(max_length=100, label="Nom",      widget=forms.TextInput(attrs={'class': _input()}))
    email      = forms.EmailField(label="Email",                   widget=forms.EmailInput(attrs={'class': _input()}))
    phone      = forms.CharField(max_length=20, label="Téléphone", widget=forms.TextInput(attrs={'class': _input()}))

    def __init__(self, *args, instructor_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile = instructor_profile
        if instructor_profile:
            self.fields['first_name'].initial = instructor_profile.user.first_name
            self.fields['last_name'].initial  = instructor_profile.user.last_name
            self.fields['email'].initial      = instructor_profile.user.email
            self.fields['phone'].initial      = instructor_profile.phone

    def save(self):
        d = self.cleaned_data
        user = self._profile.user
        user.first_name, user.last_name, user.email = d['first_name'], d['last_name'], d['email']
        user.save()
        self._profile.phone = d['phone']
        self._profile.save()
        return self._profile


# comptes secrétaires

class SecretaryCreateForm(forms.Form):
    username   = forms.CharField(max_length=150, label="Identifiant",    widget=forms.TextInput(attrs={'class': _input()}))
    first_name = forms.CharField(max_length=100, label="Prénom",         widget=forms.TextInput(attrs={'class': _input()}))
    last_name  = forms.CharField(max_length=100, label="Nom",            widget=forms.TextInput(attrs={'class': _input()}))
    email      = forms.EmailField(label="Email",                         widget=forms.EmailInput(attrs={'class': _input()}))
    password1  = forms.CharField(label="Mot de passe",                  widget=forms.PasswordInput(attrs={'class': _input()}))
    password2  = forms.CharField(label="Confirmer le mot de passe",     widget=forms.PasswordInput(attrs={'class': _input()}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        return CustomUser.objects.create_user(
            username=d['username'], email=d['email'], password=d['password1'],
            first_name=d['first_name'], last_name=d['last_name'], role=CustomUser.ROLE_SECRETARY,
        )


class SecretaryUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': _input()}),
            'last_name':  forms.TextInput(attrs={'class': _input()}),
            'email':      forms.EmailInput(attrs={'class': _input()}),
        }


# heures

class HourPackageForm(forms.Form):
    hours = forms.IntegerField(min_value=1, max_value=100, label="Nombre d'heures à ajouter",
                               widget=forms.NumberInput(attrs={'class': _input()}))
    notes = forms.CharField(max_length=200, required=False, label="Notes (facultatif)",
                            widget=forms.TextInput(attrs={'class': _input()}))

    def save(self, student_profile, added_by):
        return HourPackage.objects.create(
            student=student_profile,
            minutes=self.cleaned_data['hours'] * 60,
            notes=self.cleaned_data.get('notes', ''),
            added_by=added_by,
        )


# lecons

class LessonForm(forms.ModelForm):
    date = forms.DateTimeField(
        label="Date et heure",
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': _input()}),
    )

    class Meta:
        model = Lesson
        fields = ['student', 'instructor', 'vehicle', 'date', 'duration', 'status', 'notes']
        widgets = {
            'student':    forms.Select(attrs={'class': _select()}),
            'instructor': forms.Select(attrs={'class': _select()}),
            'vehicle':    forms.Select(attrs={'class': _select()}),
            'duration':   forms.NumberInput(attrs={'class': _input()}),
            'status':     forms.Select(attrs={'class': _select()}),
            'notes':      forms.Textarea(attrs={'class': _input(), 'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        instructor = cleaned.get('instructor')
        date       = cleaned.get('date')
        duration   = cleaned.get('duration', 60)
        student    = cleaned.get('student')
        status     = cleaned.get('status', 'scheduled')

        if instructor and date and status != 'cancelled':
            end_time = date + timedelta(minutes=duration)
            overlap_qs = Lesson.objects.filter(
                instructor=instructor,
                status='scheduled',
                date__lt=end_time,
            ).exclude(pk=self.instance.pk or None)

            for lesson in overlap_qs:
                if lesson.date + timedelta(minutes=lesson.duration) > date:
                    raise ValidationError(
                        f"Le moniteur {instructor} a déjà une leçon planifiée "
                        f"le {lesson.date.strftime('%d/%m/%Y à %H:%M')} "
                        f"({lesson.duration} min). Choisissez un autre horaire."
                    )

        if student and duration and status != 'cancelled':
            available = student.available_minutes()
            if self.instance.pk and self.instance.status != 'cancelled':
                available += self.instance.duration
            if available < duration:
                h, m = divmod(available, 60)
                dispo = f"{h}h{m:02d}" if m else f"{h}h"
                raise ValidationError(
                    f"L'élève ne dispose que de {dispo} de cours disponibles. "
                    f"Veuillez d'abord recharger son forfait."
                )

        return cleaned


# examens

class ExamForm(forms.ModelForm):
    date = forms.DateField(
        label="Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': _input()}),
    )

    class Meta:
        model = Exam
        fields = ['student', 'exam_type', 'date', 'result', 'score', 'notes']
        widgets = {
            'student':   forms.Select(attrs={'class': _select()}),
            'exam_type': forms.Select(attrs={'class': _select()}),
            'result':    forms.Select(attrs={'class': _select()}),
            'score':     forms.NumberInput(attrs={'class': _input()}),
            'notes':     forms.Textarea(attrs={'class': _input(), 'rows': 2}),
        }


# vehicules

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['name', 'transmission']
        widgets = {
            'name':         forms.TextInput(attrs={'class': _input()}),
            'transmission': forms.Select(attrs={'class': _select()}),
        }
