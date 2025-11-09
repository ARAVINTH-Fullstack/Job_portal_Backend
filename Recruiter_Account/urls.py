from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('company', CompanyProfileViewSet, basename='company')
router.register('jobs', JobViewSet, basename='jobs')
router.register('applications', JobApplicationViewSet,basename="application")
router.register('job_count', RecruiterDashboardViewSet,basename='job_count')
router.register("insights", RecruiterInsightsViewSet, basename="recruiter-insights")

urlpatterns = [

    path('', include(router.urls)),
]
