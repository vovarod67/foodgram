from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )


class IsCurrentUserOrAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return view.action == 'retrieve' or request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return (
            view.action == 'retrieve'
            or obj == request.user
            or request.user.is_staff
        )
