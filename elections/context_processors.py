def user_roles(request):
    """Expose user role helpers to templates: is_admin"""
    user = getattr(request, 'user', None)
    is_admin = False
    if user and user.is_authenticated:
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            is_admin = True
        else:
            try:
                is_admin = user.profile.role == 'admin'
            except Exception:
                is_admin = False
    return {'is_admin': is_admin}
