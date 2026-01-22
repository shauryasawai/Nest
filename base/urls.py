from django.urls import path
from . import views

app_name = 'base'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('studies/', views.study_list, name='study_list'),
    path('sites/', views.site_list, name='site_list'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('upload/', views.upload_excel, name='upload'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('api/calculate-dqi/<int:site_id>/', views.calculate_dqi, name='calculate_dqi'),
    path('api/generate-insight/<int:site_id>/', views.generate_ai_insight, name='generate_ai_insight'),
]