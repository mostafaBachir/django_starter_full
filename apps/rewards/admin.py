# apps/rewards/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from .models import (
    RewardProgram, UserLevel, UserReward, PointTransaction,
    Reward, RewardRedemption, SpinWheel, SpinWheelPrize,
    SpinHistory, Challenge, UserChallenge, LevelUpNotification
)


@admin.register(RewardProgram)
class RewardProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'points_per_dollar', 'points_per_receipt',
        'daily_receipt_limit', 'is_active'
    ]
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = [
        'level', 'name', 'points_required', 'cashback_bonus',
        'points_multiplier', 'daily_bonus_spins'
    ]
    ordering = ['level']
    
    def get_icon_display(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            obj.color,
            obj.icon
        )
    get_icon_display.short_description = 'Icône'


@admin.register(UserReward)
class UserRewardAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'current_level', 'points_balance', 'lifetime_points',
        'spins_available', 'streak_days', 'receipts_today'
    ]
    list_filter = ['current_level', 'last_daily_spin']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['lifetime_points', 'total_spins_used']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'current_level')


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'amount', 'transaction_type', 'source',
        'balance_after', 'created_at'
    ]
    list_filter = ['transaction_type', 'source', 'created_at']
    search_fields = ['user__email', 'description']
    readonly_fields = ['transaction_id', 'balance_after', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'reward_type', 'points_cost', 'cash_value',
        'stock_quantity', 'times_redeemed', 'is_active', 'is_featured'
    ]
    list_filter = ['reward_type', 'is_active', 'is_featured', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['times_redeemed']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'slug', 'description', 'reward_type', 'category')
        }),
        ('Visuels', {
            'fields': ('image', 'icon', 'partner_name', 'partner_logo')
        }),
        ('Coût et valeur', {
            'fields': ('points_cost', 'cash_value')
        }),
        ('Stock et limites', {
            'fields': ('stock_quantity', 'limit_per_user', 'required_level')
        }),
        ('Disponibilité', {
            'fields': ('is_active', 'is_featured', 'available_from', 'available_until')
        }),
        ('Détails', {
            'fields': ('terms_conditions', 'delivery_info'),
            'classes': ('collapse',)
        })
    )


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = [
        'redemption_id', 'user', 'reward', 'points_spent',
        'status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'reward__reward_type']
    search_fields = ['redemption_id', 'user__email', 'reward__name']
    readonly_fields = ['redemption_id', 'created_at', 'processed_at', 'delivered_at']
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_processing', 'mark_as_completed', 'mark_as_delivered']
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
    mark_as_processing.short_description = "Marquer comme en traitement"
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', processed_at=timezone.now())
    mark_as_completed.short_description = "Marquer comme complété"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', delivered_at=timezone.now())
    mark_as_delivered.short_description = "Marquer comme livré"


class SpinWheelPrizeInline(admin.TabularInline):
    model = SpinWheelPrize
    extra = 1
    fields = [
        'name', 'prize_type', 'prize_value', 'probability',
        'color', 'icon', 'daily_limit', 'is_active'
    ]


@admin.register(SpinWheel)
class SpinWheelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'points_cost']
    inlines = [SpinWheelPrizeInline]


@admin.register(SpinHistory)
class SpinHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'wheel', 'prize', 'prize_value', 'spun_at']
    list_filter = ['wheel', 'spun_at']
    search_fields = ['user__email']
    date_hierarchy = 'spun_at'


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'challenge_type', 'target_type', 'target_value',
        'points_reward', 'is_active', 'is_featured', 'start_date', 'end_date'
    ]
    list_filter = ['challenge_type', 'target_type', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Informations', {
            'fields': ('name', 'slug', 'description', 'challenge_type')
        }),
        ('Objectif', {
            'fields': ('target_type', 'target_value', 'target_category')
        }),
        ('Récompenses', {
            'fields': ('points_reward', 'cashback_reward', 'bonus_spins')
        }),
        ('Période', {
            'fields': ('start_date', 'end_date')
        }),
        ('Affichage', {
            'fields': ('icon', 'color', 'is_active', 'is_featured')
        })
    )


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'challenge', 'progress', 'completed',
        'reward_claimed', 'started_at'
    ]
    list_filter = ['completed', 'reward_claimed', 'challenge__challenge_type']
    search_fields = ['user__email', 'challenge__name']
    readonly_fields = ['started_at', 'completed_at']
    
    actions = ['claim_rewards']
    
    def claim_rewards(self, request, queryset):
        count = 0
        for uc in queryset.filter(completed=True, reward_claimed=False):
            if uc.claim_reward():
                count += 1
        self.message_user(request, f"{count} récompenses réclamées")
    claim_rewards.short_description = "Réclamer les récompenses"


@admin.register(LevelUpNotification)
class LevelUpNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'old_level', 'new_level', 'seen', 'created_at']
    list_filter = ['seen', 'created_at']
    search_fields = ['user__email']
    date_hierarchy = 'created_at'