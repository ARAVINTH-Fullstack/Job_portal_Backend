# recruiter/serializers.py
from rest_framework import serializers
from .models import CompanyProfile, Job, JobApplication

class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = '__all__'
        read_only_fields = ['recruiter', 'created_at', 'updated_at']


class JobSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source='company.name')
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'company',
            'company_name',
            'title',
            'location',
            'employment_type',
            'salary_min',
            'salary_max',
            'experience_required',
            'skills_required',
            'education_required',
            'job_type',
            'remote_option',
            'application_deadline',
            'posted_by',
            'created_at',
            'updated_at',
            'is_active',
            'job_slug',
            'about_job',
            'key_responsibilities',
            'qualifications',
            'applications_count',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'job_slug',
            'posted_by',
            'company', 
        ]

    def create(self, validated_data):
        user = self.context['request'].user

        # ✅ Check if recruiter has a company profile
        if not hasattr(user, 'company_profile'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Please complete your company profile before posting a job.")

        validated_data['posted_by'] = user
        job = super().create(validated_data)
        
        # Generate a slug
        job.job_slug = f"{job.title.replace(' ', '-')}-{job.id}"
        job.save()
        return job

    
    def get_applications_count(self, obj):
        return obj.applications.count()


class JobApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.ReadOnlyField(source='candidate.name')
    job_title = serializers.ReadOnlyField(source='job.title')
    company_logo = serializers.SerializerMethodField()
    job_details = JobSerializer(source="job",read_only=True) 
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_title', 'candidate', 'candidate_name',
            'resume', 'applied_at', 'status', 'company_logo','job_details','company_name'
        ]
        read_only_fields = ['id', 'candidate', 'applied_at']

    def validate(self, data):
        request = self.context.get("request")
        user = request.user if request else None

        # Prevent candidates from editing status
        if request and request.method in ["PUT", "PATCH"] and not hasattr(user, "company_profile"):
            if "status" in data:
                raise serializers.ValidationError("You cannot modify the application status.")
        return data
    
    def get_company_logo(self, obj):
        request = self.context.get('request')
        if obj.job.company.logo:
            return request.build_absolute_uri(obj.job.company.logo.url)
        return None
    def get_company_name(self, obj):
        # obj.job is the related Job object
        if obj.job and obj.job.company and obj.job.company.name:
            return obj.job.company.name
        return None