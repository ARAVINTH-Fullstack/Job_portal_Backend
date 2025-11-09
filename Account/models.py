from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin,BaseUserManager
from django.conf import settings

class GoogleUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, user_type='candidate', **extra_fields):
        if not email:
            raise ValueError('User must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, user_type=user_type, **extra_fields)

        if password:
            user.set_password(password)  # Recruiter
        else:
            user.set_unusable_password()  # Candidate (Google)

        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, name, password, user_type='recruiter', **extra_fields)

class GoogleUser(AbstractBaseUser,PermissionsMixin):

    USER_TYPE_CHOICES = (
        ('candidate', 'Candidate'),
        ('recruiter', 'Recruiter'),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    picture = models.URLField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # New field
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='candidate')

    # User-edited data
    user_name = models.CharField(max_length=100, blank=True, null=True)
    user_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    job_role = models.CharField(max_length=100, blank=True, null=True)

    # Django admin fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = GoogleUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.name

class About(models.Model):
    user = models.OneToOneField(GoogleUser,on_delete=models.CASCADE,related_name="about")
    description = models.TextField(null=False,blank=False)

    def __str__(self):
        return self.description


class Education(models.Model):
    user = models.ForeignKey(GoogleUser,on_delete=models.CASCADE,related_name="education")
    school_name = models.CharField(max_length=300,null=False,blank=False)
    field_name = models.CharField(max_length=300,null=False,blank=False)
    start_year = models.IntegerField()
    end_year = models.IntegerField()

    class Meta:
        unique_together = ('user', 'school_name', 'field_name', 'start_year', 'end_year')

class Experience(models.Model):
    user = models.ForeignKey(GoogleUser,on_delete=models.CASCADE,related_name="experience")
    company_name = models.CharField(max_length=200)
    position_name = models.CharField(max_length=200)
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    description = models.TextField()

    class Meta:
        unique_together = ('user', 'company_name', 'position_name', 'start_year', 'end_year','description')    

class Skill(models.Model):
    user = models.ForeignKey(GoogleUser,on_delete=models.CASCADE,related_name="skill")
    skill_name = models.CharField(max_length=300)

    class Meta:
        unique_together = ('user','skill_name')

class Project(models.Model):
    user = models.ForeignKey(GoogleUser,on_delete=models.CASCADE,related_name="project")
    project_name = models.CharField(max_length=300)
    description = models.TextField()

    class Meta:
        unique_together = ('user', 'project_name')

class Resume(models.Model):
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resumes"
    )
    file = models.FileField(upload_to="resumes/")
    ats_score = models.IntegerField(default=0)
    hire_chance = models.IntegerField(default=0)
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    processed = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProfileView(models.Model):
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_views"
    )
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viewed_profiles"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.viewer} viewed {self.candidate}"
