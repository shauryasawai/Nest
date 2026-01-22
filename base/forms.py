from django import forms
from .models import ExcelUpload, Study

class ExcelUploadForm(forms.ModelForm):
    class Meta:
        model = ExcelUpload
        fields = ['study', 'file_type', 'file']
        widgets = {
            'study': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls,.csv',
                'required': True
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            if not file.name.endswith(('.xlsx', '.xls', '.csv')):
                raise forms.ValidationError('Only Excel files (.xlsx, .xls) or CSV files are allowed.')
            
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')
        
        return file


class StudyFilterForm(forms.Form):
    study = forms.ModelChoiceField(
        queryset=Study.objects.all(),
        required=False,
        empty_label="All Studies",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('closed', 'Closed')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class AIQueryForm(forms.Form):
    query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ask a question about the data (e.g., "Which sites need immediate attention?" or "What are the main issues at Site 101?")'
        }),
        max_length=500
    )
    
    context_type = forms.ChoiceField(
        choices=[
            ('study', 'Study Level'),
            ('site', 'Site Level'),
            ('patient', 'Patient Level')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    context_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False
    )