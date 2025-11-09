from django.urls import path,include
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('resume', ResumeViewSet, basename='resume')

urlpatterns = [
    path('', ServerHealthCheckView.as_view(), name='server_health_check'),
    path('api/auth/',GoogleLoginAPIView.as_view(),name="google"),
    path('api/auth/recruiter/', RecruiterRegisterView.as_view(), name='register-recruiter'),
    path("api/auth/recruiter/login/", RecruiterLoginView.as_view(), name="recruiter-login"),
    path('api/currentuser/',CurrentUserAPIView.as_view(),name="currentuser"),
    path("api/update-profile/", UpdateProfileAPIView.as_view(), name="update-profile"),
    path('api/token/refresh/',TokenRefreshView.as_view(),name="token_refresh"),
    path('api/about/',AboutView.as_view(),name="about"),
    path('api/add/education/',EducationListCreateView.as_view(),name="education"),
    path('api/add/education/<int:pk>/',EducationDetailView.as_view(),name="education"),
    path('api/add/experience/',ExperienceListCreateView.as_view(),name="experince"),
    path('api/add/experience/<int:pk>/',ExperienceDetailView.as_view(),name="experince"),
    path('api/add/skill/',SkillListCreateView.as_view(),name="skills"),
    path('api/add/skill/<int:pk>/',SkillListCreateView.as_view(),name="skills"),
    path('api/add/project/',ProjectBulkView.as_view(),name="project"),
    path('api/add/project/<int:pk>/',ProjectDetailView.as_view(),name="project_edit_or_delete"),

    path('api/candidate/apply_count/', CandidateDashboardAPIView.as_view(), name='candidate-dashboard'),
    path('api/candidate/badges/', CandidateMilestonesAPIView.as_view(), name='candidate-dashboard'),
    path("api/profile-info/", UserProfileInfoView.as_view(), name="user-profile-info"),

    path('api/', include(router.urls)), 
    
]




