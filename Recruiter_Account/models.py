# recruiter/models.py
from django.db import models
from django.conf import settings
from Account.models import GoogleUser  # assuming you already have this

from django.conf import settings

class CompanyProfile(models.Model):
    recruiter = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    number_of_employees = models.CharField(
        max_length=50,
        choices=[
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-500', '201-500 employees'),
            ('500+', '500+ employees'),
        ],
        blank=True,
        null=True
    )
    location = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    company = models.ForeignKey(
        'CompanyProfile', on_delete=models.CASCADE, related_name='jobs'
    )

    title = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('full-time', 'Full-time'),
            ('part-time', 'Part-time'),
            ('internship', 'Internship'),
            ('contract', 'Contract'),
            ('freelance', 'Freelance')
        ],
        default='full-time'
    )
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    experience_required = models.CharField(max_length=100, blank=True)
    skills_required = models.TextField(blank=True)
    education_required = models.CharField(max_length=200, blank=True)

    job_type = models.CharField(max_length=50, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    remote_option = models.BooleanField(default=False)
    posted_by = models.ForeignKey(
        'Account.GoogleUser', on_delete=models.SET_NULL, null=True, blank=True
    )

    # Structured fields for description
    about_job = models.TextField(blank=True)
    key_responsibilities = models.TextField(blank=True)
    qualifications = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    job_slug = models.SlugField(max_length=250, unique=True, blank=True)

    def __str__(self):
        return f"{self.title} at {self.company.name}"



class JobApplication(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_applications')
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('applied', 'Applied'),
            ('shortlisted', 'Shortlisted'),
            ('interviewed', 'Interviewed'),
            ('offered', 'Offered'),
            ('rejected', 'Rejected'),
        ],
        default='applied'
    )

    class Meta:
        unique_together = ('job', 'candidate')  # Prevent duplicate applications

    def __str__(self):
        return f"{self.candidate.email} - {self.job.title}"

