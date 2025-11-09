from django.shortcuts import render,get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status,generics,permissions,viewsets,serializers
from .serializers import GoogleUserSerializer,AboutSerializer,EducationSerializer,ExperienceSerializer,SkillSerializer,ProjectSerializer,RecruiterRegisterSerializer,ResumeSerializer
from .models import GoogleUser,About,Education,Experience,Skill,Project,Resume
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from PyPDF2 import PdfReader
import google.generativeai as genai
from django.conf import settings
import json
from google import genai  # sdk import from google‑genai
import json
import re
from django.db import connection

class ServerHealthCheckView(APIView):
    def get(self, request):
        try:
            # Simple DB check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_status = "ok"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return Response({
            "server": "live",
            "database": db_status,
            "status": "success" if db_status == "ok" else "fail"
        }, status=status.HTTP_200_OK if db_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE)
    


class GoogleLoginAPIView(APIView):
   
    authentication_classes = []
    permission_classes = []

    def get(self,request):
       pass
        
    def post(self, request):
        name = request.data.get("name")
        email = request.data.get("email")
        picture = request.data.get("picture")

        if not email:
            return Response({"detail": "Email required"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = GoogleUser.objects.get_or_create(
            email=email,
            defaults={"name": name, "picture": picture}
        )
        if not user.id:
                return Response({"error": "User creation failed"}, status=400)

        # Issue JWT tokens for this user
        refresh = RefreshToken.for_user(user)

        serializer = GoogleUserSerializer(user)

        return Response({
            "user": serializer.data,
            "access": str(refresh.access_token),
            "refresh":str(refresh)
        })
    

class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = GoogleUserSerializer(request.user,context={'request': request})
        return Response(serializer.data)
    
class RecruiterRegisterView(APIView):
    def post(self, request):
        serializer = RecruiterRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Save the recruiter

            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            user_serializer = RecruiterRegisterSerializer(user)  # Serialize recruiter data

            return Response({
                "message": "Recruiter account created successfully",
                "user": user_serializer.data,
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class RecruiterLoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"detail": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate the recruiter
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user info
        user_serializer = RecruiterRegisterSerializer(user)

        return Response({
            "message": "Login successful",
            "user": user_serializer.data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)
    
class AboutView(generics.RetrieveUpdateAPIView):
    serializer_class = AboutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        about, created = About.objects.get_or_create(user=self.request.user)
        return about

class UpdateProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        data = request.data

        user.user_name = data.get("user_name", user.user_name)
        user.job_role = data.get("job_role", user.job_role)

        # Handle picture upload
        if request.FILES.get("user_picture"):
            user.user_picture = request.FILES["user_picture"]

        user.save()

        serializer = GoogleUserSerializer(user,context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class EducationListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        educations = Education.objects.filter(user=request.user)
        serializer = EducationSerializer(educations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        # Convert single object to list if not already
        if not isinstance(data, list):
            data = [data]

        created = []
        skipped = []

        # Get all existing entries for the user
        existing = Education.objects.filter(user=request.user).values_list(
            'school_name', 'field_name', 'start_year', 'end_year'
        )
        existing_set = set(existing)

        # Track duplicates within this batch
        new_set = set()

        for edu_item in data:
            key = (
                edu_item['school_name'],
                edu_item['field_name'],
                int(edu_item['start_year']),
                int(edu_item['end_year'])
            )

            # Skip if exists in DB or already added in this request
            if key in existing_set or key in new_set:
                skipped.append(edu_item)
                continue

            new_set.add(key)

            # Save new entry
            edu = Education.objects.create(
                user=request.user,
                school_name=edu_item['school_name'],
                field_name=edu_item['field_name'],
                start_year=key[2],
                end_year=key[3]
            )
            created.append(EducationSerializer(edu).data)

        return Response({"created": created, "skipped": skipped}, status=status.HTTP_201_CREATED)
    
# Detail GET / PUT / DELETE
class EducationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Education, pk=pk, user=self.request.user)

    def get(self, request, pk):
        edu = self.get_object(pk)
        serializer = EducationSerializer(edu)
        return Response(serializer.data)

    def put(self, request, pk):
        edu = self.get_object(pk)
        serializer = EducationSerializer(edu, data=request.data,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        edu = self.get_object(pk)
        edu.delete()
        return Response({"detail": "Education deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    

class ExperienceListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        experience = Experience.objects.filter(user=request.user)
        serializer = ExperienceSerializer(experience, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        # Convert single object to list if not already
        if not isinstance(data, list):
            data = [data]

        created = []
        skipped = []

        # Get all existing entries for the user
        existing = Experience.objects.filter(user=request.user).values_list(
            'company_name', 'position_name', 'start_year', 'end_year', 'description'
        )
        existing_set = set(existing)

        # Track duplicates within this batch
        new_set = set()

        for edu_item in data:
            key = (
                edu_item['company_name'],
                edu_item['position_name'],
                int(edu_item['start_year']),
                int(edu_item['end_year']),
                edu_item['description']
            )

            # Skip if exists in DB or already added in this request
            if key in existing_set or key in new_set:
                skipped.append(edu_item)
                continue

            new_set.add(key)

            # Save new entry
            edu = Experience.objects.create(
                user=request.user,
                company_name=edu_item['company_name'],
                position_name=edu_item['position_name'],
                start_year=key[2],
                end_year=key[3],
                description=key[4]
            )
            created.append(ExperienceSerializer(edu).data)

        return Response({"created": created, "skipped": skipped}, status=status.HTTP_201_CREATED)
    
# Retrieve, Update, Delete Experience
class ExperienceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(Experience, pk=pk, user=user)

    def put(self, request, pk):
        experience = self.get_object(pk, request.user)
        serializer = ExperienceSerializer(experience, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        experience = self.get_object(pk, request.user)
        experience.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class SkillListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Return all skills for the authenticated user.
        """
        skills = Skill.objects.filter(user=request.user).order_by('skill_name')
        serializer = SkillSerializer(skills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
    
        data = request.data

        if not isinstance(data, list):
            return Response(
                {"detail": "Expected a list of skill names."},
                status=status.HTTP_400_BAD_REQUEST
            )

        skills_to_add = []
        existing_skills = []

        for name in data:
            name = name.strip()
            if not name:
                continue
            if Skill.objects.filter(user=request.user, skill_name__iexact=name).exists():
                existing_skills.append(name)
            else:
                skills_to_add.append(Skill(user=request.user, skill_name=name))

        if existing_skills:
            return Response(
                {"detail": f"These skills already exist: {', '.join(existing_skills)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if skills_to_add:
            Skill.objects.bulk_create(skills_to_add)
            return Response({"message": "Skills added successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"detail": "No new skills to add."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    def delete(self, request, pk=None):
        try:
            skill = Skill.objects.get(pk=pk, user=request.user)
        except Skill.DoesNotExist:
            return Response({"error": "Skill not found."}, status=status.HTTP_404_NOT_FOUND)

        skill.delete()
        return Response({"message": "Skill deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class ProjectBulkView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        projects = Project.objects.filter(user=request.user)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Expecting a list of projects
        projects_data = request.data if isinstance(request.data, list) else [request.data]

        created_projects = []
        for project in projects_data:
            # Prevent duplicates
            if not Project.objects.filter(
                user=request.user,
                project_name__iexact=project.get("project_name", "")
            ).exists():
                serializer = ProjectSerializer(data=project)
                if serializer.is_valid():
                    serializer.save(user=request.user)
                    created_projects.append(serializer.data)

        if not created_projects:
            return Response({"detail": "No new projects to add."}, status=200)

        # ✅ Return the list (important!)
        return Response(created_projects, status=201)

class ProjectDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Project, pk=pk, user=self.request.user)

    # PUT to update project
    def put(self, request, pk):
        project = self.get_object(pk)
        serializer = ProjectSerializer(project, data=request.data,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE project
    def delete(self, request, pk):
        project = self.get_object(pk)
        project.delete()
        return Response({"detail": "Project deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    



class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(candidate=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        file_obj = self.request.FILES.get('file')
        if not file_obj:
            raise ValueError("No file uploaded")

        # Extract text from the uploaded PDF
        try:
            pdf = PdfReader(file_obj)
            text = " ".join([page.extract_text() or "" for page in pdf.pages])
        except Exception as e:
            print(f"PDF extraction failed: {e}")
            text = ""

        # Initialize genai client
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        prompt = f"""
        Analyze this resume and return structured JSON:
        {{
          "ats_score": 0-100,
          "hire_probability": 0-100,
          "strengths": [],
          "weaknesses": []
        }}
        Resume text:
        {text}
        """

        # Make the request to the model
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            output = response.text
            match = re.search(r"\{.*\}", output, re.DOTALL)
            data = json.loads(match.group()) if match else {}
        except Exception as e:
            print(f"GenAI API failed: {e}")
            data = {}

        ats_score = data.get("ats_score", 50)
        hire_probability = data.get("hire_probability", 50)
        strengths = "\n".join(data.get("strengths", []))
        weaknesses = "\n".join(data.get("weaknesses", []))

        # If the candidate has an existing resume, update it; else create a new one
        existing = Resume.objects.filter(candidate=self.request.user)
        if existing.exists():
            resume = existing.first()
            serializer.update(
                resume,
                {
                    "file": file_obj,
                    "ats_score": ats_score,
                    "hire_chance": hire_probability,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "processed": True
                }
            )
        else:
            serializer.save(
                candidate=self.request.user,
                file=file_obj,
                ats_score=ats_score,
                hire_chance=hire_probability,
                strengths=strengths,
                weaknesses=weaknesses,
                processed=True
            )



from .models import ProfileView

class CandidateDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1️⃣ Total jobs applied
        total_applied = user.job_applications.count()

        # 2️⃣ Total profile views
        profile_views = ProfileView.objects.filter(candidate=user).count()

        # 3️⃣ Interviewed count
        interviewed_count = user.job_applications.filter(status='interviewed').count()

        # 4️⃣ Success rate = interviewed / total_applied * 100
        success_rate = round((interviewed_count / total_applied) * 100, 1) if total_applied > 0 else 0

        # 5️⃣ Profile Completion (example logic)
        profile_fields = [
            user.name,
            user.email,
            getattr(user, 'phone_number', None),
            getattr(user, 'education', None),
            getattr(user, 'experience', None),
            getattr(user, 'skills', None),
            getattr(user, 'profile_picture', None)
        ]
        filled_fields = [f for f in profile_fields if f]  # Count non-empty fields
        profile_completion = round((len(filled_fields) / len(profile_fields)) * 100, 1)

        return Response({
            "total_applied": total_applied,
            "profile_views": profile_views,
            "interviewed": interviewed_count,
            "success_rate": success_rate,
            "profile_completion": profile_completion
        })

class CandidateMilestonesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # ✅ Define milestones thresholds for each field
    milestone_thresholds = {
        "total_applied": [1, 5, 10, 20, 50],
        "profile_views": [10, 25, 50, 100, 200],
        "interviewed": [1, 3, 5, 10, 20],
        "success_rate": [10, 30, 50, 70, 90],  # percentage
        "profile_completion": [20, 40, 60, 80, 100],  # percentage
    }

    def get_level(self, value, thresholds):
        for idx, threshold in enumerate(thresholds):
            if value < threshold:
                return idx + 1
        return len(thresholds)

    def get_tasks_to_next(self, value, thresholds, field_name):
        for threshold in thresholds:
            if value < threshold:
                # Field-specific formatting
                if field_name == "total_applied":
                    return f"{threshold - value} job{'s' if threshold - value > 1 else ''}"
                elif field_name == "profile_views":
                    return f"{threshold - value} views"
                elif field_name == "interviewed":
                    return f"{threshold - value} interview{'s' if threshold - value > 1 else ''}"
                elif field_name in ["success_rate", "profile_completion"]:
                    return f"{threshold - value}% to next level"
        return "Max level reached"

    def get(self, request):
        user = request.user

        # ✅ Gather raw values
        total_applied = user.job_applications.count()
        profile_views = ProfileView.objects.filter(candidate=user).count()
        interviewed = user.job_applications.filter(status="interviewed").count()
        success_rate = round((interviewed / total_applied) * 100, 1) if total_applied > 0 else 0
        profile_completion = user.profile_completion if hasattr(user, "profile_completion") else 0

        raw_values = {
            "total_applied": total_applied,
            "profile_views": profile_views,
            "interviewed": interviewed,
            "success_rate": success_rate,
            "profile_completion": profile_completion,
        }

        data = {}
        for key, value in raw_values.items():
            thresholds = self.milestone_thresholds[key]
            level = self.get_level(value, thresholds)
            tasks_next = self.get_tasks_to_next(value, thresholds, key)

            data[key] = {
                "value": value,
                "level": level,
                "tasks_to_next": tasks_next,
            }

        return Response(data)
    
class UserProfileInfoView(APIView):
    """
    Returns profile info for the logged-in user:
    - For candidates: user name and profile image
    - For recruiters: company name and logo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if hasattr(user, 'company_profile'):  # Recruiter
            profile = user.company_profile
            image_url = request.build_absolute_uri(profile.logo.url) if profile.logo else ""
            name = profile.name or user.name
            user_type = 'recruiter'
        else:  # Candidate
            image_url = (
                request.build_absolute_uri(user.user_picture.url)
                if user.user_picture else
                user.picture or ""
            )
            name = user.user_name or user.name
            user_type = 'candidate'

        return Response({
            "name": name,
            "imageUrl": image_url,
            "userType": user_type
        })