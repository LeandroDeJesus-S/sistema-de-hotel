from django.db import models


class Reserva(models.Model):
    nome = models.CharField('Nome', max_length=255)
    check_in = models.DateField('Check-in')
    checkout = models.DateField('Checkout')
    quantidade_de_adultos = models.PositiveIntegerField('Qtd. Adultos')
    quantidade_de_criancas = models.PositiveIntegerField('Qtd. Crianças')
    tipo_de_quarto = models.CharField('Tipo de quarto', max_length=2, choices=(
        ('B', 'Básico'),
        ('L', 'Luxo'),
        ('V', 'VIP'),
    ))
    telefone = models.CharField('Telefone', max_length=15)
    email = models.CharField('E-mail', max_length=155)
    observacoes = models.TextField('Observações', max_length=100)

    def __str__(self) -> str:
        return self.nome
