from django.contrib import admin
from .models import (
    Study, Site, Patient, Visit, Form, Query, 
    LabData, CodingIssue, ExcelUpload, AIInsight, 
    Alert, DQIHistory
)

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['study_id', 'study_name', 'protocol_number', 'phase', 'created_at']
    search_fields = ['study_id', 'study_name', 'protocol_number']
    list_filter = ['phase', 'therapeutic_area']

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['site_number', 'site_name', 'study', 'country', 'dqi_score', 'status']
    search_fields = ['site_number', 'site_name', 'country']
    list_filter = ['status', 'study', 'country']
    readonly_fields = ['dqi_score', 'last_calculated']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('study')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'site', 'status', 'is_clean', 'issues_count', 'enrollment_date']
    search_fields = ['patient_id', 'screening_number']
    list_filter = ['status', 'is_clean', 'site__study']
    readonly_fields = ['is_clean', 'issues_count', 'last_updated']

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['patient', 'visit_number', 'visit_name', 'scheduled_date', 'is_completed', 'is_missing']
    list_filter = ['is_completed', 'is_missing']
    search_fields = ['patient__patient_id', 'visit_name']

@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ['query_id', 'patient', 'query_type', 'severity', 'opened_date', 'days_open', 'is_resolved']
    list_filter = ['is_resolved', 'query_type', 'severity']
    search_fields = ['query_id', 'query_text', 'patient__patient_id']
    readonly_fields = ['days_open']

@admin.register(LabData)
class LabDataAdmin(admin.ModelAdmin):
    list_display = ['patient', 'test_name', 'lab_name', 'is_missing', 'collection_date']
    list_filter = ['is_missing', 'lab_name']
    search_fields = ['patient__patient_id', 'test_name']

@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'study', 'file_type', 'uploaded_at', 'processed', 'rows_processed']
    list_filter = ['file_type', 'processed', 'study']
    readonly_fields = ['uploaded_at', 'processed_at', 'rows_processed', 'errors']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['site', 'alert_type', 'severity', 'is_resolved', 'created_at']
    list_filter = ['severity', 'is_resolved', 'alert_type']
    search_fields = ['site__site_number', 'message']

@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'site', 'patient', 'created_at']
    list_filter = ['insight_type']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'cache_key']

@admin.register(DQIHistory)
class DQIHistoryAdmin(admin.ModelAdmin):
    list_display = ['site', 'dqi_score', 'calculated_at']
    list_filter = ['site__study']
    readonly_fields = ['calculated_at']

@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['form_name', 'visit', 'is_required', 'is_complete', 'is_verified']
    list_filter = ['is_complete', 'is_verified', 'is_required']

@admin.register(CodingIssue)
class CodingIssueAdmin(admin.ModelAdmin):
    list_display = ['patient', 'issue_type', 'term', 'is_resolved', 'created_at']
    list_filter = ['issue_type', 'is_resolved']
    search_fields = ['term', 'patient__patient_id']