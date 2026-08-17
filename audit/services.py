def log_action(actor, scope, model_name, object_repr, action='create', details=''):
    from .models import AuditLog
    AuditLog.objects.create(
        actor=actor if (actor and getattr(actor, 'pk', None)) else None,
        scope=scope, action=action, model_name=model_name,
        object_repr=str(object_repr)[:255], details=details,
    )