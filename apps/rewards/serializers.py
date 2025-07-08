# apps/rewards/serializers.py
from rest_framework import serializers
from .models import (
    RewardProgram, UserLevel, UserReward, PointTransaction,
    Reward, RewardRedemption, SpinWheel, SpinWheelPrize,
    SpinHistory, Challenge, UserChallenge, LevelUpNotification
)


class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLevel
        fields = [
            'level', 'name', 'icon', 'color', 'points_required',
            'receipts_required', 'cashback_bonus', 'points_multiplier',
            'daily_bonus_spins', 'perks'
        ]


class UserRewardSerializer(serializers.ModelSerializer):
    current_level = UserLevelSerializer(read_only=True)
    next_level = serializers.SerializerMethodField()
    points_to_next_level = serializers.SerializerMethodField()
    
    class Meta:
        model = UserReward
        fields = [
            'points_balance', 'lifetime_points', 'current_level',
            'next_level', 'level_progress', 'points_to_next_level',
            'spins_available', 'streak_days', 'longest_streak',
            'receipts_today', 'points_earned_today'
        ]
    
    def get_next_level(self, obj):
        if obj.current_level:
            next_level = UserLevel.objects.filter(
                level=obj.current_level.level + 1
            ).first()
            if next_level:
                return UserLevelSerializer(next_level).data
        return None
    
    def get_points_to_next_level(self, obj):
        next_level = self.get_next_level(obj)
        if next_level:
            return next_level['points_required'] - obj.lifetime_points
        return 0


class PointTransactionSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = PointTransaction
        fields = [
            'id', 'transaction_id', 'amount', 'transaction_type',
            'source', 'source_display', 'description', 'balance_after',
            'created_at'
        ]


class RewardSerializer(serializers.ModelSerializer):
    is_available = serializers.BooleanField(read_only=True)
    can_redeem = serializers.SerializerMethodField()
    
    class Meta:
        model = Reward
        fields = [
            'id', 'name', 'slug', 'description', 'reward_type',
            'category', 'image', 'icon', 'points_cost', 'cash_value',
            'stock_quantity', 'limit_per_user', 'required_level',
            'partner_name', 'partner_logo', 'is_available', 'can_redeem',
            'available_from', 'available_until', 'terms_conditions'
        ]
    
    def get_can_redeem(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_redeem, reason = obj.can_redeem(request.user)
            return {'status': can_redeem, 'reason': reason}
        return {'status': False, 'reason': 'Non connecté'}


class RewardRedemptionSerializer(serializers.ModelSerializer):
    reward = RewardSerializer(read_only=True)
    reward_id = serializers.PrimaryKeyRelatedField(
        queryset=Reward.objects.filter(is_active=True),
        source='reward',
        write_only=True
    )
    
    class Meta:
        model = RewardRedemption
        fields = [
            'id', 'redemption_id', 'reward', 'reward_id',
            'points_spent', 'status', 'delivery_method',
            'delivery_details', 'redemption_code', 'notes',
            'created_at', 'processed_at', 'delivered_at'
        ]
        read_only_fields = [
            'redemption_id', 'points_spent', 'status',
            'redemption_code', 'created_at', 'processed_at',
            'delivered_at'
        ]
    
    def validate_reward_id(self, value):
        user = self.context['request'].user
        can_redeem, reason = value.can_redeem(user)
        if not can_redeem:
            raise serializers.ValidationError(reason)
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        reward = validated_data['reward']
        
        # Créer la rédemption
        redemption = RewardRedemption.objects.create(
            user=user,
            reward=reward,
            points_spent=reward.points_cost,
            **validated_data
        )
        
        # Déduire les points
        user_reward = user.reward_status
        user_reward.points_balance -= reward.points_cost
        user_reward.save()
        
        # Créer la transaction
        PointTransaction.objects.create(
            user=user,
            amount=-reward.points_cost,
            transaction_type='spend',
            source='reward_redemption',
            description=f"Échange: {reward.name}",
            reward=reward,
            balance_after=user_reward.points_balance
        )
        
        # Mettre à jour le stock
        if reward.stock_quantity > 0:
            reward.stock_quantity -= 1
            reward.times_redeemed += 1
            reward.save()
        
        return redemption


class SpinWheelPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpinWheelPrize
        fields = [
            'id', 'name', 'prize_type', 'prize_value',
            'probability', 'color', 'icon', 'order'
        ]


class SpinWheelSerializer(serializers.ModelSerializer):
    prizes = SpinWheelPrizeSerializer(many=True, read_only=True)
    
    class Meta:
        model = SpinWheel
        fields = ['id', 'name', 'is_active', 'points_cost', 'theme', 'prizes']


class SpinHistorySerializer(serializers.ModelSerializer):
    prize_name = serializers.CharField(source='prize.name', read_only=True)
    
    class Meta:
        model = SpinHistory
        fields = [
            'id', 'wheel', 'prize', 'prize_name',
            'points_spent', 'prize_value', 'spun_at'
        ]


class ChallengeSerializer(serializers.ModelSerializer):
    is_current = serializers.BooleanField(read_only=True)
    user_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'slug', 'description', 'challenge_type',
            'target_type', 'target_value', 'target_category',
            'points_reward', 'cashback_reward', 'bonus_spins',
            'start_date', 'end_date', 'icon', 'color',
            'is_current', 'user_progress'
        ]
    
    def get_user_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_challenge = UserChallenge.objects.filter(
                user=request.user,
                challenge=obj
            ).first()
            if user_challenge:
                return {
                    'progress': user_challenge.progress,
                    'completed': user_challenge.completed,
                    'reward_claimed': user_challenge.reward_claimed
                }
        return None


class UserChallengeSerializer(serializers.ModelSerializer):
    challenge = ChallengeSerializer(read_only=True)
    percentage_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = UserChallenge
        fields = [
            'id', 'challenge', 'progress', 'completed',
            'completed_at', 'reward_claimed', 'percentage_complete'
        ]
    
    def get_percentage_complete(self, obj):
        if obj.challenge.target_value > 0:
            return min(100, int((obj.progress / obj.challenge.target_value) * 100))
        return 0


class LevelUpNotificationSerializer(serializers.ModelSerializer):
    old_level = UserLevelSerializer(read_only=True)
    new_level = UserLevelSerializer(read_only=True)
    
    class Meta:
        model = LevelUpNotification
        fields = [
            'id', 'old_level', 'new_level', 'seen', 'created_at'
        ]


class SpinRequestSerializer(serializers.Serializer):
    wheel_id = serializers.IntegerField()
    
    def validate_wheel_id(self, value):
        try:
            wheel = SpinWheel.objects.get(id=value, is_active=True)
        except SpinWheel.DoesNotExist:
            raise serializers.ValidationError("Roue invalide")
        
        user = self.context['request'].user
        user_reward = user.reward_status
        
        if wheel.points_cost > 0 and user_reward.points_balance < wheel.points_cost:
            raise serializers.ValidationError("Points insuffisants")
        
        if wheel.points_cost == 0 and user_reward.spins_available <= 0:
            raise serializers.ValidationError("Aucun spin gratuit disponible")
        
        return value