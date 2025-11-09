from rest_framework import viewsets, permissions,status
from .models import CompanyProfile, Job, JobApplication
from .serializers import CompanyProfileSerializer, JobSerializer, JobApplicationSerializer
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from Account.models import Resume
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum


class CompanyProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ensure the recruiter only sees their own profile
        return CompanyProfile.objects.filter(recruiter=self.request.user)

    def create(self, request, *args, **kwargs):
        # Allow creation only if recruiter doesn't have a profile yet
        if CompanyProfile.objects.filter(recruiter=request.user).exists():
            return Response(
                {"detail": "Profile already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(recruiter=self.request.user)

    def list(self, request, *args, **kwargs):
        # Override list to return only the single profile if it exists
        profile = self.get_queryset().first()
        if not profile:
            return Response({}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by('-created_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['location', 'employment_type', 'remote_option', 'is_active']
    search_fields = ['title', 'skills_required', 'description']

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company_profile,
            posted_by=self.request.user
        )

    def get_queryset(self):
        queryset = Job.objects.all().order_by('-created_at')

        # Optional query param filters (safe for candidate view)
        location = self.request.query_params.get('location')
        employment_type = self.request.query_params.get('employment_type')
        remote_option = self.request.query_params.get('remote_option')

        if location:
            queryset = queryset.filter(location__icontains=location)
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)
        if remote_option:
            queryset = queryset.filter(remote_option=remote_option.lower() in ['true', '1'])

        # ✅ Annotate each job with application count to avoid extra queries
        queryset = queryset.annotate(applications_count=Count('applications'))

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        for item in data:
            job_instance = queryset.get(id=item['id'])
            item['company_logo'] = (
                request.build_absolute_uri(job_instance.company.logo.url)
                if job_instance.company.logo
                else None
            )

        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        data['company_logo'] = (
            request.build_absolute_uri(instance.company.logo.url)
            if instance.company.logo
            else None
        )
        return Response(data)


class JobApplicationViewSet(viewsets.ModelViewSet):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "company_profile"):
            # Recruiter view: show applications for their jobs
            return JobApplication.objects.filter(job__company=user.company_profile)
        # Candidate view: show their own job applications
        return JobApplication.objects.filter(candidate=user)

    def perform_create(self, serializer):
        user = self.request.user

        # 🚫 Recruiters cannot apply for jobs
        if hasattr(user, "company_profile"):
            raise PermissionDenied("Recruiters cannot apply for jobs.")

        # 🧾 Check if resume exists
        resume = Resume.objects.filter(candidate=user).order_by("-created_at").first()
        if not resume:
            raise ValidationError({"error": "Resume upload required before applying."})

        # ⚠️ Prevent duplicate applications
        job = serializer.validated_data.get("job")
        if JobApplication.objects.filter(candidate=user, job=job).exists():
            raise ValidationError({"error": "You have already applied for this job."})

        # ✅ Save application with the candidate’s latest resume
        serializer.save(candidate=user, resume=resume.file)

    def create(self, request, *args, **kwargs):
        """Custom create to return cleaner frontend messages."""
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

class RecruiterDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        recruiter = request.user

        # ✅ Recruiter’s posted jobs
        jobs = Job.objects.filter(posted_by=recruiter)
        total_jobs_posted = jobs.count()

        # ✅ Applications for recruiter's jobs
        applications = JobApplication.objects.filter(job__in=jobs)
        total_applicants = applications.count()

        # ✅ Interviewed & Offered
        interviewed_count = applications.filter(status='interviewed').count()
        offered_count = applications.filter(status='offered').count()


        data = {
            "jobs_posted": total_jobs_posted,
            "total_applicants": total_applicants,
            "interviewed": interviewed_count,
            "offered": offered_count,
        }

        return Response(data)
    
class RecruiterInsightsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        recruiter = request.user

        # Only allow recruiters (must have company_profile)
        if not hasattr(recruiter, "company_profile"):
            return Response({"detail": "Only recruiters can access this."}, status=403)

        # Jobs posted by recruiter
        jobs = Job.objects.filter(company=recruiter.company_profile)
        job_count = jobs.count()

        # Applications for these jobs
        applications = JobApplication.objects.filter(job__in=jobs)
        total_applications = applications.count()

        # Average applications per job
        avg_applications_per_job = round(total_applications / job_count, 2) if job_count > 0 else 0

        # Response rate = processed applications / total applications * 100
        processed_statuses = ["interviewed", "offered", "rejected"]
        processed_count = applications.filter(status__in=processed_statuses).count()
        response_rate = round((processed_count / total_applications) * 100, 1) if total_applications > 0 else 0

        # Job reach = sum of job views (assuming Job has a 'views' field)
        job_reach = total_applications

        return Response({
            "avg_applications_per_job": avg_applications_per_job,
            "response_rate": response_rate,
            "job_views": job_reach
            
        })