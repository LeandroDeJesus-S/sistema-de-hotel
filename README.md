# SISTEMA DE HOTEL

Site de hotel construído com Python e Django.

<img src="./readme/home.gif" type="gif" width=480 height=300>

O objetivo é disponibilizar um site de hotel onde os clientes possam realizar e agendar suas reservas de forma autônoma sem necessidade de interação com um gerente intermediador (Ex.: por whatsapp como vi em muitos casos).

<img src="./readme/acomodacoes.gif" type="gif" width=480 height=300>

O site é um projeto pessoal criado para fins de prática e para aplicar alguns conceitos novos para mim como o uso de fila de tarefas e a integração de sistemas de pagamentos.

<img src="./readme/quarto.gif" type="gif" width=480 height=300>

## Funcionamento
- O cliente pode reservar ou agendar um quarto por vez.
- É necessário estar logado para realizar uma reserva/agendamento.
- Ao preencher os dados é solicitado o pagamento e quando concluído é criada uma task que envia um PDF com os dados do pagamento por email ao cliente. Em caso de agendamentos também é criada uma task que ativa a reserva na data de checkin agendada e envia um aviso por email para o cliente e para os usuários administradores informando o início da reserva.
- As reservas ativas são automaticamente finalizadas na data do checkout e envia um aviso via email para o cliente e os adms

## Features
- Login personalizado por email ou username
- Uso de django axes para gerenciamento de acesso
- Uso de google reCAPTCHA v3
- Django Q para gerenciamento de fila de tarefas
- Sistema de pagamento com Stripe
- Realização e agendamento de reservas
- Geração de PDFs
- listagens de quartos e histórico de reservas
- Usuário pode gerenciar sua conta tendo ele a possibilidade de altera seus dados ou deletar sua conta.

## Rodando o projeto
1. clone este repositório
   ```powershell
   git clone https://github.com/LeandroDeJesus-S/sistema-de-hotel.git
   ```

2. entre na pasta do projeto
   ```powershell 
   cd sistema-de-hotel
   ```

3. crie um ambiente virtual
   ```powershell
   # python3 caso esteja no linux
   python -m venv venv
   ```
   ative o ambiente virtual
   ```powershell
   # windows powershell
   venv/Scripts/activate
   # linux
   source usr/bin/activate
   ```

4. com o ambiente ativo instale as dependências
   ```powershell
   # pip3 no linux
   pip install -r requirements.txt
   ```

5. crie um arquivo `.env` e preencha de acordo com o arquivo de exemplo `.env-exemplo`. Para gera sua `SECRET_KEY` execute o comando `python -c "from django.core.management.utils import get_random_secret_key;print(get_random_secret_key())"` copie o resultado e cole como valor no arquivo .env

6. antes de iniciar o servidor faça as migrações
   ```powershell
   python manage.py migrate
   ```

7. verifique se esta tudo ok
   ```powershell
   python manage.py check
   ```

8. execute o servidor
   ```powershell
   python manage.py runserver
   ```

OBS: Para criar um super usuário use o comando padrão (`python manage.py createsuperuser`) sem argumentos extras. Sera pedido os dados necessários para a criação do usuário.
