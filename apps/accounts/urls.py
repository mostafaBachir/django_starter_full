# apps/accounts/urls.py
from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    UserDetailView, UserListView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView,
    GroupListView, CustomTokenObtainPairView, CustomTokenRefreshView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # JWT Token
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Users Management
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<uuid:id>/', UserDetailView.as_view(), name='user_detail'),
    
    # Groups
    path('groups/', GroupListView.as_view(), name='group_list'),
]