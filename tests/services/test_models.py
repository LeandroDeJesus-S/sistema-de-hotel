from django.test import TestCase
from services.models import Service
from PIL import Image
from utils.supportmodels import ServicesRules
from django.core.management import call_command
from home.models import Hotel
from tempfile import gettempdir
import os


class TestService(TestCase):
    def setUp(self):
        call_command('loaddata', 'tests/fixtures/hotel_fixture.json')
        self.hotel = Hotel.objects.first()

    def test_imagem_e_redimensionada_apos_salvar(self):
        img = Image.open('media/test/room_test.jpg')
        tmp_img = img.resize((600, 600), resample=Image.Resampling.NEAREST)

        tmp_img_path = 'media/test/tmp_img.jpg'
        tmp_img.save(tmp_img_path)
        tmp_img_path = tmp_img_path.replace('media/', '')
        img.close()
        tmp_img.close()
        
        service = Service(name='service 1', presentation_text='presentation', logo=tmp_img_path, hotel=self.hotel)
        service.save()
        service.refresh_from_db()
        self.assertTupleEqual((service.logo.width, service.logo.height), ServicesRules.IMG_SIZE)
    
    def test_metodo_str_retorna_nome_do_servico(self):
        service = Service(name='service 1', presentation_text='presentation', logo="", hotel=self.hotel)
        result = service.__str__()
        expected = 'service 1'
        self.assertEqual(result, expected)
