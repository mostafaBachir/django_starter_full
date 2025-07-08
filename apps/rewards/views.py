from django.shortcuts import render

# Create your views here.
# apps/rewards/views.py
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import (
    UserReward, Reward, RewardRedemption,
    SpinWheel, Challenge, UserChallenge
)
from .serializers import (
    UserRewardSerializer, RewardSerializer, RewardRedemptionSerializer,
    SpinWheelSerializer, ChallengeSerializer, UserChallengeSerializer
)


class UserRewardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserRewardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserReward.objects.filter(user=self.request.user)


class RewardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Reward.objects.filter(is_active=True)
    serializer_class = RewardSerializer
    permission_classes = [IsAuthenticated]


class RewardRedemptionViewSet(viewsets.ModelViewSet):
    serializer_class = RewardRedemptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RewardRedemption.objects.filter(user=self.request.user)


class SpinWheelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SpinWheel.objects.filter(is_active=True)
    serializer_class = SpinWheelSerializer
    permission_classes = [IsAuthenticated]


class ChallengeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Challenge.objects.filter(is_active=True)
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]


class UserChallengeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserChallengeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserChallenge.objects.filter(user=self.request.user)


class SpinWheelView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # TODO: Implémenter le spin
        return Response({"message": "Spin wheel endpoint"})


class ClaimRewardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, reward_id):
        # TODO: Implémenter le claim
        return Response({"message": f"Claim reward {reward_id}"})


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # TODO: Implémenter le leaderboard
        return Response({"message": "Leaderboard endpoint"})