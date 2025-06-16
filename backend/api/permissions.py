from rest_framework import permissions
from typing import Any


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(
            self,
            request: Any,
            view: Any
    ) -> bool:
        return(request.method in permissions.SAFE_METHODS
               or request.user.is_authenticated)
    
    def has_object_permission(
            self,
            request: Any,
            view: Any,
            obj: Any
    ) -> bool:
        return request.method in permissions.SAFE_METHODS or obj.author == request.user