from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Study(models.Model):
    study_id = models.CharField(max_length=50, unique=True)
    study_name = models.CharField(max_length=200)
    protocol_number = models.CharField(max_length=100)
    phase = models.CharField(max_length=20, choices=[
        ('I', 'Phase I'),
        ('II', 'Phase II'),
        ('III', 'Phase III'),
        ('IV', 'Phase IV')
    ], default='III')
    therapeutic_area = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.study_id} - {self.study_name}"
    
    def get_overall_dqi(self):
        sites = self.sites.all()
        if not sites:
            return 0
        return sum(site.dqi_score for site in sites) / len(sites)
    
    def get_clean_patients_percentage(self):
        total_patients = sum(site.patients.count() for site in self.sites.all())
        if total_patients == 0:
            return 0
        clean_patients = sum(site.patients.filter(is_clean=True).count() for site in self.sites.all())
        return (clean_patients / total_patients) * 100
    
    class Meta:
        verbose_name_plural = "Studies"
        ordering = ['-created_at']


class Site(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='sites')
    site_number = models.CharField(max_length=20)
    site_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    investigator_name = models.CharField(max_length=200)
    coordinator_name = models.CharField(max_length=200, blank=True)
    coordinator_email = models.EmailField(blank=True)
    dqi_score = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('closed', 'Closed')
    ], default='active')
    last_calculated = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Site {self.site_number} - {self.site_name}"
    
    def get_dqi_status(self):
        if self.dqi_score >= 90:
            return 'excellent'
        elif self.dqi_score >= 75:
            return 'good'
        elif self.dqi_score >= 60:
            return 'fair'
        elif self.dqi_score >= 45:
            return 'poor'
        else:
            return 'critical'
    
    def get_metrics(self):
        patients = self.patients.all()
        total_patients = patients.count()
        
        if total_patients == 0:
            return {
                'total_patients': 0,
                'clean_patients': 0,
                'open_queries': 0,
                'avg_query_age': 0,
                'completion_rate': 0
            }
        
        clean_patients = patients.filter(is_clean=True).count()
        open_queries = Query.objects.filter(patient__site=self, is_resolved=False).count()
        avg_query_age = Query.objects.filter(patient__site=self, is_resolved=False).aggregate(
            models.Avg('days_open')
        )['days_open__avg'] or 0
        
        total_visits = Visit.objects.filter(patient__site=self).count()
        completed_visits = Visit.objects.filter(patient__site=self, is_completed=True).count()
        completion_rate = (completed_visits / total_visits * 100) if total_visits > 0 else 0
        
        return {
            'total_patients': total_patients,
            'clean_patients': clean_patients,
            'open_queries': open_queries,
            'avg_query_age': round(avg_query_age, 1),
            'completion_rate': round(completion_rate, 1)
        }
    
    class Meta:
        unique_together = ['study', 'site_number']
        ordering = ['site_number']


class Patient(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='patients')
    patient_id = models.CharField(max_length=50)
    screening_number = models.CharField(max_length=50, blank=True)
    enrollment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('clean', 'Clean'),
        ('minor_issues', 'Minor Issues'),
        ('major_issues', 'Major Issues'),
        ('critical', 'Critical')
    ], default='minor_issues')
    is_clean = models.BooleanField(default=False)
    issues_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Patient {self.patient_id}"
    
    def update_status(self):
        """Calculate patient status based on open issues"""
        open_queries = self.queries.filter(is_resolved=False).count()
        missing_visits = self.visits.filter(is_missing=True).count()
        incomplete_forms = Form.objects.filter(visit__patient=self, is_complete=False).count()
        missing_labs = self.lab_data.filter(is_missing=True).count()
        
        total_issues = open_queries + missing_visits + incomplete_forms + missing_labs
        self.issues_count = total_issues
        
        if total_issues == 0:
            self.status = 'clean'
            self.is_clean = True
        elif total_issues <= 3:
            self.status = 'minor_issues'
            self.is_clean = False
        elif total_issues <= 10:
            self.status = 'major_issues'
            self.is_clean = False
        else:
            self.status = 'critical'
            self.is_clean = False
        
        self.save()
        return total_issues
    
    class Meta:
        unique_together = ['site', 'patient_id']
        ordering = ['patient_id']


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_number = models.CharField(max_length=20)
    visit_name = models.CharField(max_length=100)
    scheduled_date = models.DateField(null=True, blank=True)
    actual_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    is_missing = models.BooleanField(default=False)
    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient} - {self.visit_name}"
    
    def is_overdue(self):
        if self.window_end and not self.is_completed:
            return timezone.now().date() > self.window_end
        return False
    
    class Meta:
        unique_together = ['patient', 'visit_number']
        ordering = ['visit_number']


class Form(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='forms')
    form_id = models.CharField(max_length=50)
    form_name = models.CharField(max_length=200)
    is_required = models.BooleanField(default=True)
    is_complete = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    verified_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.form_name}"
    
    class Meta:
        ordering = ['form_id']


class Query(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='queries')
    query_id = models.CharField(max_length=50)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, null=True, blank=True, related_name='queries')
    query_text = models.TextField()
    query_type = models.CharField(max_length=50, choices=[
        ('missing_data', 'Missing Data'),
        ('inconsistency', 'Data Inconsistency'),
        ('clarification', 'Clarification Needed'),
        ('protocol_deviation', 'Protocol Deviation')
    ])
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], default='medium')
    opened_date = models.DateField()
    resolved_date = models.DateField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    days_open = models.IntegerField(default=0)
    response_text = models.TextField(blank=True)

    class Meta:
        unique_together = ['patient', 'query_id']
        
    def __str__(self):
        return f"Query {self.query_id}"
    
    def calculate_days_open(self):
        if self.is_resolved and self.resolved_date:
            delta = self.resolved_date - self.opened_date
        else:
            delta = timezone.now().date() - self.opened_date
        self.days_open = delta.days
        self.save()
    
    class Meta:
        verbose_name_plural = "Queries"
        ordering = ['-opened_date']


class LabData(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_data')
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, null=True, blank=True, related_name='lab_data')
    lab_name = models.CharField(max_length=200)
    test_name = models.CharField(max_length=200)
    test_code = models.CharField(max_length=50, blank=True)
    result_value = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    is_missing = models.BooleanField(default=False)
    collection_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient} - {self.test_name}"
    
    class Meta:
        ordering = ['-collection_date']


class CodingIssue(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='coding_issues')
    issue_type = models.CharField(max_length=50, choices=[
        ('meddra', 'MedDRA Coding'),
        ('whodd', 'WHO-DD Coding'),
        ('other', 'Other Coding')
    ])
    term = models.CharField(max_length=200)
    suggested_code = models.CharField(max_length=50, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.issue_type} - {self.term}"


class ExcelUpload(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='uploads')
    file = models.FileField(upload_to='excel_uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, choices=[
        ('missing_labs', 'Missing Lab Data'),
        ('missing_visits', 'Missing Visits/Pages'),
        ('coding_issues', 'Coding Issues'),
        ('inactivated_forms', 'Inactivated Forms'),
        ('visit_projections', 'Visit Projections'),
        ('open_queries', 'Open Queries')
    ])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    rows_processed = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.file_type} - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-uploaded_at']


class AIInsight(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_insights')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_insights')
    study = models.ForeignKey(Study, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_insights')
    insight_type = models.CharField(max_length=50, choices=[
        ('summary', 'Executive Summary'),
        ('root_cause', 'Root Cause Analysis'),
        ('prediction', 'Predictive Analysis'),
        ('recommendation', 'Recommendation'),
        ('comparative', 'Comparative Analysis')
    ])
    title = models.CharField(max_length=200)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cache_key = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return f"{self.insight_type} - {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-created_at']


class Alert(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='alerts')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    alert_type = models.CharField(max_length=50, choices=[
        ('dqi_drop', 'DQI Score Drop'),
        ('query_age', 'Old Queries'),
        ('missing_visits', 'Missing Visits Pattern'),
        ('site_capacity', 'Site Capacity Issue'),
        ('database_lock', 'Database Lock Risk')
    ])
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    message = models.TextField()
    action_taken = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=200, blank=True)
    action_taken = models.TextField(blank=True)
    notified_users = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.severity.upper()} - {self.alert_type}"
    
    class Meta:
        ordering = ['-created_at']


class DQIHistory(models.Model):
    """Track DQI score changes over time"""
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='dqi_history')
    dqi_score = models.FloatField()
    missing_data_score = models.FloatField(default=0)
    query_score = models.FloatField(default=0)
    visit_completion_score = models.FloatField(default=0)
    verification_score = models.FloatField(default=0)
    coding_score = models.FloatField(default=0)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.site} - {self.dqi_score} ({self.calculated_at.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-calculated_at']
        verbose_name_plural = "DQI Histories"