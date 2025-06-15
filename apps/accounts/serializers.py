# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, PasswordResetToken
import secrets


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    group_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'avatar', 'bio', 'is_active', 'is_staff',
            'date_joined', 'last_login', 'groups', 'group_names'
        )
        read_only_fields = ('id', 'date_joined', 'last_login', 'is_staff')
    
    def update(self, instance, validated_data):
        group_names = validated_data.pop('group_names', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update groups if provided
        if group_names is not None:
            instance.groups.clear()
            for group_name in group_names:
                group, _ = Group.objects.get_or_create(name=group_name)
                instance.groups.add(group)
        
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    tokens = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'password', 'password2',
            'first_name', 'last_name', 'tokens'
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        
        # Add default User group
        user_group, _ = Group.objects.get_or_create(name='User')
        user.groups.add(user_group)
        
        return user
    
    def get_tokens(self, obj):
        refresh = RefreshToken.for_user(obj)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'Email ou mot de passe incorrect.',
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'Ce compte a été désactivé.',
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                'Email et mot de passe sont requis.',
                code='authorization'
            )
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Les nouveaux mots de passe ne correspondent pas."
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("L'ancien mot de passe est incorrect.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            # Pour des raisons de sécurité, on ne révèle pas si l'email existe
            pass
        return value
    
    def save(self):
        email = self.validated_data['email']
        try:
            user = User.objects.get(email=email)
            # Générer un token unique
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(user=user, token=token)
            
            # Envoyer l'email via Celery
            from .tasks import send_password_reset_email
            send_password_reset_email.delay(user.id, token)
            
        except User.DoesNotExist:
            # Pour des raisons de sécurité, on ne fait rien
            pass


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Les mots de passe ne correspondent pas."
            })
        
        try:
            reset_token = PasswordResetToken.objects.get(
                token=attrs['token'],
                used=False
            )
            if reset_token.is_expired():
                raise serializers.ValidationError({
                    "token": "Ce lien de réinitialisation a expiré."
                })
            attrs['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                "token": "Lien de réinitialisation invalide."
            })
        
        return attrs
    
    def save(self):
        reset_token = self.validated_data['reset_token']
        user = reset_token.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        
        # Marquer le token comme utilisé
        reset_token.used = True
        reset_token.save()