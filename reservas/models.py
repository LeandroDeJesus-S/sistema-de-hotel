from decimal import Decimal
from django.db import models
from django.db.models import Q, F
from clientes.models import Cliente
from django.core.validators import FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from PIL import Image


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
    image = models.ImageField(
        'Imagem', 
        upload_to='media/%Y-%m', 
        validators=[
            FileExtensionValidator(['jpg', 'png'], 'Somete jpg ou png'),
            RegexValidator(r'^\w+\.(png|jpg)$')
        ],
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-disponivel']

    def __str__(self) -> str:
        return f'Nº{self.numero} {self.classe}'

    def daily_price_formatted(self):
        return f'R${self.preco_diaria:.2f}'
    
    daily_price_formatted.short_description = 'Preço da diária'
    
    @property
    def daily_price_in_cents(self) -> int:
        return int(self.preco_diaria * Decimal('100'))

    @staticmethod
    def resize_image(img_path, w, h=None):
        img = Image.open(img_path)
        original_w, original_h = img.size

        if original_h <= h: return
        if h is None: h = round(h * original_h / original_w)
        
        resized = img.resize((w, h), Image.Resampling.NEAREST)
        resized.save(img_path, optimize=True, quality=70)
        img.close()

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.resize_image(self.image.path, w=560, h=420)
    

class Reserva(models.Model):
    check_in = models.DateField(
        'Check-in',
        blank=False,
        null=False,
    )
    checkout = models.DateField(
        'Check-out', 
        blank=False, 
        null=False,
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
        on_delete=models.SET_NULL, 
        related_name='reservas', 
        related_query_name='reserva',
        null=True
    )
    quarto = models.ForeignKey(
        Quarto, 
        on_delete=models.SET_NULL, 
        related_name='quartos', 
        related_query_name='quarto',
        null=True,
        blank=True
    )
    observacoes = models.TextField(
        'Observações', 
        max_length=100, 
        blank=True,
        null=True,
    )
    custo =  models.DecimalField(
        'Valor da reserva', 
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True
    )
    data_reserva = models.DateTimeField(
        'Data de criação da reserva', 
        auto_now_add=True,
        null=False,
        blank=False,
    )
    STATUS_CHOICES = (
        ('i', 'iniciado'),
        ('p', 'processando'),
        ('f', 'finalizado'),
        ('c', 'cancelado')
    )
    status = models.CharField(
        'Status',
        max_length=1,
        choices=STATUS_CHOICES,
        unique=False,
        blank=False,
        null=False,
        default='p'
    )

    def __str__(self) -> str:
        if not hasattr(self, 'quarto') or self.quarto is None:
            return f'{self.__class__.__name__} {self.pk}'
        
        room = self.quarto
        client = self.cliente
        in_ = self.check_in
        out = self.checkout
        price = self.custo

        string = f'{self.pk} | {client} Quarto:{room} {in_}-{out}'
        if price is not None:
            string += f'| R${price:.2f}'
        return string
    
    def formatted_price(self):
        if self.custo:
            return f'R${self.custo:.2f}'
        raise AttributeError('Custo não foi persistido.')
    
    formatted_price.short_description = 'Valor da reserva'

    class Meta:
        ordering = ['-data_reserva']
        constraints = [
            models.CheckConstraint(
                check=Q(check_in__lte=F('checkout')), 
                name='chk_checkin_lt_checkout',
            ),
            models.CheckConstraint(
                check=Q(qtd_adultos__gte=1), 
                name='chk_qtd_adultos_gte_1',
            ),
            models.CheckConstraint(
                check=Q(qtd_criancas__gte=0), 
                name='chk_qtd_criancas_gte_0',
            ),
        ]
    
    def calc_reservation_value(self) -> int:
        """"calcula o valor da reserva atribuindo a model e retorna o valor 
        em centavos."""
        days = Decimal(str((self.checkout - self.check_in).days))
        value = self.quarto.preco_diaria * days
        return value
    
    def reserve(self, client, room=None):
        if not self.quarto and room:
            self.quarto = room
            self.quarto.disponivel = False

        if not self.cliente:
            self.cliente = client
        
        if self.custo is None:
            self.custo = self.calc_reservation_value()
    
    @property
    def coast_in_cents(self):
        return int(self.custo * Decimal('100'))

    @property
    def reservation_days(self) -> int:
        return (self.checkout - self.check_in).days
    
    def clean(self) -> None:
        super().clean()
        error_messages = {}

        if self.quarto and not self.quarto.disponivel:
            error_messages['quarto'] = 'Este quarto não esta disponível'

        if error_messages:
            raise ValidationError(error_messages)

