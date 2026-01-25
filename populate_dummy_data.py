import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from base.models import (
    Study, Site, Patient, Visit, Form, Query, 
    LabData, CodingIssue, Alert, DQIHistory
)
from base.utils.dqi_calculator import DQICalculator

# Sample data
COUNTRIES = ['USA', 'UK', 'Germany', 'France', 'Canada', 'Australia', 'Japan', 'India']
SITE_NAMES = [
    'Memorial Hospital', 'City Medical Center', 'University Clinic',
    'General Hospital', 'Health Institute', 'Research Center',
    'Clinical Trials Unit', 'Medical Research Institute'
]
INVESTIGATOR_NAMES = [
    'Dr. Sarah Johnson', 'Dr. Michael Chen', 'Dr. Emily Brown',
    'Dr. Robert Wilson', 'Dr. Lisa Anderson', 'Dr. David Martinez',
    'Dr. Jennifer Lee', 'Dr. Christopher Taylor', 'Dr. Amanda Garcia'
]
QUERY_TYPES = ['missing_data', 'inconsistency', 'clarification', 'protocol_deviation']
LAB_NAMES = ['Central Lab', 'Quest Diagnostics', 'LabCorp', 'Mayo Clinic Labs']
TEST_NAMES = [
    'Complete Blood Count', 'Liver Function Test', 'Kidney Function Test',
    'Lipid Panel', 'Thyroid Function', 'Glucose Test', 'Hemoglobin A1c',
    'Urinalysis', 'Coagulation Panel', 'Electrolyte Panel'
]

def clear_existing_data():
    """Clear all existing data"""
    print("Clearing existing data...")
    with transaction.atomic():
        Alert.objects.all().delete()
        DQIHistory.objects.all().delete()
        CodingIssue.objects.all().delete()
        LabData.objects.all().delete()
        Query.objects.all().delete()
        Form.objects.all().delete()
        Visit.objects.all().delete()
        Patient.objects.all().delete()
        Site.objects.all().delete()
        Study.objects.all().delete()
    print("✓ Data cleared")

def create_studies():
    """Create test studies"""
    print("\nCreating studies...")
    
    studies_data = [
        {
            'study_id': 'ONCO-2024-001',
            'study_name': 'Phase III Oncology Trial - Advanced Melanoma',
            'protocol_number': 'ONK-MEL-301',
            'phase': 'III',
            'therapeutic_area': 'Oncology'
        },
        {
            'study_id': 'CARDIO-2024-002',
            'study_name': 'Phase II Cardiovascular Study - Heart Failure',
            'protocol_number': 'CVD-HF-201',
            'phase': 'II',
            'therapeutic_area': 'Cardiology'
        },
        {
            'study_id': 'NEURO-2024-003',
            'study_name': 'Phase III Neurology Trial - Alzheimer\'s Disease',
            'protocol_number': 'NEU-ALZ-302',
            'phase': 'III',
            'therapeutic_area': 'Neurology'
        }
    ]
    
    studies = []
    for data in studies_data:
        study = Study(**data)
        studies.append(study)
    
    # Bulk create studies
    Study.objects.bulk_create(studies)
    
    # Fetch created studies to get IDs
    studies = list(Study.objects.all().order_by('id'))
    
    for study in studies:
        print(f"  ✓ Created study: {study.study_id}")
    
    return studies

def create_sites(studies):
    """Create test sites using bulk operations"""
    print("\nCreating sites...")
    sites_to_create = []
    
    site_counter = 101
    for study in studies:
        # Create 8-12 sites per study
        num_sites = random.randint(8, 12)
        
        for i in range(num_sites):
            site = Site(
                study=study,
                site_number=f"{site_counter}",
                site_name=random.choice(SITE_NAMES),
                country=random.choice(COUNTRIES),
                investigator_name=random.choice(INVESTIGATOR_NAMES),
                coordinator_name=f"Coordinator {random.randint(1, 50)}",
                coordinator_email=f"coord{random.randint(1, 100)}@example.com",
                status='active'
            )
            sites_to_create.append(site)
            site_counter += 1
    
    # Bulk create sites
    Site.objects.bulk_create(sites_to_create, batch_size=100)
    
    # Fetch created sites
    sites = list(Site.objects.all().select_related('study'))
    
    for site in sites:
        print(f"  ✓ Created site: {site.site_number} - {site.site_name}")
    
    return sites

def create_patients(sites):
    """Create test patients using bulk operations"""
    print("\nCreating patients...")
    patients_to_create = []
    
    for site in sites:
        # Create 5-15 patients per site
        num_patients = random.randint(5, 15)
        
        for i in range(num_patients):
            enrollment_date = datetime.now().date() - timedelta(days=random.randint(30, 365))
            
            patient = Patient(
                site=site,
                patient_id=f"{site.site_number}-{str(i+1).zfill(3)}",
                screening_number=f"SCR-{random.randint(1000, 9999)}",
                enrollment_date=enrollment_date
            )
            patients_to_create.append(patient)
    
    # Bulk create patients
    Patient.objects.bulk_create(patients_to_create, batch_size=500)
    
    # Fetch created patients
    patients = list(Patient.objects.all().select_related('site'))
    
    print(f"  ✓ Created {len(patients)} patients")
    return patients

def create_visits(patients):
    """Create test visits using bulk operations"""
    print("\nCreating visits...")
    visit_schedule = [
        ('V1', 'Screening'),
        ('V2', 'Baseline'),
        ('V3', 'Week 4'),
        ('V4', 'Week 8'),
        ('V5', 'Week 12'),
        ('V6', 'Week 16'),
        ('V7', 'Week 24'),
        ('V8', 'End of Treatment')
    ]
    
    visits_to_create = []
    
    for patient in patients:
        for i, (visit_num, visit_name) in enumerate(visit_schedule):
            scheduled_date = patient.enrollment_date + timedelta(weeks=i*4)
            
            is_completed = random.random() < 0.70
            actual_date = scheduled_date + timedelta(days=random.randint(-3, 7)) if is_completed else None
            is_missing = not is_completed and scheduled_date < datetime.now().date()
            
            visit = Visit(
                patient=patient,
                visit_number=visit_num,
                visit_name=visit_name,
                scheduled_date=scheduled_date,
                actual_date=actual_date,
                is_completed=is_completed,
                is_missing=is_missing,
                window_start=scheduled_date - timedelta(days=3),
                window_end=scheduled_date + timedelta(days=7)
            )
            visits_to_create.append(visit)
    
    # Bulk create visits
    print(f"  Creating {len(visits_to_create)} visits...")
    Visit.objects.bulk_create(visits_to_create, batch_size=1000)
    print(f"  ✓ Created {len(visits_to_create)} visits")
    
    # Now create forms
    print("  Creating forms...")
    create_forms(patients)

def create_forms(patients):
    """Create forms for all visits using bulk operations"""
    form_types = [
        'Demographics', 'Medical History', 'Vital Signs',
        'Laboratory Results', 'Adverse Events', 'Concomitant Medications'
    ]
    
    # Fetch all visits
    all_visits = Visit.objects.filter(patient__in=patients).select_related('patient')
    
    forms_to_create = []
    
    for visit in all_visits:
        for form_name in form_types:
            is_complete = visit.is_completed and random.random() < 0.80
            is_verified = is_complete and random.random() < 0.70
            
            form = Form(
                visit=visit,
                form_id=f"{visit.visit_number}-{form_name.replace(' ', '')[:3].upper()}",
                form_name=form_name,
                is_required=True,
                is_complete=is_complete,
                is_verified=is_verified,
                completed_date=visit.actual_date if is_complete else None,
                verified_date=visit.actual_date + timedelta(days=random.randint(1, 10)) if is_verified else None
            )
            forms_to_create.append(form)
    
    # Bulk create forms
    print(f"  Creating {len(forms_to_create)} forms...")
    Form.objects.bulk_create(forms_to_create, batch_size=2000)
    print(f"  ✓ Created {len(forms_to_create)} forms")

def create_queries(patients):
    """Create test queries using bulk operations"""
    print("\nCreating queries...")
    queries_to_create = []
    
    for patient in patients:
        # Create 0-8 queries per patient
        num_queries = random.randint(0, 8)
        
        for i in range(num_queries):
            opened_date = patient.enrollment_date + timedelta(days=random.randint(10, 200))
            
            # 60% chance query is resolved
            is_resolved = random.random() < 0.60
            resolved_date = opened_date + timedelta(days=random.randint(1, 30)) if is_resolved else None
            
            days_open = (resolved_date - opened_date).days if is_resolved else (datetime.now().date() - opened_date).days
            
            query = Query(
                patient=patient,
                query_id=f"Q-{patient.site.site_number}-{random.randint(1000, 9999)}",
                query_text=f"Query regarding {random.choice(['missing data', 'data inconsistency', 'clarification needed', 'protocol deviation'])}",
                query_type=random.choice(QUERY_TYPES),
                severity=random.choice(['low', 'medium', 'high', 'critical']),
                opened_date=opened_date,
                resolved_date=resolved_date,
                is_resolved=is_resolved,
                days_open=days_open
            )
            queries_to_create.append(query)
    
    # Bulk create queries
    Query.objects.bulk_create(queries_to_create, batch_size=1000)
    print(f"  ✓ Created {len(queries_to_create)} queries")

def create_lab_data(patients):
    """Create lab data entries using bulk operations"""
    print("\nCreating lab data...")
    labs_to_create = []
    
    for patient in patients:
        # Create 3-8 lab entries per patient
        num_labs = random.randint(3, 8)
        
        for i in range(num_labs):
            is_missing = random.random() < 0.15  # 15% chance lab is missing
            
            lab = LabData(
                patient=patient,
                lab_name=random.choice(LAB_NAMES),
                test_name=random.choice(TEST_NAMES),
                test_code=f"LAB-{random.randint(100, 999)}",
                result_value=str(random.randint(50, 200)) if not is_missing else "",
                unit='mg/dL',
                reference_range='70-100' if not is_missing else "",
                is_missing=is_missing,
                collection_date=patient.enrollment_date + timedelta(days=random.randint(0, 100))
            )
            labs_to_create.append(lab)
    
    # Bulk create lab data
    LabData.objects.bulk_create(labs_to_create, batch_size=1000)
    print(f"  ✓ Created {len(labs_to_create)} lab entries")

def create_coding_issues(patients):
    """Create coding issues using bulk operations"""
    print("\nCreating coding issues...")
    
    # 30% of patients have coding issues
    patients_with_issues = random.sample(list(patients), k=int(len(patients) * 0.3))
    
    issues_to_create = []
    
    for patient in patients_with_issues:
        num_issues = random.randint(1, 3)
        
        for i in range(num_issues):
            is_resolved = random.random() < 0.50
            
            issue = CodingIssue(
                patient=patient,
                issue_type=random.choice(['meddra', 'whodd', 'other']),
                term=f"Medical term {random.randint(1, 100)}",
                suggested_code=f"CODE-{random.randint(10000, 99999)}",
                is_resolved=is_resolved,
                resolved_at=timezone.now() - timedelta(days=random.randint(1, 30)) if is_resolved else None
            )
            issues_to_create.append(issue)
    
    # Bulk create coding issues
    CodingIssue.objects.bulk_create(issues_to_create, batch_size=500)
    print(f"  ✓ Created {len(issues_to_create)} coding issues")

def calculate_dqi_scores(sites):
    """Calculate DQI scores for all sites"""
    print("\nCalculating DQI scores...")
    
    for i, site in enumerate(sites, 1):
        try:
            calculator = DQICalculator(site)
            dqi = calculator.calculate()
            print(f"  ✓ Site {site.site_number}: DQI = {dqi:.2f} ({i}/{len(sites)})")
        except Exception as e:
            print(f"  ✗ Error calculating DQI for site {site.site_number}: {str(e)}")

def update_patient_statuses(patients):
    """Update patient statuses based on issues"""
    print("\nUpdating patient statuses...")
    
    for i, patient in enumerate(patients, 1):
        try:
            patient.update_status()
            if i % 100 == 0:
                print(f"  ✓ Updated {i}/{len(patients)} patients...")
        except Exception as e:
            print(f"  ✗ Error updating patient {patient.patient_id}: {str(e)}")
    
    print(f"  ✓ All {len(patients)} patient statuses updated")

def create_alerts(sites):
    """Create alerts for sites with issues"""
    print("\nCreating alerts...")
    alerts_to_create = []
    
    for site in sites:
        # Create alert if DQI is low
        if site.dqi_score < 60:
            alert = Alert(
                site=site,
                alert_type='dqi_drop',
                severity='critical' if site.dqi_score < 45 else 'high',
                message=f"Site {site.site_number} DQI score dropped to {site.dqi_score}/100. Immediate attention required."
            )
            alerts_to_create.append(alert)
        
        # Create alert for old queries
        old_queries = Query.objects.filter(
            patient__site=site,
            is_resolved=False,
            days_open__gte=21
        ).count()
        
        if old_queries > 5:
            alert = Alert(
                site=site,
                alert_type='query_age',
                severity='high',
                message=f"Site {site.site_number} has {old_queries} queries open for more than 21 days."
            )
            alerts_to_create.append(alert)
    
    # Bulk create alerts
    Alert.objects.bulk_create(alerts_to_create, batch_size=100)
    print(f"  ✓ Created {len(alerts_to_create)} alerts")

def main():
    """Main function to generate all test data"""
    print("="*60)
    print("NEST 2.0 - Test Data Generator (Optimized)")
    print("="*60)
    
    # Clear existing data
    response = input("\nThis will DELETE all existing data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    try:
        clear_existing_data()
        
        # Create data
        print("\n" + "="*60)
        print("Phase 1: Creating Core Data")
        print("="*60)
        studies = create_studies()
        sites = create_sites(studies)
        patients = create_patients(sites)
        
        print("\n" + "="*60)
        print("Phase 2: Creating Visit and Form Data")
        print("="*60)
        create_visits(patients)
        
        print("\n" + "="*60)
        print("Phase 3: Creating Additional Data")
        print("="*60)
        create_queries(patients)
        create_lab_data(patients)
        create_coding_issues(patients)
        
        # Update calculated fields
        print("\n" + "="*60)
        print("Phase 4: Calculating Metrics")
        print("="*60)
        update_patient_statuses(patients)
        calculate_dqi_scores(sites)
        create_alerts(sites)
        
        # Print summary
        print("\n" + "="*60)
        print("DATA GENERATION COMPLETE!")
        print("="*60)
        print(f"Studies created:      {Study.objects.count()}")
        print(f"Sites created:        {Site.objects.count()}")
        print(f"Patients created:     {Patient.objects.count()}")
        print(f"Visits created:       {Visit.objects.count()}")
        print(f"Forms created:        {Form.objects.count()}")
        print(f"Queries created:      {Query.objects.count()}")
        print(f"Lab entries created:  {LabData.objects.count()}")
        print(f"Coding issues:        {CodingIssue.objects.count()}")
        print(f"Alerts created:       {Alert.objects.count()}")
        print("="*60)
        print("\n✓ You can now access the application at http://localhost:8000")
        print("✓ Admin interface at http://localhost:8000/admin")
        print("\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check database connection in settings.py")
        print("3. Run: python manage.py migrate")
        print("4. Restart PostgreSQL service if needed")
        raise

if __name__ == '__main__':
    main()