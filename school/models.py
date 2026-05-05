from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum


class CustomUser(AbstractUser):
    ROLE_STUDENT = 'student'
    ROLE_INSTRUCTOR = 'instructor'
    ROLE_SECRETARY = 'secretary'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Élève'),
        (ROLE_INSTRUCTOR, 'Moniteur'),
        (ROLE_SECRETARY, 'Secrétaire'),
        (ROLE_ADMIN, 'Administrateur'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT, verbose_name="Rôle")

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_instructor(self):
        return self.role == self.ROLE_INSTRUCTOR

    @property
    def is_secretary(self):
        return self.role == self.ROLE_SECRETARY

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_staff_member(self):
        return self.role in (self.ROLE_SECRETARY, self.ROLE_ADMIN)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    birth_date = models.DateField(verbose_name="Date de naissance")
    address = models.TextField(verbose_name="Adresse")

    class Meta:
        verbose_name = "Profil élève"
        verbose_name_plural = "Profils élèves"

    def total_minutes_purchased(self):
        return self.hour_packages.aggregate(total=Sum('minutes'))['total'] or 0

    def total_minutes_used(self):
        return self.lessons.filter(
            status__in=['scheduled', 'done']
        ).aggregate(total=Sum('duration'))['total'] or 0

    def available_minutes(self):
        return self.total_minutes_purchased() - self.total_minutes_used()

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class InstructorProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='instructor_profile')
    phone = models.CharField(max_length=20, verbose_name="Téléphone")

    class Meta:
        verbose_name = "Profil moniteur"
        verbose_name_plural = "Profils moniteurs"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class HourPackage(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='hour_packages', verbose_name="Élève")
    minutes = models.PositiveIntegerField(verbose_name="Durée (en minutes)")
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name="Acheté le")
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='packages_added', verbose_name="Ajouté par")
    notes = models.CharField(max_length=200, blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Forfait d'heures"
        verbose_name_plural = "Forfaits d'heures"
        ordering = ['-purchased_at']

    def hours_display(self):
        h, m = divmod(self.minutes, 60)
        return f"{h}h{m:02d}" if m else f"{h}h"

    def __str__(self):
        return f"{self.student} – {self.hours_display()}"


class Vehicle(models.Model):
    TRANSMISSION_CHOICES = [
        ('manual', 'Manuelle'),
        ('auto', 'Automatique'),
    ]
    name = models.CharField(max_length=100, verbose_name="Nom du véhicule")
    transmission = models.CharField(max_length=10, choices=TRANSMISSION_CHOICES, default='manual', verbose_name="Boîte")

    class Meta:
        verbose_name = "Véhicule"
        verbose_name_plural = "Véhicules"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_transmission_display()})"


class Lesson(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Planifiée'),
        ('done', 'Effectuée'),
        ('cancelled', 'Annulée'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='lessons', verbose_name="Élève")
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.SET_NULL, null=True, related_name='lessons', verbose_name="Moniteur")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons', verbose_name="Véhicule")
    date = models.DateTimeField(verbose_name="Date et heure")
    duration = models.PositiveIntegerField(default=60, verbose_name="Durée (min)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Statut")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Leçon"
        verbose_name_plural = "Leçons"
        ordering = ['date']

    def __str__(self):
        return f"{self.student} avec {self.instructor} le {self.date.strftime('%d/%m/%Y %H:%M')}"


class Exam(models.Model):
    TYPE_CHOICES = [
        ('theory', 'Code de la route'),
        ('practical', 'Permis B'),
    ]
    RESULT_CHOICES = [
        ('pass', 'Reçu'),
        ('fail', 'Échoué'),
        ('pending', 'En attente'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='exams', verbose_name="Élève")
    exam_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type")
    date = models.DateField(verbose_name="Date")
    result = models.CharField(max_length=10, choices=RESULT_CHOICES, default='pending', verbose_name="Résultat")
    score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Score (/40 pour le code)")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Examens"
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} – {self.get_exam_type_display()} ({self.date})"
