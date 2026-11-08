from django.db import connection 
from cuentas.models import Usuario 
with connection.schema_editor() as ed: 
    try: 
        ed.create_model(Usuario.groups.through) 
        print("✓ Tabla 'usuario_groups' creada correctamente.") 
    except Exception as e: print(f"Nota usuario_groups: {e}") 
    
    try: 
        ed.create_model(Usuario.user_permissions.through)
        print("✓ Tabla 'usuario_user_permissions' creada correctamente.") 
    except Exception as e:
        print(f"Nota usuario_user_permissions: {e}")