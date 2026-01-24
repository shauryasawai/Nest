from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import Study, Site, Patient, Query, Alert, ExcelUpload, AIInsight, DQIHistory
from .forms import ExcelUploadForm, AIQueryForm
from .utils.excel_parser import ExcelParser
from .utils.dqi_calculator import DQICalculator
from .utils.ai_integration import AIIntegration
from .tasks import process_excel_file, calculate_all_dqi_scores
import json

def dashboard(request):
    """Main dashboard view"""
    studies = Study.objects.all().prefetch_related('sites')
    
    # Get selected study from query params
    selected_study_id = request.GET.get('study')
    if selected_study_id:
        studies = studies.filter(id=selected_study_id)
    
    # Calculate overall metrics
    total_sites = Site.objects.filter(study__in=studies).count()
    total_patients = Patient.objects.filter(site__study__in=studies).count()
    clean_patients = Patient.objects.filter(site__study__in=studies, is_clean=True).count()
    
    # DQI distribution
    critical_sites = Site.objects.filter(study__in=studies, dqi_score__lt=45).count()
    poor_sites = Site.objects.filter(study__in=studies, dqi_score__gte=45, dqi_score__lt=60).count()
    fair_sites = Site.objects.filter(study__in=studies, dqi_score__gte=60, dqi_score__lt=75).count()
    good_sites = Site.objects.filter(study__in=studies, dqi_score__gte=75).count()
    
    # Recent alerts
    recent_alerts = Alert.objects.filter(
        site__study__in=studies,
        is_resolved=False
    ).order_by('-created_at')[:10]
    
    # Sites needing attention (DQI < 60)
    attention_sites = Site.objects.filter(
        study__in=studies,
        dqi_score__lt=60
    ).order_by('dqi_score')[:10]
    
    # Top performing sites
    top_sites = Site.objects.filter(
        study__in=studies,
        dqi_score__gte=63
    ).order_by('-dqi_score')[:5]
    
    context = {
        'studies': Study.objects.all(),
        'selected_study': selected_study_id,
        'total_sites': total_sites,
        'total_patients': total_patients,
        'clean_patients': clean_patients,
        'clean_percentage': round((clean_patients / total_patients * 100) if total_patients > 0 else 0, 1),
        'critical_sites': critical_sites,
        'poor_sites': poor_sites,
        'fair_sites': fair_sites,
        'good_sites': good_sites,
        'recent_alerts': recent_alerts,
        'attention_sites': attention_sites,
        'top_sites': top_sites,
    }
    
    return render(request, 'base/dashboard.html', context)


def study_list(request):
    """List all studies"""
    studies = Study.objects.all().annotate(
        site_count=Count('sites', distinct=True),
        patient_count=Count('sites__patients', distinct=True)
    )
    
    # Calculate aggregated totals
    total_sites = Site.objects.count()
    total_patients = Patient.objects.count()
    unique_phases = studies.values('phase').distinct().count()
    
    context = {
        'studies': studies,
        'total_sites': total_sites,
        'total_patients': total_patients,
        'unique_phases': unique_phases,
    }
    
    return render(request, 'base/study_list.html', context)


def site_list(request):
    """List all sites with filtering"""
    sites = Site.objects.all().select_related('study')
    
    # Filtering
    study_id = request.GET.get('study')
    if study_id:
        sites = sites.filter(study_id=study_id)
    
    status = request.GET.get('status')
    if status:
        sites = sites.filter(status=status)
    
    dqi_filter = request.GET.get('dqi')
    if dqi_filter == 'critical':
        sites = sites.filter(dqi_score__lt=45)
    elif dqi_filter == 'poor':
        sites = sites.filter(dqi_score__gte=45, dqi_score__lt=60)
    elif dqi_filter == 'fair':
        sites = sites.filter(dqi_score__gte=60, dqi_score__lt=75)
    elif dqi_filter == 'good':
        sites = sites.filter(dqi_score__gte=75)
    
    # Sorting
    sort_by = request.GET.get('sort', 'site_number')
    sites = sites.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(sites, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'studies': Study.objects.all(),
        'selected_study': study_id,
        'selected_status': status,
        'selected_dqi': dqi_filter
    }
    
    return render(request, 'base/site_list.html', context)


def site_detail(request, site_id):
    """Detailed view of a single site"""
    site = get_object_or_404(Site, id=site_id)
    
    # Get metrics
    metrics = site.get_metrics()
    
    # Get patients
    patients = site.patients.all().order_by('patient_id')
    
    # Get recent alerts
    alerts = site.alerts.filter(is_resolved=False).order_by('-created_at')[:5]
    
    # Get DQI history (last 30 days)
    dqi_history = site.dqi_history.all().order_by('-calculated_at')[:30]
    
    # Get AI insights
    ai_insights = site.ai_insights.all().order_by('-created_at')[:3]
    
    # AI Query Form
    if request.method == 'POST' and 'ai_query' in request.POST:
        ai_form = AIQueryForm(request.POST)
        if ai_form.is_valid():
            question = ai_form.cleaned_data['query']
            ai = AIIntegration()
            answer = ai.answer_custom_query(question, 'site', site.id)
            messages.success(request, "AI insight generated!")
            return JsonResponse({'answer': answer})
    else:
        ai_form = AIQueryForm(initial={'context_type': 'site', 'context_id': site.id})
    
    context = {
        'site': site,
        'metrics': metrics,
        'patients': patients,
        'alerts': alerts,
        'dqi_history': list(dqi_history.values('dqi_score', 'calculated_at')),
        'ai_insights': ai_insights,
        'ai_form': ai_form
    }
    
    return render(request, 'base/site_detail.html', context)


def patient_detail(request, patient_id):
    """Detailed view of a single patient"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get all related data
    visits = patient.visits.all().order_by('visit_number')
    queries = patient.queries.all().order_by('-opened_date')
    lab_data = patient.lab_data.all().order_by('-collection_date')
    coding_issues = patient.coding_issues.filter(is_resolved=False)
    
    # Update patient status
    patient.update_status()
    
    context = {
        'patient': patient,
        'visits': visits,
        'queries': queries,
        'lab_data': lab_data,
        'coding_issues': coding_issues
    }
    
    return render(request, 'base/patient_detail.html', context)


def upload_excel(request):
    """Upload and process Excel files"""
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.original_filename = request.FILES['file'].name
            upload.save()
            
            # Trigger async processing
            try:
                process_excel_file.delay(upload.id)
            except Exception:
                process_excel_file(upload.id)
            
            messages.success(request, 'File uploaded successfully! Processing in background.')
            return redirect('base:upload')
    else:
        form = ExcelUploadForm()
    
    # Get recent uploads
    recent_uploads = ExcelUpload.objects.all().order_by('-uploaded_at')[:20]
    
    context = {
        'form': form,
        'recent_uploads': recent_uploads
    }
    
    return render(request, 'base/upload.html', context)


@require_http_methods(["POST"])
def calculate_dqi(request, site_id):
    """Manually trigger DQI calculation for a site"""
    site = get_object_or_404(Site, id=site_id)
    
    calculator = DQICalculator(site)
    dqi = calculator.calculate()
    
    return JsonResponse({
        'success': True,
        'dqi_score': dqi,
        'dqi_status': site.get_dqi_status()
    })


@require_http_methods(["POST"])
def generate_ai_insight(request, site_id):
    """Generate AI insight for a site"""
    site = get_object_or_404(Site, id=site_id)
    insight_type = request.POST.get('insight_type', 'summary')
    
    ai = AIIntegration()
    
    if insight_type == 'summary':
        content = ai.generate_site_summary(site)
    elif insight_type == 'root_cause':
        content = ai.generate_root_cause_analysis(site)
    else:
        content = "Unknown insight type"
    
    return JsonResponse({
        'success': True,
        'content': content,
        'insight_type': insight_type
    })


def alerts_view(request):
    """View all alerts"""
    alerts = Alert.objects.all().select_related('site', 'patient')
    
    # Get all filter parameters
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    alert_type = request.GET.get('alert_type')
    
    # Apply filters
    if severity:
        alerts = alerts.filter(severity=severity)
    
    if status == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    elif status == 'all':
        # Show all, no filter
        pass
    else:
        # Default: active only
        alerts = alerts.filter(is_resolved=False)
    
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    alerts = alerts.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'selected_severity': severity
    }
    
    return render(request, 'base/alerts.html', context)