# def release_room(
#     reservation_pk, logger: logging.Logger = Provide[ReservationsContainer.logger]
# ):
#     """libera o quarto caso a reserva não tenha um pagamento finalizado"""
#     try:
#         reservation = Reservation.objects.get(pk=reservation_pk)
#         payment = Payment.objects.filter(reservation=reservation).first()
#         if payment is None or payment.status != Payment.Status.COMPLETED:
#             logger.info(
#                 f'room {reservation.room} of the reservation {reservation_pk} released'
#             )
#             room = Room.objects.get(pk=reservation.room.pk)
#             room.available = True
#             room.save()
#
#     except Reservation.DoesNotExist:
#         pass
