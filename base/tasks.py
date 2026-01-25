from django.utils import timezone
from .models import ExcelUpload, Site, Patient, Alert
from .utils.excel_parser import ExcelParser
from .utils.dqi_calculator import DQICalculator


def process_excel_file(upload_id):
    """Process uploaded Excel file synchronously"""
    try:
        upload = ExcelUpload.objects.get(id=upload_id)
        
        # Parse the file
        parser = ExcelParser(upload)
        success, rows_processed = parser.parse()
        
        # Update upload record
        upload.processed = success
        upload.processed_at = timezone.now()
        upload.rows_processed = rows_processed
        upload.errors = parser.get_errors()
        upload.save()
        
        if success:
            # Recalculate DQI for affected sites
            sites = Site.objects.filter(study=upload.study)
            for site in sites:
                calculate_site_dqi(site.id)
            
            # Update patient statuses
            patients = Patient.objects.filter(site__study=upload.study)
            for patient in patients:
                patient.update_status()
        
        return f"Processed {rows_processed} rows"
        
    except Exception as e:
        return f"Error: {str(e)}"


def calculate_site_dqi(site_id):
    """Calculate DQI for a specific site"""
    try:
        site = Site.objects.get(id=site_id)
        calculator = DQICalculator(site)
        dqi = calculator.calculate()
        
        # Check for alerts
        check_dqi_alerts(site_id)
        
        return f"Site {site.site_number}: DQI = {dqi}"
        
    except Exception as e:
        return f"Error: {str(e)}"


def calculate_all_dqi_scores():
    """Calculate DQI for all active sites (scheduled task)"""
    sites = Site.objects.filter(status='active')
    
    for site in sites:
        calculate_site_dqi(site.id)
    
    return f"Calculated DQI for {sites.count()} sites"


def check_dqi_alerts(site_id):
    """Check and create alerts based on DQI thresholds"""
    try:
        site = Site.objects.get(id=site_id)
        
        # Check for DQI drop below critical threshold
        if site.dqi_score < 60:
            # Check if alert already exists
            existing = Alert.objects.filter(
                site=site,
                alert_type='dqi_drop',
                is_resolved=False
            ).exists()
            
            if not existing:
                severity = 'critical' if site.dqi_score < 45 else 'high'
                Alert.objects.create(
                    site=site,
                    alert_type='dqi_drop',
                    severity=severity,
                    message=f"Site {site.site_number} DQI score dropped to {site.dqi_score}/100. Immediate attention required."
                )
        
        # Check for old queries
        from .models import Query
        old_queries = Query.objects.filter(
            patient__site=site,
            is_resolved=False,
            days_open__gte=21
        ).count()
        
        if old_queries > 10:
            existing = Alert.objects.filter(
                site=site,
                alert_type='query_age',
                is_resolved=False
            ).exists()
            
            if not existing:
                Alert.objects.create(
                    site=site,
                    alert_type='query_age',
                    severity='high',
                    message=f"Site {site.site_number} has {old_queries} queries open for more than 21 days."
                )
        
        return f"Alerts checked for Site {site.site_number}"
        
    except Exception as e:
        return f"Error: {str(e)}"


def update_query_ages():
    """Update days_open for all unresolved queries (daily task)"""
    from .models import Query
    
    queries = Query.objects.filter(is_resolved=False)
    
    for query in queries:
        query.calculate_days_open()
    
    return f"Updated {queries.count()} queries"


def check_missing_visit_patterns():
    """Detect patterns of missing visits at sites"""
    from django.db.models import Count
    from .models import Visit
    
    # Find sites with many missing visits
    sites_with_issues = Visit.objects.filter(
        is_missing=True
    ).values('patient__site').annotate(
        missing_count=Count('id')
    ).filter(missing_count__gte=5)
    
    for item in sites_with_issues:
        site_id = item['patient__site']
        site = Site.objects.get(id=site_id)
        
        existing = Alert.objects.filter(
            site=site,
            alert_type='missing_visits',
            is_resolved=False
        ).exists()
        
        if not existing:
            Alert.objects.create(
                site=site,
                alert_type='missing_visits',
                severity='medium',
                message=f"Site {site.site_number} has a pattern of {item['missing_count']} missing visits. Review scheduling process."
            )
    
    return f"Checked {sites_with_issues.count()} sites for missing visit patterns"