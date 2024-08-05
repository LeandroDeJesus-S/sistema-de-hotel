from datetime import date, datetime, timedelta
from functools import reduce

from django.core.exceptions import ValidationError
from django.test import TestCase

from clients.models import Client
from utils.supportmodels import ClientErrorMessages, ClientRules, ContactErrorMessages


class TestClient(TestCase):
    def setUp(self) -> None:
        self.login_data = {
            'username': 'DahyeLee123',
            'password': 'LeeDahyeCheer@123',
        }
        self.extra_data = {
            'first_name': 'Lee',
            'last_name': 'Dahye',
            'phone': '27988555333',
            'email': 'dahye@email.com',
            'birthdate': date(2002, 3, 2),
            'cpf': '90248488066'
        }
        self.base_client = Client(**self.login_data, **self.extra_data)
        self.other_client = self._new_variated_client(
            username='Aylin123',
            first_name='Aylin',
            phone='2798789798',
            email='alyin@email.com',
            cpf='48256848073',
        )
    
    def _new_variated_client(self, **mapping):
        """cria um novo usuario usando os dados base de setUp.login_data
        e setUp.extra_data.
        """
        self.login_data.update(self.extra_data)
        self.login_data.update(**mapping)

        client = Client(**self.login_data)
        return client

    def test_cliente_salvo_com_dados_validos(self):
        """testa se o usuário é salvo na base de dados se todos
        os dados enviados são validos.
        """
        self.base_client.full_clean()
        self.base_client.save()
        client = Client.objects.get(username='DahyeLee123')
        self.assertEqual(client.pk, self.base_client.pk)

    # username
    def _username_invalid_cases(self):
        """retorna uma lista de tuplas com casos invalidos de teste para o username
        no padrão (identificação, valor, messagem)
        """
        cases = [
            (
                'test_username_muito_curto',
                'a' * (ClientRules.USERNAME_MIN_SIZE - 1),
                ClientErrorMessages.INVALID_USERNAME_LEN
            ),
            (
                'test_username_muito_longo',
                'a' * (ClientRules.USERNAME_MAX_SIZE + 1),
                ClientErrorMessages.INVALID_USERNAME_LEN
            ),
            (
                'test_username_com_caracteres_invalidos',
                'Avd/d123#',
                ClientErrorMessages.INVALID_USERNAME_CHARS
            )
        ]
        return cases

    def test_username_com_caracteres_invalidos(self):
        """testa o nome de usuario para tamanho minimo, maximo e caracteres invalidos
        """
        for case_id, case_value, case_msg in self._username_invalid_cases():
            with self.subTest(case_id=case_id, case_value=case_value, case_msg=case_msg):
                self.base_client.username = case_value
                with self.assertRaisesMessage(ValidationError, case_msg):
                    self.base_client.full_clean()

    def test_username_duplicado_levanta_validation_error(self):
        """testa se o username levanta ValidationError ser for duplicado"""
        self.base_client.save()
        self.other_client.username = self.base_client.username
        with self.assertRaisesRegex(ValidationError, ClientErrorMessages.DUPLICATED_USERNAME):
            self.other_client.full_clean()
    
    def test_username_em_branco_levanta_validation_error(self):
        """testa se levanta ValidationError com a devida mensagem
        caso o username não seja passado
        """
        self.other_client.username = ''
        with self.assertRaisesMessage(ValidationError, ClientErrorMessages.NOT_PROVIDED_USERNAME):
            self.other_client.full_clean()

    # password
    def test_senha_alfanumericas_sem_simbolos_levantam_validation_error_com_mensagem_correta(self):
        """testa se password levanta ValidationError com a msg correta caso
        seja alfanumerica e não contenha simbolos.
        """
        cases = [
            '1234567', 
            'abcdefegguda', 
            '45648998464',
            'fdsjfsdfj7879878'
        ]
        for case in cases:
            with self.subTest(case=case):
                client = self._new_variated_client(password=case)
                with self.assertRaisesMessage(ValidationError, ClientErrorMessages.PASSWORD_WEAK):
                    client.full_clean()

    # first_name
    def _first_name_invalid_cases(self):
        """retorna uma lista de dicionarios de casos invalidos de
        first_name tamanho maximo, minimo e caracteres"""
        cases = [
            (
                'test_first_name_com_tamanho_maximo_invalido_levanta_validation_error',
                'a' * (ClientRules.MIN_FIRSTNAME_CHARS - 1),
                ClientErrorMessages.INVALID_FIRSTNAME_MIN_LENGTH
            ),
            (
                'test_first_name_com_tamanho_maximo_invalido_levanta_validation_error',
                'a' * (ClientRules.MAX_FIRSTNAME_CHARS + 1),
                ClientErrorMessages.INVALID_FIRSTNAME_MAX_LENGTH
            ),
            (
                'test_first_name_com_nao_apenas_letras_levanta_validation_error_com_messagem_correta',
                ['teste123', '12343', 'teste@', 'teste '],
                ClientErrorMessages.INVALID_FIRSTNAME_LETTERS
            )
        ]
        return cases

    def test_first_name_casos_invalidos_levanta_validation_error_com_mensagem_correta(self):
        """testa os casos invalidos de first_name como tamanho maximo, minimo e caracteres
        """
        for case_id, case_value, case_msg in self._first_name_invalid_cases():
            if not isinstance(case_value, list):
                self.base_client.first_name = case_value
                with self.subTest(case_id=case_id, case_value=case_value, case_msg=case_msg):
                    with self.assertRaisesMessage(ValidationError, case_msg):
                        self.base_client.full_clean()
                
                continue

            for value in case_value:
                self.base_client.first_name = value
                with self.subTest(case_id=case_id, case_value=value, case_msg=case_msg):
                    with self.assertRaisesMessage(ValidationError, case_msg):
                        self.base_client.full_clean()

    # last_name
    def _last_name_invalid_cases(self):
        """retorna lista de tuplas com casos invalidos de last_name
        como tamanho maximo, minimo e caracteres.
        """
        cases = [
            (
                'test_last_name_com_tamanho_maximo_invalido_levanta_validation_error',
                'a' * (ClientRules.MIN_SURNAME_CHARS - 1),
                ClientErrorMessages.INVALID_SURNAME_MIN_LENGTH
            ),
            (
                'test_last_name_com_tamanho_maximo_invalido_levanta_validation_error',
                'a' * (ClientRules.MAX_SURNAME_CHARS + 1),
                ClientErrorMessages.INVALID_SURNAME_MAX_LENGTH
            ),
            (
                'test_last_name_com_nao_apenas_letras_levanta_validation_error_com_messagem_correta',
                ['teste123', '12343', 'teste@', 'teste_teste'],
                ClientErrorMessages.INVALID_SURNAME_LETTERS
            )
        ]
        return cases

    def test_last_name_casos_invalidos_levanta_validation_error_com_mensagem_correta(self):
        """testa casos invalidos de last_name de self._last_name_invalid_cases
        """
        for case_id, case_value, case_msg in self._last_name_invalid_cases():
            if not isinstance(case_value, list):
                self.base_client.last_name = case_value
                with self.subTest(case_id=case_id, case_value=case_value, case_msg=case_msg):
                    with self.assertRaisesMessage(ValidationError, case_msg):
                        self.base_client.full_clean()
                
                continue

            for value in case_value:
                self.base_client.last_name = value
                with self.subTest(case_id=case_id, case_value=value, case_msg=case_msg):
                    with self.assertRaisesMessage(ValidationError, case_msg):
                        self.base_client.full_clean()

    def test_property_complete_name(self):
        """testa se a property complete_name retorna first_name + last_name
        separados por espaço
        """
        result = self.base_client.complete_name
        expected = f"{self.extra_data['first_name']} {self.extra_data['last_name']}"
        self.assertEqual(result, expected)

    # birthdate
    def _birthdate_invalid_cases(self):
        """retorna os casos de idade minima e maxia invalidos"""
        cases = [
            (
                'test_idade_minima_invalida',
                datetime.now().date() - timedelta(days=365 * (ClientRules.MIN_AGE - 1)),
                ClientErrorMessages.INVALID_BIRTHDATE
            ),
            (
                'test_idade_maxima_invalida',
                datetime.now().date() - timedelta(days=365 * (ClientRules.MAX_AGE + 1)),
                ClientErrorMessages.INVALID_BIRTHDATE
            )
        ]
        return cases
    
    def test_idade_casos_invalidos_levanta_value_error_com_msg_correta(self):
        """testa os casos de `_birthdate_invalid_cases` levantam ValidationError
        com a mensagem correta.
        """
        for case_id, case_value, case_msg in self._birthdate_invalid_cases():
            with self.subTest(case_id=case_id, case_value=case_value, case_msg=case_msg):
                client = self._new_variated_client(birthdate=case_value)
                with self.assertRaisesMessage(ValidationError, case_msg):
                    client.full_clean()

    def test_property_age_apartir_de_birthdate(self):
        """testa se a property age retorna a idade correta a partir
        da data de nascimento
        """
        result = self.base_client.age
        expected = datetime.now().year - self.extra_data['birthdate'].year
        self.assertEqual(result, expected)

    # email
    def test_email_mascarado(self):
        """testa se a property masked_email retorna o email
        com caracteres ofuscados corretamente
        """
        start, end = ClientRules.EMAIL_MASK_RANGE
        end = len(self.extra_data['email']) + end
        
        result = self.base_client.masked_email
        expected = reduce(
            lambda ini, i: ini + ('*' if start <= i[0] <= end else i[1]),
            enumerate(self.extra_data['email']),
            ''
        )

        self.assertEqual(result, expected)

    def test_email_invalido_levanta_validaton_error_com_msg_correta(self):
        """testa se emails com padrão invalido levantam ValidationError
        """
        invalid_emails = ['email.com', 'email', 'email@invalid']
        for email in invalid_emails:
            with self.subTest(email=email):
                self.base_client.email = email
                with self.assertRaisesMessage(ValidationError, ContactErrorMessages.INVALID_EMAIL):
                    self.base_client.full_clean()

    # phone
    def test_phone_formatado(self):
        """testa se a property formatted_phone retorna o telefone
        formatado no padrão (xx) xxxx-xxxx
        """
        phone = self.extra_data['phone']

        result = self.base_client.formatted_phone
        expected = f'({phone[:2]}) {phone[2:-4]}-{phone[-4:]}'

        self.assertEqual(result, expected)
    
    def test_phone_mascarado(self):
        """testa se a property masked_phone retorna o telefone
        com caracteres ofuscados corretamente
        """
        start, end = ClientRules.PHONE_MASK_RANGE
        end = len(self.extra_data['phone']) + end
        
        result = self.base_client.masked_phone
        mask = ['*' if start <= i <= end else n for i, n in enumerate(self.extra_data['phone'])]
        expected = ''.join(mask)

        self.assertEqual(result, expected)
    
    # cpf
    def test_com_cpf_sequencia(self):
        """testa se um cpf como sequencia levanta ValidationError com
        a mensagem correta
        """
        self.base_client.cpf = '1' * 11
        with self.assertRaisesMessage(ValidationError, ClientErrorMessages.INVALID_CPF):
            self.base_client.full_clean()
    
    def test_com_cpf_invalido(self):
        """testa se um cpf invalido que não é uma sequincia levanta ValidationError
        com a mensagem correta.
        """
        self.base_client.cpf = self.base_client.cpf[:-1] + '0'
        with self.assertRaisesMessage(ValidationError, ClientErrorMessages.INVALID_CPF):
            self.base_client.full_clean()

    def test_masked_cpf_retorna_cpf_com_digitos_ofuscados(self):
        """testa se a property masked_cpf retorna o cpf com
        os digitos ofuscados corretamente
        """
        start, end = ClientRules.CPF_MASK_RANGE
        end = len(self.extra_data['cpf']) + end
        
        result = self.base_client.masked_cpf
        mask = ['*' if start <= i <= end else n for i, n in enumerate(self.extra_data['cpf'])]
        expected = ''.join(mask)

        self.assertEqual(result, expected)

    def test_cpf_duplicado_levanta_validation_error_com_msg_correta(self):
        """testa se levanta ValidationError caso o cpf já exista"""
        self.base_client.save()
        
        self.other_client.cpf = self.base_client.cpf
        with self.assertRaisesMessage(ValidationError, ClientErrorMessages.DUPLICATED_CPF):
            self.other_client.full_clean()

    # custom methods
    def test_create_mask_levanta_value_error_se_parametro_end_for_positivo(self):
        """testa se o metodo _create_mask levanta ValueError caso o parametro
        end não seja negativo.
        """
        with self.assertRaisesMessage(ValueError, 'end must be a negative value'):
            Client._create_mask('0123456789', start=2, end=6)
    
    def test_create_mask_ofusca_digitos_corretamente(self):
        """testa se o metodo _create_mask esta criando as mascaras corretamente
        """
        value = '0123456789'
        masked = Client._create_mask(value, start=2, end=-3)
        masked_with_diff_char = Client._create_mask(value, start=2, end=-3, maskchar='-')

        result = [masked, masked_with_diff_char]
        expected = ['01******89', '01------89']
        
        self.assertListEqual(result, expected)
