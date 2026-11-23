from django.shortcuts import render
# Create your views here.

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .models import Multa


@login_required
def mis_multas_view(request):
    """Muestra únicamente las multas del usuario que inició sesión."""
    multas = Multa.objects.filter(
        usuario=request.user
    ).select_related(
        'prestamo__ejemplar__libro'
    ).order_by('-fecha_generacion', '-pk')

    total_pendiente = multas.filter(
        estado='PENDIENTE'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    return render(
        request,
        'multas/mis_multas.html',
        {
            'multas': multas,
            'total_pendiente': total_pendiente,
        }
    )
