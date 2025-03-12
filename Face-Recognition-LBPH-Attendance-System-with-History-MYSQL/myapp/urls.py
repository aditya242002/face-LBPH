from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('faceRegistration/', views.faceRegistration, name='faceRegistration'),
    path('adminpanel/', views.adminpanel, name='adminpanel'),
    path('admindashboard/', views.admindashboard, name='admindashboard'),
    path('attendancehistory/', views.attendancehistory, name='attendancehistory'),
    path('student_details/', views.student_details, name='student_details'),
]