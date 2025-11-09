from rest_framework import serializers
from .models import GoogleUser,About,Education,Experience,Skill,Project,Resume

class GoogleUserSerializer(serializers.ModelSerializer):
    user_picture_url = serializers.SerializerMethodField()
    class Meta:
        model = GoogleUser
        fields = ["id","name","email","picture","user_name","user_picture","job_role","user_picture_url","created_at"]
    
    def get_user_picture_url(self, obj):
        request = self.context.get('request')
        if obj.user_picture:
            if request:
                return request.build_absolute_uri(obj.user_picture.url)
            return obj.user_picture.url
        return obj.picture  # fallback to google picture

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleUser
        fields = ["user_name", "user_picture", "job_role"]

    def update(self, instance, validated_data):
        if "user_name" in validated_data:
            instance.user_name = validated_data["user_name"]
        if "job_role" in validated_data:
            instance.user_name = validated_data["job_role"]
        if "user_picture" in validated_data:
            instance.user_picture = validated_data["user_picture"]
        instance.save()
        return instance
    
class RecruiterRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = GoogleUser
        fields = ['name', 'email', 'password']

    def create(self, validated_data):
        return GoogleUser.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            user_type='recruiter'  # 🔹 Force recruiter type
        )

class AboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = About
        fields = ['id', 'user', 'description']
        read_only_fields = ['user']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'school_name','field_name','start_year','end_year']
        read_only_fields = ['id']
    
    def validate(self, attrs):
        user = self.context['request'].user
        if Education.objects.filter(
            user=user,
            school_name=attrs['school_name'],
            field_name=attrs['field_name'],
            start_year=attrs['start_year'],
            end_year=attrs['end_year']
        ).exists():
            raise serializers.ValidationError("This education entry already exists.")
        return attrs

class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['id', 'company_name','position_name','start_year','end_year','description']
        read_only_fields = ['id']
    
    def validate(self, attrs):
        user = self.context['request'].user
        if Experience.objects.filter(
            user=user,
            company_name=attrs['company_name'],
            position_name=attrs['position_name'],
            start_year=attrs['start_year'],
            end_year=attrs['end_year'],
            description=attrs['description']
        ).exists():
            raise serializers.ValidationError("This education entry already exists.")
        return attrs

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'skill_name']
        read_only_fields = ['id']

    def validate_name(self, value):
        user = self.context['request'].user
        if Skill.objects.filter(user=user, skill_name__iexact=value).exists():
            raise serializers.ValidationError("This skill already exists.")
        return value

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'project_name','description']
        read_only_fields = ['user']

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = '__all__'
        read_only_fields = ['candidate', 'ats_score', 'hire_chance', 'strengths', 'weaknesses', 'processed', 'created_at', 'updated_at']