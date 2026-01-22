import os
import hashlib
from openai import OpenAI
from django.core.cache import cache
from django.conf import settings
from ..models import AIInsight

class AIIntegration:
    """Integration with OpenAI for generating insights"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', 500))
        self.cache_timeout = int(os.getenv('AI_CACHE_TIMEOUT', 3600))
        self.enabled = os.getenv('AI_ENABLED', 'True') == 'True'
    
    def generate_cache_key(self, prompt, context_type, context_id):
        """Generate cache key for AI response"""
        content = f"{prompt}_{context_type}_{context_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def generate_insight(self, prompt, context_data, insight_type='summary', 
                        site=None, patient=None, study=None):
        """Generate AI insight with caching"""
        
        if not self.enabled:
            return "AI insights are currently disabled."
        
        # Generate cache key
        context_id = site.id if site else (patient.id if patient else (study.id if study else 0))
        context_type = 'site' if site else ('patient' if patient else 'study')
        cache_key = self.generate_cache_key(prompt, context_type, context_id)
        
        # Check cache first
        cached_response = cache.get(f'ai_insight_{cache_key}')
        if cached_response:
            return cached_response
        
        # Check database for existing insight
        existing_insight = AIInsight.objects.filter(cache_key=cache_key).first()
        if existing_insight:
            cache.set(f'ai_insight_{cache_key}', existing_insight.content, self.cache_timeout)
            return existing_insight.content
        
        # Generate new insight
        try:
            full_prompt = self._build_full_prompt(prompt, context_data)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a clinical data analyst expert. Provide clear, actionable insights about clinical trial data quality issues. Be concise and specific."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Save to database
            AIInsight.objects.create(
                site=site,
                patient=patient,
                study=study,
                insight_type=insight_type,
                title=prompt[:200],
                content=content,
                cache_key=cache_key,
                metadata={'prompt': prompt, 'context_type': context_type}
            )
            
            # Cache the response
            cache.set(f'ai_insight_{cache_key}', content, self.cache_timeout)
            
            return content
            
        except Exception as e:
            return f"Error generating AI insight: {str(e)}"
    
    def _build_full_prompt(self, user_prompt, context_data):
        """Build complete prompt with context"""
        context_str = "\n".join([f"{k}: {v}" for k, v in context_data.items()])
        
        return f"""
Context Data:
{context_str}

User Question: {user_prompt}

Provide a clear, concise analysis focusing on:
1. Key issues identified
2. Root causes (if applicable)
3. Recommended actions
4. Priority level

Keep the response under 300 words.
"""
    
    def generate_site_summary(self, site):
        """Generate executive summary for a site"""
        metrics = site.get_metrics()
        
        context_data = {
            'Site Number': site.site_number,
            'Site Name': site.site_name,
            'DQI Score': f"{site.dqi_score}/100",
            'Total Patients': metrics['total_patients'],
            'Clean Patients': metrics['clean_patients'],
            'Open Queries': metrics['open_queries'],
            'Average Query Age': f"{metrics['avg_query_age']} days",
            'Visit Completion Rate': f"{metrics['completion_rate']}%"
        }
        
        prompt = f"Provide an executive summary of Site {site.site_number}'s data quality status and recommended actions."
        
        return self.generate_insight(
            prompt, 
            context_data, 
            insight_type='summary',
            site=site
        )
    
    def generate_root_cause_analysis(self, site):
        """Analyze root causes of low DQI"""
        from ..models import Query
        
        metrics = site.get_metrics()
        recent_queries = Query.objects.filter(
            patient__site=site, 
            is_resolved=False
        ).order_by('-days_open')[:5]
        
        query_info = "; ".join([
            f"Query {q.query_id} ({q.days_open} days old): {q.query_type}"
            for q in recent_queries
        ])
        
        context_data = {
            'Site': f"{site.site_number} - {site.site_name}",
            'DQI Score': site.dqi_score,
            'Recent Query Patterns': query_info,
            'Open Queries': metrics['open_queries'],
            'Avg Query Age': metrics['avg_query_age']
        }
        
        prompt = f"Analyze the root causes of Site {site.site_number}'s data quality issues and suggest corrective actions."
        
        return self.generate_insight(
            prompt,
            context_data,
            insight_type='root_cause',
            site=site
        )
    
    def answer_custom_query(self, question, context_type, context_id):
        """Answer custom user questions"""
        from ..models import Site, Patient, Study
        
        # Get context object
        context_obj = None
        if context_type == 'site':
            context_obj = Site.objects.get(id=context_id)
            context_data = {
                'Site': f"{context_obj.site_number} - {context_obj.site_name}",
                'DQI Score': context_obj.dqi_score,
                **context_obj.get_metrics()
            }
        elif context_type == 'patient':
            context_obj = Patient.objects.get(id=context_id)
            context_data = {
                'Patient ID': context_obj.patient_id,
                'Status': context_obj.status,
                'Issues Count': context_obj.issues_count,
                'Site': context_obj.site.site_number
            }
        elif context_type == 'study':
            context_obj = Study.objects.get(id=context_id)
            context_data = {
                'Study': f"{context_obj.study_id} - {context_obj.study_name}",
                'Total Sites': context_obj.sites.count(),
                'Average DQI': context_obj.get_overall_dqi(),
                'Clean Patients %': context_obj.get_clean_patients_percentage()
            }
        else:
            return "Invalid context type."
        
        kwargs = {f'{context_type}': context_obj}
        
        return self.generate_insight(
            question,
            context_data,
            insight_type='summary',
            **kwargs
        )