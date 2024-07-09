from django.db import models
from django.db.models import Q, F
from clientes.models import Cliente


class Beneficio(models.Model):
    nome = models.CharField(
        'Nome', 
        max_length=45, 
        blank=False, 
        null=False, 
        unique=True
    )
    descricao_curta = models.CharField(
        'Descrição curta', 
        max_length=100, 
        blank=False, 
        null=False, 
        unique=True
    )

    class Meta:
        verbose_name = 'Benefício'

    def __str__(self) -> str:
        return self.nome


class Classe(models.Model):
    nome = models.CharField(
        'Classe', 
        max_length=15, 
        blank=False, 
        null=False, 
        unique=True
    )

    def __str__(self) -> str:
        return self.nome
    

class Quarto(models.Model):
    classe = models.ForeignKey(
        Classe,
        on_delete=models.DO_NOTHING,
        related_name='quartos',
        related_query_name='quarto'
    )
    numero = models.SmallIntegerField(
        'Número',
        blank=False,
        null=False,
    )
    capacidade = models.PositiveIntegerField(
        'Capacidade', 
        blank=False, 
        null=False, 
        default=1,
    )
    tamanho = models.FloatField(
        'Tamanho m²', 
        blank=False, 
        null=False
    )
    preco_diaria = models.DecimalField(
        'Diária', 
        max_digits=10, 
        decimal_places=5, 
        blank=False, 
        null=False
    )
    beneficio = models.ManyToManyField(
        Beneficio, 
        related_name='quartos', 
        related_query_name='quarto'
    )
    disponivel = models.BooleanField(
        'Disponível',
        blank=False,
        null=False,
        default=True
    )

    class Meta:
        ordering = ['-disponivel']

    def __str__(self) -> str:
        return f'Nº{self.numero} {self.classe}'

    @property
    def daily_price_formatted(self):
        return f'R${self.preco_diaria:.2f}'


class Reserva(models.Model):
    check_in = models.DateField(
        'Check-in', 
        auto_now=True, 
        blank=False,
        null=False
    )
    checkout = models.DateField(
        'Check-out', 
        blank=False, 
        null=False
    )
    qtd_adultos = models.PositiveIntegerField(
        'Qtd. Adultos', 
        blank=False,
        null=False,
        default=1,
    )
    qtd_criancas = models.PositiveIntegerField(
        'Qtd. Crianças',
        blank=False,
        null=False,
        default=1,
    )
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.DO_NOTHING, 
        related_name='reservas', 
        related_query_name='reserva'
    )
    quarto = models.ForeignKey(
        Quarto, 
        on_delete=models.DO_NOTHING, 
        related_name='quartos', 
        related_query_name='quarto'
    )
    observacoes = models.TextField(
        'Observações', 
        max_length=100, 
        blank=True
    )
    custo =  models.DecimalField(
        'Valor da reserva', 
        max_digits=10, 
        decimal_places=8,
        blank=True,
        null=True
    )
    data_reserva = models.DateTimeField(
        'Data de criação da reserva', 
        auto_now=True,
        null=False,
        blank=False,
    )

    def __str__(self) -> str:
        if not hasattr(self, 'quarto'):
            return f'{self.__class__.__name__} {self.pk}'
        
        room_class = self.quarto.classe
        room_num = self.quarto.numero
        client = self.cliente.complete_name 
        in_ = self.check_in
        out = self.checkout
        price = self.custo
        string = f'{client} Quarto: nº {room_num} classe {room_class} {in_}-{out} | R${price:.2f}'
        return string
    
    @property
    def formatted_price(self):
        return f'R${self.custo:.2f}'

    class Meta:
        ordering = ['-data_reserva']
        constraints = [
            models.CheckConstraint(
                check=Q(check_in__gte=F('checkout')), 
                name='chk_checkin_gte_checkout',
                violation_error_message='A data de Check-in é maior ou igual a de Check-out'
            ),
            models.CheckConstraint(
                check=Q(qtd_adultos__gte=1), 
                name='chk_qtd_adultos_gte_1',
                violation_error_message='Número de adultos inválido.'
            ),
            models.CheckConstraint(
                check=Q(qtd_criancas__gte=0), 
                name='chk_qtd_criancas_gte_0',
                violation_error_message='A quantidade de crianças não pode ser menor que 0.'
            ),
        ]
    
