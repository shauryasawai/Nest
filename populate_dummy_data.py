
import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

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
    studies = []
    
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
    
    for data in studies_data:
        study = Study.objects.create(**data)
        studies.append(study)
        print(f"  ✓ Created study: {study.study_id}")
    
    return studies

def create_sites(studies):
    """Create test sites"""
    print("\nCreating sites...")
    sites = []
    
    for study in studies:
        # Create 8-12 sites per study
        num_sites = random.randint(8, 12)
        
        for i in range(num_sites):
            site = Site.objects.create(
                study=study,
                site_number=f"{100 + len(sites) + 1}",
                site_name=random.choice(SITE_NAMES),
                country=random.choice(COUNTRIES),
                investigator_name=random.choice(INVESTIGATOR_NAMES),
                coordinator_name=f"Coordinator {random.randint(1, 50)}",
                coordinator_email=f"coord{random.randint(1, 100)}@example.com",
                status='active'
            )
            sites.append(site)
            print(f"  ✓ Created site: {site.site_number} - {site.site_name}")
    
    return sites

def create_patients(sites):
    """Create test patients"""
    print("\nCreating patients...")
    patients = []
    
    for site in sites:
        # Create 5-15 patients per site
        num_patients = random.randint(5, 15)
        
        for i in range(num_patients):
            enrollment_date = datetime.now().date() - timedelta(days=random.randint(30, 365))
            
            patient = Patient.objects.create(
                site=site,
                patient_id=f"{site.site_number}-{str(i+1).zfill(3)}",
                screening_number=f"SCR-{random.randint(1000, 9999)}",
                enrollment_date=enrollment_date
            )
            patients.append(patient)
    
    print(f"  ✓ Created {len(patients)} patients")
    return patients

def create_visits(patients):
    """Create test visits"""
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
    
    for patient in patients:
        for i, (visit_num, visit_name) in enumerate(visit_schedule):
            scheduled_date = patient.enrollment_date + timedelta(weeks=i*4)
            
            # 70% chance visit is completed
            is_completed = random.random() < 0.70
            actual_date = scheduled_date + timedelta(days=random.randint(-3, 7)) if is_completed else None
            is_missing = not is_completed and scheduled_date < datetime.now().date()
            
            visit = Visit.objects.create(
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
            
            # Create forms for this visit
            create_forms_for_visit(visit)
    
    print("  ✓ Created visits and forms")

def create_forms_for_visit(visit):
    """Create forms for a visit"""
    form_types = [
        'Demographics', 'Medical History', 'Vital Signs',
        'Laboratory Results', 'Adverse Events', 'Concomitant Medications'
    ]
    
    for form_name in form_types:
        # 80% chance form is complete if visit is complete
        is_complete = visit.is_completed and random.random() < 0.80
        is_verified = is_complete and random.random() < 0.70
        
        Form.objects.create(
            visit=visit,
            form_id=f"{visit.visit_number}-{form_name.replace(' ', '')[:3].upper()}",
            form_name=form_name,
            is_required=True,
            is_complete=is_complete,
            is_verified=is_verified,
            completed_date=visit.actual_date if is_complete else None,
            verified_date=visit.actual_date + timedelta(days=random.randint(1, 10)) if is_verified else None
        )

def create_queries(patients):
    """Create test queries"""
    print("\nCreating queries...")
    
    for patient in patients:
        # Create 0-8 queries per patient
        num_queries = random.randint(0, 8)
        
        for i in range(num_queries):
            opened_date = patient.enrollment_date + timedelta(days=random.randint(10, 200))
            
            # 60% chance query is resolved
            is_resolved = random.random() < 0.60
            resolved_date = opened_date + timedelta(days=random.randint(1, 30)) if is_resolved else None
            
            days_open = (resolved_date - opened_date).days if is_resolved else (datetime.now().date() - opened_date).days
            
            Query.objects.create(
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
    
    print("  ✓ Created queries")

def create_lab_data(patients):
    """Create lab data entries"""
    print("\nCreating lab data...")
    
    for patient in patients:
        # Create 3-8 lab entries per patient
        num_labs = random.randint(3, 8)
        
        for i in range(num_labs):
            is_missing = random.random() < 0.15  # 15% chance lab is missing
            
            LabData.objects.create(
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
    
    print("  ✓ Created lab data")

def create_coding_issues(patients):
    """Create coding issues"""
    print("\nCreating coding issues...")
    
    # 30% of patients have coding issues
    patients_with_issues = random.sample(list(patients), k=int(len(patients) * 0.3))
    
    for patient in patients_with_issues:
        num_issues = random.randint(1, 3)
        
        for i in range(num_issues):
            is_resolved = random.random() < 0.50
            
            CodingIssue.objects.create(
                patient=patient,
                issue_type=random.choice(['meddra', 'whodd', 'other']),
                term=f"Medical term {random.randint(1, 100)}",
                suggested_code=f"CODE-{random.randint(10000, 99999)}",
                is_resolved=is_resolved,
                resolved_at=timezone.now() - timedelta(days=random.randint(1, 30)) if is_resolved else None
            )
    
    print("  ✓ Created coding issues")

def calculate_dqi_scores(sites):
    """Calculate DQI scores for all sites"""
    print("\nCalculating DQI scores...")
    
    for site in sites:
        calculator = DQICalculator(site)
        dqi = calculator.calculate()
        print(f"  ✓ Site {site.site_number}: DQI = {dqi:.2f}")

def update_patient_statuses(patients):
    """Update patient statuses based on issues"""
    print("\nUpdating patient statuses...")
    
    for patient in patients:
        patient.update_status()
    
    print("  ✓ Patient statuses updated")

def create_alerts(sites):
    """Create alerts for sites with issues"""
    print("\nCreating alerts...")
    
    for site in sites:
        # Create alert if DQI is low
        if site.dqi_score < 60:
            Alert.objects.create(
                site=site,
                alert_type='dqi_drop',
                severity='critical' if site.dqi_score < 45 else 'high',
                message=f"Site {site.site_number} DQI score dropped to {site.dqi_score}/100. Immediate attention required."
            )
        
        # Create alert for old queries
        old_queries = Query.objects.filter(
            patient__site=site,
            is_resolved=False,
            days_open__gte=21
        ).count()
        
        if old_queries > 5:
            Alert.objects.create(
                site=site,
                alert_type='query_age',
                severity='high',
                message=f"Site {site.site_number} has {old_queries} queries open for more than 21 days."
            )
    
    print("  ✓ Alerts created")

def main():
    """Main function to generate all test data"""
    print("="*60)
    print("NEST 2.0 - Test Data Generator")
    print("="*60)
    
    # Clear existing data
    response = input("\nThis will DELETE all existing data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    clear_existing_data()
    
    # Create data
    studies = create_studies()
    sites = create_sites(studies)
    patients = create_patients(sites)
    create_visits(patients)
    create_queries(patients)
    create_lab_data(patients)
    create_coding_issues(patients)
    
    # Update calculated fields
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

if __name__ == '__main__':
    main()


# ============================================
# generate_sample_excel_files.py
# Generate sample Excel files for upload testing
# ============================================

import pandas as pd
from datetime import datetime, timedelta
import random
import os

def create_sample_excel_files():
    """Create sample Excel files for testing uploads"""
    
    # Create directory for sample files
    os.makedirs('sample_excel_files', exist_ok=True)
    
    print("Generating sample Excel files...")
    
    # 1. Missing Lab Data
    print("  Creating missing_labs.xlsx...")
    missing_labs_data = []
    for i in range(20):
        missing_labs_data.append({
            'site_number': random.randint(101, 115),
            'site_name': random.choice(['Memorial Hospital', 'City Medical Center', 'University Clinic']),
            'country': random.choice(['USA', 'UK', 'Canada']),
            'patient_id': f"{random.randint(101, 115)}-{str(random.randint(1, 50)).zfill(3)}",
            'visit': f"V{random.randint(1, 8)}",
            'lab_name': random.choice(['Central Lab', 'Quest Diagnostics', 'LabCorp']),
            'test_name': random.choice(['CBC', 'LFT', 'KFT', 'Lipid Panel']),
            'test_code': f"LAB-{random.randint(100, 999)}",
            'reference_range': random.choice(['70-100', '50-150', '3-5', '']),
        })
    
    df = pd.DataFrame(missing_labs_data)
    df.to_excel('sample_excel_files/missing_labs.xlsx', index=False)
    
    # 2. Missing Visits
    print("  Creating missing_visits.xlsx...")
    missing_visits_data = []
    for i in range(25):
        missing_visits_data.append({
            'site_number': random.randint(101, 115),
            'patient_id': f"{random.randint(101, 115)}-{str(random.randint(1, 50)).zfill(3)}",
            'visit_number': f"V{random.randint(1, 8)}",
            'visit_name': random.choice(['Screening', 'Baseline', 'Week 4', 'Week 8', 'Week 12']),
            'scheduled_date': (datetime.now() - timedelta(days=random.randint(1, 90))).strftime('%Y-%m-%d'),
        })
    
    df = pd.DataFrame(missing_visits_data)
    df.to_excel('sample_excel_files/missing_visits.xlsx', index=False)
    
    # 3. Open Queries
    print("  Creating open_queries.xlsx...")
    open_queries_data = []
    for i in range(30):
        opened_date = datetime.now() - timedelta(days=random.randint(1, 60))
        open_queries_data.append({
            'site_number': random.randint(101, 115),
            'patient_id': f"{random.randint(101, 115)}-{str(random.randint(1, 50)).zfill(3)}",
            'query_id': f"Q-{random.randint(10000, 99999)}",
            'query_text': random.choice([
                'Missing lab result for CBC',
                'Data inconsistency in vital signs',
                'Clarification needed for adverse event',
                'Protocol deviation - visit outside window'
            ]),
            'query_type': random.choice(['missing_data', 'inconsistency', 'clarification', 'protocol_deviation']),
            'severity': random.choice(['low', 'medium', 'high', 'critical']),
            'opened_date': opened_date.strftime('%Y-%m-%d'),
        })
    
    df = pd.DataFrame(open_queries_data)
    df.to_excel('sample_excel_files/open_queries.xlsx', index=False)
    
    # 4. Coding Issues
    print("  Creating coding_issues.xlsx...")
    coding_issues_data = []
    for i in range(15):
        coding_issues_data.append({
            'site_number': random.randint(101, 115),
            'patient_id': f"{random.randint(101, 115)}-{str(random.randint(1, 50)).zfill(3)}",
            'term': random.choice(['Headache', 'Nausea', 'Fatigue', 'Dizziness', 'Rash']),
            'issue_type': random.choice(['meddra', 'whodd']),
            'suggested_code': f"CODE-{random.randint(10000, 99999)}",
        })
    
    df = pd.DataFrame(coding_issues_data)
    df.to_excel('sample_excel_files/coding_issues.xlsx', index=False)
    
    # 5. Visit Projections
    print("  Creating visit_projections.xlsx...")
    visit_projections_data = []
    for i in range(40):
        projected_date = datetime.now() + timedelta(days=random.randint(-30, 60))
        actual_date = projected_date + timedelta(days=random.randint(-5, 5)) if random.random() < 0.6 else None
        
        visit_projections_data.append({
            'site_number': random.randint(101, 115),
            'patient_id': f"{random.randint(101, 115)}-{str(random.randint(1, 50)).zfill(3)}",
            'visit_number': f"V{random.randint(1, 8)}",
            'visit_name': random.choice(['Screening', 'Baseline', 'Week 4', 'Week 8', 'Week 12']),
            'projected_date': projected_date.strftime('%Y-%m-%d'),
            'actual_date': actual_date.strftime('%Y-%m-%d') if actual_date else '',
        })
    
    df = pd.DataFrame(visit_projections_data)
    df.to_excel('sample_excel_files/visit_projections.xlsx', index=False)
    
    print("\n✓ Sample Excel files created in 'sample_excel_files/' directory")
    print("\nGenerated files:")
    print("  - missing_labs.xlsx")
    print("  - missing_visits.xlsx")
    print("  - open_queries.xlsx")
    print("  - coding_issues.xlsx")
    print("  - visit_projections.xlsx")
    print("\nYou can upload these files through the web interface at:")
    print("http://localhost:8000/upload/")

if __name__ == '__main__':
    create_sample_excel_files()