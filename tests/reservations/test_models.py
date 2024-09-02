from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from reservations.models import Class, Room, Benefit, Reservation
from clients.models import Client
from home.models import Hotel
from utils.supportmodels import (
    RoomErrorMessages,
    RoomRules,
    ReserveErrorMessages,
    ReserveRules,
    ClasseErrorMessages,
    BenefitErrorMessages
)
from django.core.exceptions import ValidationError
from PIL import Image
import tempfile
import os
from secrets import token_hex

class TestBenefit(TestCase):
    def setUp(self):
        self.valid_benefit = Benefit(
            name='beneficio',
            short_desc='descrição curta',
            icon='test/test_icon.png',
            displayable_on_homepage=False
        )
    
    def test_beneficio_criado_com_dados_validos(self):
        """valida se o beneficio é salvo no banco caso os
        dados sejam validos
        """
        self.valid_benefit.full_clean()
        self.valid_benefit.save()
        db_benefit = Benefit.objects.get(pk=1)
        self.assertEqual(db_benefit, self.valid_benefit)

    def test_icone_maiores_que_64x64_nao_passam_validacao(self):
        """imagem maior que 64x64 não passa na vaidação"""
        self.valid_benefit.icon = 'test/room_test.jpg'
        with self.assertRaisesMessage(ValidationError, BenefitErrorMessages.INVALID_ICON_SIZE):
            self.valid_benefit.full_clean()
    
    def test_se_name_nao_for_passado_levanta_validation_error(self):
        """levanta ValidationError se name não for passado"""
        self.valid_benefit.name = ''
        with self.assertRaises(ValidationError):
            self.valid_benefit.full_clean()
    
    def test_se_short_desc_nao_for_passado_levanta_validation_error(self):
        """levanta ValidationError se short_desc não for passado"""
        self.valid_benefit.short_desc = ''
        with self.assertRaises(ValidationError):
            self.valid_benefit.full_clean()
        

class TestClass(TestCase):
    def test_nome_da_classe_valido(self):
        """teste se classe é criada corretamente com nome
        valido
        """
        name = 'The best class'
        classe = Class(name=name)
        classe.full_clean()
        classe.save()

        db_class = Class.objects.get(pk=1)
        self.assertEqual(classe, db_class)
        
    def test_nome_da_classe_invalido(self):
        """teste se classe não é criada caso o nome seja invalido"""
        cases = [
            'class #1',
            'class-1',
            'class @2',
            ' ',
        ]

        for case in cases:
             with self.subTest(case=case):
                with self.assertRaisesMessage(ValidationError, ClasseErrorMessages.INVALID_NAME):
                        classe = Class(name=case)
                        classe.full_clean()


class BaseTestReservations(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        self.hotel = Hotel.objects.get(pk=1)


class TestRoom(BaseTestReservations):
    def setUp(self) -> None:
        super().setUp()
        self.valid_room = Room(
            id=1,
            room_class=Class.objects.first(),
            number='202A',
            adult_capacity= 1,
            child_capacity=0,
            size=25.5,
            daily_price=Decimal('100.00'),
            available=True,
            image='test/room_test.jpg',
            short_desc='desc test',
            long_desc=None,
            hotel=self.hotel
        )

        tmp_dir = tempfile.gettempdir()
        self.tmp_file = os.path.join(tmp_dir, f'{token_hex(8)}.jpg')
        img_path = 'media/test/room_test.jpg'
        self.tmp_img = Image.open(img_path)
    
    def tearDown(self) -> None:
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)
        
        self.tmp_img.close()
    
    def test_criado_com_dados_validos(self):
        """testa se o quarto é salvo corretamente na BD se
        os dados forem validos.
        """
        room = self.valid_room
        room.full_clean()
        room.save()
        room.benefit.add(Benefit.objects.first())

        saved_room = Room.objects.get(pk=1)
        self.assertEqual(saved_room, Room.objects.last())

    def test_numero_invalido(self):
        """testa se o quarto tiver um padrão de numero inválido
        levanta ValidationError
        """
        numbers = [
             'AAAA',
             'A123',
             '123a',
             '12AA',
             '12A'
        ]
        for num in numbers:
            with self.subTest(number=num):
                self.valid_room.number = num
                with self.assertRaises(ValidationError):
                    self.valid_room.full_clean()
    
    def test_adult_capacity_child_capacity_size_e_daily_price_com_valor_minimo_invalidos(self):
        """testa se adult_capacity, child_capacity, size e daily price levantam ValidationError
        caso o valor minimo seja invalido
        """
        cases = (
            (
                'adult_capacity', 
                RoomRules.MIN_ADULTS - 1, 
                RoomErrorMessages.ADULTS_INSUFFICIENT
            ),
            (
                'child_capacity', 
                RoomRules.MIN_CHILDREN - 1, 
                RoomErrorMessages.CHILD_INSUFFICIENT
            ),
            (
                'size', 
                RoomRules.MIN_SIZE - 1, 
                RoomErrorMessages.SIZE_INSUFFICIENT
            ),
            (
                'daily_price', 
                RoomRules.MIN_DAILY_PRICE - 1, 
                RoomErrorMessages.PRICE_INSUFFICIENT
            ),
        )
        for case_attr, case_attr_val, case_msg in cases:
            old = getattr(self.valid_room, case_attr)
            setattr(self.valid_room, case_attr, case_attr_val)
            with self.subTest(case_attr=case_attr, case_attr_value=case_attr_val):
                with self.assertRaisesMessage(ValidationError, case_msg):
                    self.valid_room.full_clean()
            
            setattr(self.valid_room, case_attr, old)
       
    def test_adult_capacity_child_capacity_daily_price_e_size_com_valor_maximo_invalidos(self):
        """testa se adult_capacity, child_capacity, daily_price e size levantam ValidationError
        caso o valor máximo seja invalido
        """
        cases = (
            (
                'adult_capacity', 
                RoomRules.MAX_ADULTS + 1, 
                RoomErrorMessages.ADULTS_EXCEEDED
            ),
            (
                'child_capacity', 
                RoomRules.MAX_CHILDREN + 1, 
                RoomErrorMessages.CHILD_EXCEEDED
            ),
            (
                'size', 
                RoomRules.MAX_SIZE + 1, 
                RoomErrorMessages.SIZE_EXCEEDED
            ),
            (
                'daily_price', 
                RoomRules.MAX_DAILY_PRICE + 1, 
                RoomErrorMessages.PRICE_EXCEEDED
            ),
        )
        for case_attr, case_attrv, case_msg in cases:
            old = getattr(self.valid_room, case_attr)
            setattr(self.valid_room, case_attr, case_attrv)
            with self.subTest(case_attr=case_attr, case_attr_value=case_attrv):
                with self.assertRaisesMessage(ValidationError, case_msg):
                    self.valid_room.full_clean()
            
            setattr(self.valid_room, case_attr, old)
       
    def test_imagem_redimensionada_apos_salvar(self):
        """testa se a imagem é redimensionada corretamente após
        salva
        """
        img_path = 'test/room_test.jpg'
        img = Image.open('media/' + img_path)
        img = img.resize((800,600))
        self.assertTupleEqual(img.size, (800, 600))
        img.close()

        self.valid_room.image = img_path
        self.valid_room.save()

        self.assertTupleEqual(
            (self.valid_room.image.width, self.valid_room.image.height),
            RoomRules.IMAGE_SIZE
        )

    def test_imagem_com_nome_invalido(self):
        """testa se levanta ValidationError com a msg correta
        caso seja passada um imagem com nome invalido
        """
        room = Room(
            id=1,
            room_class=Class.objects.first(),
            number='202A',
            adult_capacity= 1,
            child_capacity=0,
            size=25.5,
            daily_price=Decimal('100.00'),
            available=True,
            image='test/room_test_inv@lid#.jpg',
            short_desc='desc test',
            long_desc=None,
        )
        with self.assertRaisesMessage(ValidationError, RoomErrorMessages.IMAGE_INVALID_NAME):
            room.full_clean()
    
    def test_formatacao_do_preco_da_diaria(self):
        """testa se a função daily_price_formatted retorna a valor do quarto
        formatado corretamente.
        """
        result = self.valid_room.daily_price_formatted()
        expected = 'R$100.00'
        self.assertEqual(result, expected)
    
    def test_daily_price_em_centavos(self):
        """testa se a property daily_price_in_cents retorna o valor
        do quarto em centavos corretamente.
        """
        result = self.valid_room.daily_price_in_cents
        expected = 100_00
        self.assertEqual(result, expected)
    
    def test_metodo_str_retorna_numero_e_classe(self):
        """testa se o método __str__ retorna o valor correto"""
        result = self.valid_room.__str__()
        expected = f'Nº{self.valid_room.number} {self.valid_room.room_class}'
        self.assertEqual(result, expected)
    
    # def test_resize_image_redimensiona_a_img_corretamente_passando_w_e_h_validos(self):
    #     """testa se redimensiona a imagem corretamente passa os args `w` e `h` esperados"""
    #     img = self.tmp_img.resize((800,600))
    #     img.save(self.tmp_file)

    #     Room.resize_image(self.tmp_file, 400, 300)
    #     img = Image.open(self.tmp_file)

    #     self.assertTupleEqual(img.size, (400, 300))
    
    # def test_resize_image_redimensiona_a_img_corretamente_passando_w_e_h_validos(self):
    #     """testa se redimensiona a imagem corretamente passa os args `w` e `h` esperados"""
    #     img = self.tmp_img.resize((800,600))
    #     img.save(self.tmp_file)

    #     Room.resize_image(self.tmp_file, 400, 300)
    #     img = Image.open(self.tmp_file)
    #     self.assertTupleEqual(img.size, (400, 300))
    
    # def test_resize_image_nao_altera_altura_da_img_caso_seja_menor_que_a_altura_original(self):
    #     """testa se a imagem não tem a altura alterada caso a altura original seja menor que a passada"""
    #     resized = self.tmp_img.resize((400,300))
    #     resized.save(self.tmp_file)

    #     Room.resize_image(self.tmp_file, 400, 400)
    #     img = Image.open(self.tmp_file)

    #     resized.close()
    #     img.close()

    #     self.assertTupleEqual(img.size, (400, 300))


class TestReserva(BaseTestReservations):
    def setUp(self) -> None:
        super().setUp()
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')

        self.cliente = Client.objects.get(pk=1)
        self.room = Room.objects.get(pk=1)

        checkin = datetime.now().date()
        self.checkout = (checkin + timedelta(days=ReserveRules.MAX_RESERVATION_DAYS))
        custo = (self.checkout - checkin).days * self.room.daily_price_in_cents / 100

        self.valid_data = {
            'client': self.cliente,
            'checkin': checkin,
            'checkout': self.checkout,
            'amount': f'{custo}',
            'observations': '*'*100,
            'room': self.room,
        }
        self.valid_reservation = Reservation(**self.valid_data)

    def test_checkin_para_ontem(self):
        """testa se levanta ValidationError com a mensagem correta
        quando é feita um reserva com data de check-in para um tempo
        passado"""
        self.valid_reservation.checkin = datetime.now().date() - timedelta(days=1)
        
        with self.assertRaisesMessage(ValidationError, ReserveErrorMessages.INVALID_CHECKIN_DATE):
            self.valid_reservation.full_clean()

    def test_checkin_data_antecipada_muito_longa(self):
        """levanta ValidationError se a data de check-in for antecipada
        para daqui a um tempo maior que o tempo valido determinado
        """
        self.valid_reservation.checkin = ReserveRules.checkin_anticipation_offset() + timedelta(days=1)
        self.valid_reservation.checkout = self.valid_reservation.checkin + timedelta(days=1)
        
        with self.assertRaisesMessage(ValidationError, ReserveErrorMessages.INVALID_CHECKIN_ANTICIPATION):
            self.valid_reservation.full_clean()

    def test_tempo_minimo_e_maximo_de_reserva_invalido(self):
        """testa se o tempo de duração minimo e máximo da reserva
        levantam ValidationError com a mensagem correta quando forem
        inválidos
        """
        data = [
            (
                'min', 
                self.valid_reservation.checkin
            ),
            (
                'max', 
                self.valid_reservation.checkin + timedelta(days=ReserveRules.MAX_RESERVATION_DAYS + 1)
            )
        ]
        
        for case, value in data:
            self.valid_reservation.checkout = value
            with self.subTest(case=case, value=value):
                with self.assertRaisesMessage(ValidationError, ReserveErrorMessages.INVALID_STAYED_DAYS):
                    self.valid_reservation.full_clean()

    def test_checkout_para_o_mesmo_dia(self):
        """testa se levanta ValidationError com msg correta se a data de check-in e
        checkout forem para o mesmo dia
        """
        self.valid_reservation.checkout = self.valid_reservation.checkin
        with self.assertRaisesMessage(ValidationError, ReserveErrorMessages.INVALID_STAYED_DAYS):
            self.valid_reservation.full_clean()

    def test_reservar_quarto_nao_disponivel_levanta_excessao(self):
        """testa se levanta validation error com msg correta se um quarto
        não disponivel for passado para a reserva
        """
        self.valid_reservation.room.available = False
        with self.assertRaisesMessage(ValidationError, ReserveErrorMessages.UNAVAILABLE_ROOM):
            self.valid_reservation.full_clean()

    def test_calculo_do_valor_total_da_reserva(self):
        """testa se o valor da reserva esta sendo calculado corretamente"""
        self.valid_reservation.checkout = self.valid_reservation.checkin + timedelta(days=2)
        self.valid_reservation.room.daily_price = Decimal('100')

        result = self.valid_reservation.calc_reservation_value()
        expected = Decimal('200')
        
        self.assertEqual(result, expected)
    
    def test_valor_minimo_do_total_da_reserva(self):
        """testa se o valor minimo da reserva levanta validation error se form menor
        que o valor permitido"""
        self.valid_reservation.amount = Decimal(str(RoomRules.MIN_DAILY_PRICE - 1))
        with self.assertRaises(ValidationError):
            self.valid_reservation.full_clean()

    def test_formatted_price(self):
        """testa se a property formatted_price retorna o valor total da reserva
        formatado corretamente
        """
        self.valid_reservation.amount = Decimal('100')
        
        result = self.valid_reservation.formatted_price()
        expected = 'R$100.00'
        self.assertEqual(result, expected)

    def test_formatted_price_com_custo_nao_atribuido(self):
        """formatted_price levanta AttributeError com mensagem correta
        caso o valor da reserva ainda não tenha sido persistido.
        """
        self.valid_reservation.amount = None
        
        with self.assertRaisesMessage(AttributeError, 'Custo não foi persistido.'):
            self.valid_reservation.formatted_price()

    def test_reservation_days(self):
        """property reservation_days retorna a quantidade de dias levados pela reserva
        corretamente
        """
        days = 4
        self.valid_reservation.checkout = self.valid_reservation.checkin + timedelta(days=days)
        self.assertEqual(self.valid_reservation.reservation_days, days)

    def test_coast_in_cents(self):
        """testa se coast_in_cents retorna o valor da reserva em centavos corretamente"""
        self.valid_reservation.amount = Decimal('200')
        result = self.valid_reservation.coast_in_cents
        expected = 200_00
        self.assertEqual(result, expected)
    
    def test_status_default_e_iniciado(self):
        """testa se o valor inicial da reserva quando criado pela primeira
        vez é `I` de iniciado
        """
        self.valid_reservation.save()
        result = self.valid_reservation.status
        expected = 'I'
        self.assertEqual(result, expected)
    
    def test_reserva_inicia_desativada(self):
        """testa se quando a reserva é iniciada ela inicia desativada"""
        self.valid_reservation.save()
        self.assertFalse(self.valid_reservation.active)

    def test_reserva_para_data_que_sobrepoe_uma_reserva_ativa_nao_e_criada(self):
        """testa se levanta ValidationError se um reserva para uma data que sobrepõe
        uma reserva ativa para o mesmo quarto for criada
        """
        self.valid_reservation.active = True
        self.valid_reservation.status = 'A'
        self.valid_reservation.save()

        reservation = Reservation(
            checkin=self.valid_reservation.checkin,
            checkout=datetime.now().date() + timedelta(days=5),
            client=Client.objects.get(pk=2),
            room=self.room
        )
        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_availale_dates_retorna_datas_disponiveis(self):
        """testa se available_dates retorna as datas de disponibilidade
        para reserva de um quarto corretamente
        """
        self.valid_reservation.status = 'A'
        self.valid_reservation.active = True
        self.valid_reservation.save()

        self.valid_data['checkin'] = self.valid_data['checkout'] + timedelta(days=2)
        self.valid_data['checkout'] = self.valid_data['checkin'] + timedelta(days=1)
        self.valid_data['status'] = 'S'
        reservation2 = Reservation(**self.valid_data)
        reservation2.save()

        date_1 = self.checkout.strftime('%d/%m/%Y')
        date_2 = (reservation2.checkin - timedelta(days=1)).strftime('%d/%m/%Y')
        date_3 = reservation2.checkout.strftime('%d/%m/%Y')

        expected = f"{date_1} a {date_2}, e {date_3} para frente."
        result = Reservation.available_dates(self.room)
        self.assertEqual(result, expected)
