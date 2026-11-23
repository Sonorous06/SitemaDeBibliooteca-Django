from django.shortcuts import render
# Create your views here.

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from .models import Multa
from uuid import uuid4

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from cuentas.models import Usuario
from .forms import RegistrarPagoForm
from .models import Pago


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
@login_required
def multas_pendientes_view(request):
    """Permite al bibliotecario consultar las multas pendientes."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    multas = Multa.objects.filter(
        estado='PENDIENTE'
    ).select_related(
        'usuario',
        'prestamo__ejemplar__libro'
    ).order_by('fecha_generacion', 'pk')

    return render(
        request,
        'multas/multas_pendientes.html',
        {'multas': multas}
    )


@login_required
@require_http_methods(['GET', 'POST'])
def registrar_pago_view(request, multa_id):
    """Registra la liquidación de una multa en mostrador."""
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado.')
        return redirect('home')

    multa = get_object_or_404(Multa, pk=multa_id)
    form = RegistrarPagoForm(
        request.POST if request.method == 'POST' else None
    )

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Conservamos el orden de bloqueo usado en préstamos.
            Usuario.objects.select_for_update().get(
                pk=multa.usuario_id
            )
            multa = Multa.objects.select_for_update().get(
                pk=multa_id
            )

            if multa.estado != 'PENDIENTE':
                messages.error(
                    request,
                    'Esta multa ya no está pendiente de pago.'
                )
                return redirect('multas_pendientes')

            pagado = multa.pagos.aggregate(
                total=Sum('monto')
            )['total'] or Decimal('0.00')

            saldo = multa.monto - pagado

            if saldo <= 0:
                messages.error(
                    request,
                    'La multa ya tiene pagos que cubren su monto. '
                    'Revisa el registro.'
                )
                return redirect('multas_pendientes')

            pago = Pago.objects.create(
                multa=multa,
                monto=saldo,
                metodo=form.cleaned_data['metodo'],
                folio_recibo=f'PAGO-{uuid4().hex[:24]}',
                registrado_por=request.user,
            )

            multa.estado = 'PAGADA'
            multa.save(update_fields=['estado'])

        messages.success(
            request,
            f'Pago de ${pago.monto:.2f} MXN registrado. '
            f'Folio: {pago.folio_recibo}.'
        )
        return redirect('multas_pendientes')

    pagado = multa.pagos.aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')

    saldo = max(multa.monto - pagado, Decimal('0.00'))

    return render(
        request,
        'multas/registrar_pago.html',
        {
            'multa': multa,
            'form': form,
            'saldo': saldo,
        }
    )