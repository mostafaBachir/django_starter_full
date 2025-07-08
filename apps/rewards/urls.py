# apps/rewards/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRewardViewSet, RewardViewSet, RewardRedemptionViewSet,
    SpinWheelViewSet, ChallengeViewSet, UserChallengeViewSet,
    SpinWheelView, ClaimRewardView, LeaderboardView
)

app_name = 'rewards'

router = DefaultRouter()
router.register(r'user-rewards', UserRewardViewSet, basename='user-reward')
router.register(r'rewards', RewardViewSet, basename='reward')
router.register(r'redemptions', RewardRedemptionViewSet, basename='redemption')
router.register(r'spin-wheels', SpinWheelViewSet, basename='spin-wheel')
router.register(r'challenges', ChallengeViewSet, basename='challenge')
router.register(r'user-challenges', UserChallengeViewSet, basename='user-challenge')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Custom endpoints
    path('spin/', SpinWheelView.as_view(), name='spin'),
    path('claim/<int:reward_id>/', ClaimRewardView.as_view(), name='claim-reward'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
]