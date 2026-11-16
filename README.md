# houses-back

## Deploy

O projeto provisiona o API Gateway, a Lambda Python 3.11, as permissões IAM e o
pacote ZIP da função via Terraform. O webhook usa o Twilio WhatsApp Sandbox e
o Groq para extrair os dados dos recibos. No Windows, o empacotamento usa
PowerShell e o comando `python` precisa apontar para uma instalação Python 3.11
ou compatível com as dependências da Lambda.

1. Configure as variáveis declaradas em `infra/variables.tf` em um arquivo local
   `terraform.tfvars` (não versionado), incluindo `groq_api_key`,
   `twilio_account_sid`, `twilio_auth_token` e as credenciais do Google Sheets.

2. Execute:

   ```powershell
   cd infra
   terraform init
   terraform apply
   ```

3. No Twilio Console, configure o Sandbox para enviar mensagens para a URL
   retornada no output `webhook_url`, usando o método `POST`.

Os testes unitários podem ser executados com:

```powershell
python -m unittest discover -s tests -v
```

## Teste local da Lambda

O arquivo [run_local.py](run_local.py) contém a configuração das variáveis de
ambiente e executa a Lambda usando o evento
[tests/local_event.json](tests/local_event.json). Preencha os valores na seção
`ENVIRONMENT` e execute:

```powershell
python run_local.py
```

O evento padrão simula uma mensagem de texto sem chamar Groq, Twilio ou Google
Sheets. O resultado esperado é `statusCode: 200` com uma resposta TwiML
contendo a orientação para enviar uma foto.
