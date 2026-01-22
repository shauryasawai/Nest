from django.db.models import Count, Avg, Q
from django.utils import timezone
from ..models import DQIHistory

class DQICalculator:
    """Calculate Data Quality Index for sites"""
    
    # Weights for different components (must sum to 100)
    WEIGHTS = {
        'missing_data': 30,
        'open_queries': 25,
        'visit_completion': 20,
        'verification': 15,
        'coding': 10
    }
    
    def __init__(self, site):
        self.site = site
        self.patients = site.patients.all()
        self.total_patients = self.patients.count()
    
    def calculate(self):
        """Calculate overall DQI score"""
        if self.total_patients == 0:
            return 0.0
        
        scores = {
            'missing_data': self.calculate_missing_data_score(),
            'query': self.calculate_query_score(),
            'visit_completion': self.calculate_visit_completion_score(),
            'verification': self.calculate_verification_score(),
            'coding': self.calculate_coding_score()
        }
        
        # Calculate weighted DQI
        dqi = sum(
            scores[key] * (self.WEIGHTS.get(key, self.WEIGHTS.get(key.replace('query', 'open_queries'), 0)) / 100)
            for key in scores
        )
        
        # Update site DQI
        self.site.dqi_score = round(dqi, 2)
        self.site.last_calculated = timezone.now()
        self.site.save()
        
        # Save to history
        DQIHistory.objects.create(
            site=self.site,
            dqi_score=dqi,
            missing_data_score=scores['missing_data'],
            query_score=scores['query'],
            visit_completion_score=scores['visit_completion'],
            verification_score=scores['verification'],
            coding_score=scores['coding']
        )
        
        return dqi
    
    def calculate_missing_data_score(self):
        """Calculate score based on missing data (labs, forms, etc.)"""
        from ..models import LabData, Form
        
        total_labs = LabData.objects.filter(patient__site=self.site).count()
        missing_labs = LabData.objects.filter(patient__site=self.site, is_missing=True).count()
        
        total_forms = Form.objects.filter(visit__patient__site=self.site, is_required=True).count()
        incomplete_forms = Form.objects.filter(
            visit__patient__site=self.site, 
            is_required=True, 
            is_complete=False
        ).count()
        
        if total_labs + total_forms == 0:
            return 100.0
        
        missing_rate = (missing_labs + incomplete_forms) / (total_labs + total_forms)
        score = max(0, 100 - (missing_rate * 100))
        
        return round(score, 2)
    
    def calculate_query_score(self):
        """Calculate score based on open queries"""
        from ..models import Query
        
        total_queries = Query.objects.filter(patient__site=self.site).count()
        open_queries = Query.objects.filter(patient__site=self.site, is_resolved=False).count()
        
        if total_queries == 0:
            return 100.0
        
        # Calculate based on both volume and age
        open_rate = open_queries / total_queries
        
        # Average age of open queries
        avg_age = Query.objects.filter(
            patient__site=self.site, 
            is_resolved=False
        ).aggregate(Avg('days_open'))['days_open__avg'] or 0
        
        # Score decreases with both open rate and age
        volume_penalty = open_rate * 50  # Max 50 points penalty
        age_penalty = min(avg_age / 2, 50)  # Max 50 points penalty (capped at 100 days)
        
        score = max(0, 100 - volume_penalty - age_penalty)
        
        return round(score, 2)
    
    def calculate_visit_completion_score(self):
        """Calculate score based on visit completion"""
        from ..models import Visit
        
        total_visits = Visit.objects.filter(patient__site=self.site).count()
        completed_visits = Visit.objects.filter(patient__site=self.site, is_completed=True).count()
        
        if total_visits == 0:
            return 100.0
        
        completion_rate = completed_visits / total_visits
        score = completion_rate * 100
        
        return round(score, 2)
    
    def calculate_verification_score(self):
        """Calculate score based on data verification status"""
        from ..models import Form
        
        total_forms = Form.objects.filter(visit__patient__site=self.site).count()
        verified_forms = Form.objects.filter(visit__patient__site=self.site, is_verified=True).count()
        
        if total_forms == 0:
            return 100.0
        
        verification_rate = verified_forms / total_forms
        score = verification_rate * 100
        
        return round(score, 2)
    
    def calculate_coding_score(self):
        """Calculate score based on coding completeness"""
        from ..models import CodingIssue
        
        total_issues = CodingIssue.objects.filter(patient__site=self.site).count()
        unresolved_issues = CodingIssue.objects.filter(
            patient__site=self.site, 
            is_resolved=False
        ).count()
        
        if total_issues == 0:
            return 100.0
        
        resolution_rate = (total_issues - unresolved_issues) / total_issues
        score = resolution_rate * 100
        
        return round(score, 2)