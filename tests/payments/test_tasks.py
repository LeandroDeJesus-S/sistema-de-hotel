from django.test import TestCase
from django.core.management import call_command
from payments import tasks, models
from unittest.mock import patch

class TestTasks(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        call_command('loaddata', 'tests/fixtures/contato_fixture.json')
        call_command('loaddata', 'tests/fixtures/beneficio_fixture.json')
        call_command('loaddata', 'tests/fixtures/classe_fixture.json')
        call_command('loaddata', 'tests/fixtures/quarto_fixture.json')
        call_command('loaddata', 'tests/fixtures/cliente_fixture.json')
        call_command('loaddata', 'tests/fixtures/reserva_fixture.json')
        call_command('loaddata', 'tests/fixtures/pagamento_fixture.json')
    
        self.payment = models.Payment.objects.first()
    
    @patch('payments.tasks.PaymentPDFHandler')
    def test_create_payment_pdf_cria_e_envia_pagamento_corretamente_com_pagamento_valido(self, pdf_handle):
        """testa se a task True caso seja enviado por email corretamente com um pagamento valido"""
        pdf_handle.handle.side_effect = 1

        result = tasks.create_payment_pdf(self.payment)
        self.assertTrue(result)
    
    @patch('payments.tasks.PaymentPDFHandler.handle')
    def test_create_payment_pdf_retorna_false_se_email_nao_enviado(self, pdf_handle):
        """testa se a task retorna False caso o email não seja enviado corretamente com um pagamento valido"""
        pdf_handle.return_value = 0

        result = tasks.create_payment_pdf(self.payment)
        self.assertFalse(result)
