from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # planning général (secrétaire / admin)
    path('planning/', views.PlanningView.as_view(), name='planning'),

    # eleves
    path('eleves/', views.StudentListView.as_view(), name='student-list'),
    path('eleves/nouveau/', views.StudentCreateView.as_view(), name='student-create'),
    path('eleves/<int:pk>/', views.StudentDetailView.as_view(), name='student-detail'),
    path('eleves/<int:pk>/modifier/', views.StudentUpdateView.as_view(), name='student-update'),
    path('eleves/<int:pk>/supprimer/', views.StudentDeleteView.as_view(), name='student-delete'),
    path('eleves/<int:pk>/forfait/', views.HourPackageCreateView.as_view(), name='hour-package-create'),

    # moniteurs
    path('moniteurs/', views.InstructorListView.as_view(), name='instructor-list'),
    path('moniteurs/nouveau/', views.InstructorCreateView.as_view(), name='instructor-create'),
    path('moniteurs/<int:pk>/', views.InstructorDetailView.as_view(), name='instructor-detail'),
    path('moniteurs/<int:pk>/modifier/', views.InstructorUpdateView.as_view(), name='instructor-update'),
    path('moniteurs/<int:pk>/supprimer/', views.InstructorDeleteView.as_view(), name='instructor-delete'),

    # secretaires (admin)
    path('secretaires/', views.SecretaryListView.as_view(), name='secretary-list'),
    path('secretaires/nouveau/', views.SecretaryCreateView.as_view(), name='secretary-create'),
    path('secretaires/<int:pk>/modifier/', views.SecretaryUpdateView.as_view(), name='secretary-update'),
    path('secretaires/<int:pk>/supprimer/', views.SecretaryDeleteView.as_view(), name='secretary-delete'),

    # lecons
    path('lecons/', views.LessonListView.as_view(), name='lesson-list'),
    path('lecons/nouvelle/', views.LessonCreateView.as_view(), name='lesson-create'),
    path('lecons/<int:pk>/modifier/', views.LessonUpdateView.as_view(), name='lesson-update'),
    path('lecons/<int:pk>/supprimer/', views.LessonDeleteView.as_view(), name='lesson-delete'),

    # examens
    path('examens/', views.ExamListView.as_view(), name='exam-list'),
    path('examens/nouveau/', views.ExamCreateView.as_view(), name='exam-create'),
    path('examens/<int:pk>/modifier/', views.ExamUpdateView.as_view(), name='exam-update'),
    path('examens/<int:pk>/supprimer/', views.ExamDeleteView.as_view(), name='exam-delete'),

    # vehicules
    path('vehicules/', views.VehicleListView.as_view(), name='vehicle-list'),
    path('vehicules/nouveau/', views.VehicleCreateView.as_view(), name='vehicle-create'),
    path('vehicules/<int:pk>/modifier/', views.VehicleUpdateView.as_view(), name='vehicle-update'),
    path('vehicules/<int:pk>/supprimer/', views.VehicleDeleteView.as_view(), name='vehicle-delete'),

    # demandes RDV
    path('demandes/', views.AppointmentRequestListView.as_view(), name='appointment-request-list'),
    path('demandes/nouvelle/', views.AppointmentRequestCreateView.as_view(), name='appointment-request-create'),
    path('demandes/<int:pk>/contre-proposition/', views.AppointmentRequestCounterView.as_view(), name='appointment-request-counter'),
    path('demandes/<int:pk>/<str:action>/', views.AppointmentRequestActionView.as_view(), name='appointment-request-action'),

        # code de la route
    path('code/', views.CodeSeriesListView.as_view(), name='code-series-list'),

    path(
        'code/nouvelle-serie/',
        views.CodeSeriesCreateView.as_view(),
        name='code-series-create'
    ),

    path(
        'code/serie/<int:pk>/modifier/',
        views.CodeSeriesUpdateView.as_view(),
        name='code-series-update'
    ),

    path(
        'code/serie/<int:pk>/question/',
        views.CodeQuestionCreateView.as_view(),
        name='code-question-create'
    ),

    path(
        'code/serie/<int:pk>/entrainement/',
        views.CodeTrainingView.as_view(),
        name='code-training'
    ),

    path(
    'code/serie/<int:pk>/supprimer/',
    views.CodeSeriesDeleteView.as_view(),
    name='code-series-delete'
    ),

    path(
    'code/serie/<int:pk>/',
    views.CodeSeriesDetailView.as_view(),
    name='code-series-detail'
    ),

    path(
        'code/question/<int:pk>/modifier/',
        views.CodeQuestionUpdateView.as_view(),
        name='code-question-update'
    ),

    path(
        'code/question/<int:pk>/supprimer/',
        views.CodeQuestionDeleteView.as_view(),
        name='code-question-delete'
    ),

    path('achat-heures/', views.StripeHourPurchaseView.as_view(), name='hour-purchase'),
    path('achat-heures/success/', views.StripeHourPurchaseSuccessView.as_view(), name='stripe-hour-purchase-success'),
    path('achat-heures/cancel/', views.StripeHourPurchaseCancelView.as_view(), name='stripe-hour-purchase-cancel'),
]
