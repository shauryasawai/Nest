import pandas as pd
from datetime import datetime
from django.utils import timezone
from ..models import Site, Patient, Visit, Form, Query, LabData, CodingIssue

class ExcelParser:
    """Parse different types of Excel files and populate database"""
    
    def __init__(self, excel_upload):
        self.upload = excel_upload
        self.study = excel_upload.study
        self.file_type = excel_upload.file_type
        self.errors = []
        self.rows_processed = 0
    
    def parse(self):
        """Main parsing method"""
        try:
            df = pd.read_excel(self.upload.file.path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Route to appropriate parser based on file type
            parser_methods = {
                'missing_labs': self.parse_missing_labs,
                'missing_visits': self.parse_missing_visits,
                'coding_issues': self.parse_coding_issues,
                'open_queries': self.parse_open_queries,
                'visit_projections': self.parse_visit_projections
            }
            
            parser_method = parser_methods.get(self.file_type)
            if parser_method:
                parser_method(df)
            else:
                self.errors.append(f"Unknown file type: {self.file_type}")
            
            return True, self.rows_processed
        
        except Exception as e:
            self.errors.append(f"Error parsing file: {str(e)}")
            return False, 0
    
    def get_or_create_site(self, site_number, site_name="", country=""):
        """Get or create site"""
        site, created = Site.objects.get_or_create(
            study=self.study,
            site_number=str(site_number).strip(),
            defaults={
                'site_name': site_name or f"Site {site_number}",
                'country': country or "Unknown",
                'investigator_name': "TBD"
            }
        )
        return site
    
    def get_or_create_patient(self, site, patient_id):
        """Get or create patient"""
        patient, created = Patient.objects.get_or_create(
            site=site,
            patient_id=str(patient_id).strip()
        )
        return patient
    
    def parse_missing_labs(self, df):
        """Parse missing lab data file"""
        required_cols = ['site_number', 'patient_id', 'visit', 'lab_name', 'test_name']
        
        if not all(col in df.columns for col in required_cols):
            self.errors.append(f"Missing required columns. Required: {required_cols}")
            return
        
        for idx, row in df.iterrows():
            try:
                site = self.get_or_create_site(
                    row['site_number'],
                    row.get('site_name', ''),
                    row.get('country', '')
                )
                
                patient = self.get_or_create_patient(site, row['patient_id'])
                
                # Get or create visit
                visit_num = str(row['visit']).strip()
                visit, _ = Visit.objects.get_or_create(
                    patient=patient,
                    visit_number=visit_num,
                    defaults={'visit_name': f"Visit {visit_num}"}
                )
                
                # Create lab data entry
                LabData.objects.update_or_create(
                    patient=patient,
                    visit=visit,
                    lab_name=str(row['lab_name']).strip(),
                    test_name=str(row['test_name']).strip(),
                    defaults={
                        'is_missing': True,
                        'reference_range': row.get('reference_range', ''),
                        'test_code': row.get('test_code', '')
                    }
                )
                
                self.rows_processed += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: {str(e)}")
    
    def parse_missing_visits(self, df):
        """Parse missing visits/pages file"""
        required_cols = ['site_number', 'patient_id', 'visit_number']
        
        if not all(col in df.columns for col in required_cols):
            self.errors.append(f"Missing required columns. Required: {required_cols}")
            return
        
        for idx, row in df.iterrows():
            try:
                site = self.get_or_create_site(row['site_number'])
                patient = self.get_or_create_patient(site, row['patient_id'])
                
                visit_num = str(row['visit_number']).strip()
                visit_name = row.get('visit_name', f"Visit {visit_num}")
                
                # Parse dates if available
                scheduled_date = None
                if 'scheduled_date' in row and pd.notna(row['scheduled_date']):
                    scheduled_date = pd.to_datetime(row['scheduled_date']).date()
                
                Visit.objects.update_or_create(
                    patient=patient,
                    visit_number=visit_num,
                    defaults={
                        'visit_name': visit_name,
                        'scheduled_date': scheduled_date,
                        'is_missing': True,
                        'is_completed': False
                    }
                )
                
                self.rows_processed += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: {str(e)}")
    
    def parse_open_queries(self, df):
        """Parse open queries file"""
        required_cols = ['site_number', 'patient_id', 'query_id', 'opened_date']
        
        if not all(col in df.columns for col in required_cols):
            self.errors.append(f"Missing required columns. Required: {required_cols}")
            return
        
        for idx, row in df.iterrows():
            try:
                site = self.get_or_create_site(row['site_number'])
                patient = self.get_or_create_patient(site, row['patient_id'])
                
                # Parse opened date
                opened_date = pd.to_datetime(row['opened_date']).date()
                
                # Calculate days open
                days_open = (timezone.now().date() - opened_date).days
                
                Query.objects.update_or_create(
                    query_id=str(row['query_id']).strip(),
                    defaults={
                        'patient': patient,
                        'query_text': row.get('query_text', 'No description'),
                        'query_type': row.get('query_type', 'missing_data'),
                        'severity': row.get('severity', 'medium'),
                        'opened_date': opened_date,
                        'is_resolved': False,
                        'days_open': days_open
                    }
                )
                
                self.rows_processed += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: {str(e)}")
    
    def parse_coding_issues(self, df):
        """Parse coding issues file"""
        required_cols = ['site_number', 'patient_id', 'term']
        
        if not all(col in df.columns for col in required_cols):
            self.errors.append(f"Missing required columns. Required: {required_cols}")
            return
        
        for idx, row in df.iterrows():
            try:
                site = self.get_or_create_site(row['site_number'])
                patient = self.get_or_create_patient(site, row['patient_id'])
                
                issue_type = row.get('issue_type', 'meddra').lower()
                if issue_type not in ['meddra', 'whodd', 'other']:
                    issue_type = 'other'
                
                CodingIssue.objects.create(
                    patient=patient,
                    issue_type=issue_type,
                    term=str(row['term']).strip(),
                    suggested_code=row.get('suggested_code', ''),
                    is_resolved=False
                )
                
                self.rows_processed += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: {str(e)}")
    
    def parse_visit_projections(self, df):
        """Parse visit projections vs actuals"""
        required_cols = ['site_number', 'patient_id', 'visit_number', 'projected_date']
        
        if not all(col in df.columns for col in required_cols):
            self.errors.append(f"Missing required columns. Required: {required_cols}")
            return
        
        for idx, row in df.iterrows():
            try:
                site = self.get_or_create_site(row['site_number'])
                patient = self.get_or_create_patient(site, row['patient_id'])
                
                visit_num = str(row['visit_number']).strip()
                projected_date = pd.to_datetime(row['projected_date']).date()
                
                actual_date = None
                is_completed = False
                
                if 'actual_date' in row and pd.notna(row['actual_date']):
                    actual_date = pd.to_datetime(row['actual_date']).date()
                    is_completed = True
                
                Visit.objects.update_or_create(
                    patient=patient,
                    visit_number=visit_num,
                    defaults={
                        'visit_name': row.get('visit_name', f"Visit {visit_num}"),
                        'scheduled_date': projected_date,
                        'actual_date': actual_date,
                        'is_completed': is_completed,
                        'is_missing': not is_completed
                    }
                )
                
                self.rows_processed += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: {str(e)}")
    
    def get_errors(self):
        """Return parsing errors"""
        return "\n".join(self.errors) if self.errors else ""