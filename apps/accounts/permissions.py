# apps/accounts/permissions.py
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission personnalisée pour permettre aux propriétaires et admins
    de modifier un objet.
    """
    
    def has_object_permission(self, request, view, obj):
        # Lecture pour tous les utilisateurs authentifiés
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Écriture seulement pour le propriétaire ou admin
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_staff
        
        # Pour le modèle User
        return obj == request.user or request.user.is_staff


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission pour Admin et Manager seulement
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or
            request.user.groups.filter(name__in=['Admin', 'Manager']).exists()
        )


class HasObjectPermission(permissions.BasePermission):
    """
    Permission basée sur la méthode has_object_permission du modèle User
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Map des méthodes HTTP vers les actions
        action_map = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'edit',
            'PATCH': 'edit',
            'DELETE': 'delete'
        }
        
        action = action_map.get(request.method, 'view')
        return request.user.has_object_permission(obj, action)