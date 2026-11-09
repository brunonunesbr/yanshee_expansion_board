# Yanshee Expansion Board — Guia de uso e desenvolvimento (Rev. 1.0)

> **Estado:** os testes integrados de LED RGB, botões, OLED, BMP280 e MPU6500 foram executados com sucesso no Yanshee conforme relato do teste em hardware. Os conectores externos de loopback **não tiveram validação informada**. O VL53L0X está **fora do escopo**, pois não respondeu no endereço esperado durante o diagnóstico.
>
> **Compatibilidade-alvo:** Raspberry Pi interno do Yanshee, Python **3.5**, Linux antigo baseado em **Debian Stretch**, barramento **`/dev/i2c-1`**. A PCB é a **Yanshee Expansion Board Rev. 1.0**, TecnoBridge Robotics (esquemático datado de 24/07/2026).

Este documento serve tanto para uma pessoa instalar e utilizar a placa quanto para uma **IA assistente de programação** entender as restrições do hardware antes de gerar código. **As tabelas abaixo descrevem a placa testada, não um Raspberry Pi genérico.**

## 1. Arquivos do projeto

```text
yanshee-expansion-board/
├── README.md                         # Este guia e contrato de hardware para IA
├── requirements.txt                  # Dependencia Python externa obrigatoria
├── diagnostico_yanshee.py           # Script integrado de testes
└── hardware/
    ├── esquematico-yanshee-expansion-board-rev1.0.pdf
    └── pinout-yanshee.png
```

**Referências locais:** [Esquemático Rev. 1.0](hardware/esquematico-yanshee-expansion-board-rev1.0.pdf) e [Pinout do Yanshee](hardware/pinout-yanshee.png).

> O arquivo `diagnostico_yanshee.py` reproduz o script de teste já utilizado, com **uma correção de orientação para o jumper do teste SPI opcional**: U10 **pino 1 ↔ pino 2**. Os testes opcionais permanecem desabilitados por padrão.

## 2. Requisitos

### Hardware

- Robô **UBTECH Yanshee** com a **Yanshee Expansion Board Rev. 1.0** conectada corretamente ao cabeçalho de 40 pinos do Raspberry Pi.
- Acesso ao terminal Linux (ou ao IDE Python configurado para executar no próprio Raspberry Pi).
- Barramento I²C do Raspberry Pi habilitado.
- Módulos presentes na placa testada: **OLED I²C em `0x3C`**, **BMP280 em `0x76`** e **MPU6500 em `0x68`**.
- Para testar SPI, UART ou GPIO externo, **jumpers somente nas ligações especificadas e com o robô desligado**.
- Para medições elétricas, multímetro adequado. **Não conectar sinais de 5 V diretamente a GPIOs de 3,3 V.**

### Software

- **Python 3.5** no ambiente original testado; os exemplos devem evitar recursos de Python mais novo, como *f-strings*, `dataclasses`, `pathlib` obrigatório, `typing` moderno e operadores `:=`.
- `smbus2==0.6.1` — comunicação I²C, instalado com `pip`.
- `RPi.GPIO` — obrigatório para LED RGB e botões; **preferir pacote APT `python3-rpi.gpio`** no sistema antigo (foi observado `0.6.5`).
- `i2c-tools` — permite executar `i2cdetect`.
- `python3-spidev` — necessário **somente** para o teste SPI opcional.
- `python3-serial` (*pyserial*) — necessário **somente** para o teste UART opcional.
- `time`, `math`, `struct`: **biblioteca padrão**, não instalar via pip.

**Não instalar como requisito desta placa:** `board`, `adafruit-blinka`, `adafruit-circuitpython-*`, `numpy` ou `Pillow`. O código validado usa acesso direto aos registradores com `smbus2` e não exige essas bibliotecas. Evitar atualizar o Python ou o sistema do Yanshee apenas para acomodar drivers modernos.

### Conteúdo de `requirements.txt`

```text
smbus2==0.6.1
```

O `requirements.txt` **não enumera `RPi.GPIO`, `spidev` e `pyserial` como pacotes pip**, de propósito: nesse Raspberry Pi antigo, esses módulos são providos preferencialmente pelos pacotes APT listados acima. Isso evita tentativas de compilar versões de pip incompatíveis com Python 3.5. Dependências opcionais podem ser omitidas quando os testes correspondentes estiverem desabilitados.

## 3. Instalação no Yanshee

1. Acesse o terminal Linux **do Raspberry Pi do robô**. Não execute comandos de I²C/GPIO do Yanshee diretamente no Mac ou outro computador de desenvolvimento.
2. Confira o interpretador e a interface:

   ```bash
   python3 --version
   ls -l /dev/i2c-1
   ```

3. Se necessário, instale pacotes do sistema (não rode uma atualização geral do sistema):

   ```bash
   sudo apt install python3-rpi.gpio i2c-tools
   # Apenas se for usar os testes opcionais:
   sudo apt install python3-spidev python3-serial
   ```

   > Se o APT não encontrar repositórios por causa da idade do Debian Stretch, **não migre automaticamente o OS**. Verifique primeiro o que já está instalado com os comandos da etapa 5.

4. Na pasta que contém `requirements.txt`, instale o módulo Python com o mesmo interpretador usado para rodar o teste:

   ```bash
   python3 -m pip install --user -r requirements.txt
   ```

   O Yanshee testado conseguiu instalar `smbus2==0.6.1`. O índice `piwheels.org` apresentou avisos de SSL, mas o download pelo PyPI foi concluído. Se `pip` relatar pacote já instalado, não é necessário reinstalar.

5. Confirme os imports:

   ```bash
   python3 -c "from smbus2 import SMBus; print('smbus2 OK')"
   python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
   # Opcionais:
   python3 -c "import spidev; print('SPI OK')"
   python3 -c "import serial; print('UART OK')"
   ```

6. Verifique os endereços no barramento **1**:

   ```bash
   sudo i2cdetect -y 1
   ```

   No teste real foram vistos: **`0x3C`, `0x45`, `0x58`, `0x68` e `0x76`**. É esperado detectar **`0x3C` (OLED), `0x68` (MPU6500) e `0x76` (BMP280)** na placa testada. Os endereços `0x45` e `0x58` não foram identificados e **não devem receber comandos arbitrários**. O `0x29` (VL53L0X) **não apareceu**.

Se o IDE (por exemplo, IDLE) apresentar `ModuleNotFoundError`, execute nele `import sys; print(sys.executable)` e instale os pacotes no mesmo interpretador. **Não confundir `pip` de outro Python com `python3 -m pip` do robô.**

## 4. Como rodar o diagnóstico

Com o robô parado, sem uma rotina de movimentação simultânea:

```bash
python3 diagnostico_yanshee.py
```

A sequência padrão é:

1. **LED RGB:** acende vermelho, verde, azul, amarelo, ciano, magenta e branco, aproximadamente 1 segundo por cor.
2. **Botões:** aguarda até 15 segundos para pressionar **KEY1** e **KEY2**. O botão pressionado é lido como **nível baixo**.
3. **OLED:** envia padrões de **listras verticais** com inicialização **SSD1306 e SH1106**. A confirmação é **visual**, não uma identificação automática do controlador.
4. **BMP280:** valida o *chip ID* `0x58` e faz cinco leituras compensadas de **temperatura em °C e pressão em hPa**.
5. **MPU6500:** valida o `WHO_AM_I` `0x70` e faz cinco leituras de **aceleração (m/s²), giroscópio (°/s) e temperatura (°C)**.
6. **LED Status:** solicita conferir visualmente o indicador de alimentação da placa (não controlável por GPIO).
7. **Relatório:** mostra `OK`, `VISUAL`, `ATENCAO` ou `FALHA` conforme o teste.

**Interpretação:** `OK` significa que o programa conseguiu ler valores plausíveis, **não** uma certificação de precisão metrológica. `VISUAL` exige que o operador confirme LED ou display. O diagnóstico não controla os motores do Yanshee.

**Interfaces externas:** `TESTAR_GPIO_EXTERNO`, `TESTAR_SPI` e `TESTAR_UART` ficam `False`. Só altere para `True` após preparar os jumpers corretos, desligar o robô para conectá-los e garantir que nenhum serviço utiliza a interface. Esses testes opcionais **não foram confirmados como executados** no relato de validação da placa.

## 5. Pinagem: use BCM no Python, nunca os nomes diretamente

O esquemático e a imagem do Yanshee utilizam uma nomenclatura equivalente ao **WiringPi**. A biblioteca `RPi.GPIO`, neste projeto, é configurada com `GPIO.setmode(GPIO.BCM)`. **A numeração do nome `GPIO22` no esquemático não corresponde ao BCM22.**

| Função da PCB | Nome no esquemático (WiringPi) | BCM para Python | Pino físico de 40 vias |
|---|---:|---:|---:|
| LED RGB — vermelho | GPIO22 | **6** | 31 |
| LED RGB — verde | GPIO23 | **13** | 33 |
| LED RGB — azul | GPIO27 | **16** | 36 |
| KEY1 | GPIO21 | **5** | 29 |
| KEY2 | GPIO7 | **4** | 7 |
| U11 — GPIO0 | GPIO0 | **17** | 11 |
| U11 — GPIO26 | GPIO26 | **12** | 32 |
| I²C — SDA1 | SDA1 | **2** | 3 |
| I²C — SCL1 | SCL1 | **3** | 5 |
| UART — TXD | TXD | **14** | 8 |
| UART — RXD | RXD | **15** | 10 |
| SPI — MOSI | MOSI | **10** | 19 |
| SPI — MISO | MISO | **9** | 21 |
| SPI — SCLK | SCLK | **11** | 23 |
| SPI — CE0 | CE0 | **8** | 24 |

**Evitar conflitos com o Yanshee:** a documentação de pinagem do robô marca como ocupados **pinos físicos 3, 5, 12, 35, 38 e 40**; 3/5 são I²C, enquanto 12/35/38/40 estão relacionados ao áudio I²S. Não modificar nem reatribuir esses pinos, nem desabilitar serviços de áudio, sem entender o firmware e os processos do robô. Evitar também alterar pinos não previstos na expansão.

### LED RGB

- Tipo: **cátodo comum**, com resistores de **220 Ω** nas três cores.
- `GPIO.HIGH` **acende** a cor; `GPIO.LOW` **apaga**.
- Antes de usar os GPIOs, configurar `GPIO.setmode(GPIO.BCM)`.
- Ao encerrar, apagar as cores e usar `GPIO.cleanup([6, 13, 16])` para liberar somente os pinos manipulados.

### Botões

- KEY1: **BCM 5**; KEY2: **BCM 4**.
- Os dois fecham o contato com **GND** quando pressionados: usar entrada com `GPIO.PUD_UP`.
- Leitura `GPIO.LOW` = pressionado; `GPIO.HIGH` = solto.
- Fazer *debounce* (o script usa confirmação após cerca de 30 ms).

## 6. Barramento I²C e dispositivos efetivamente presentes

**Barramento:** `SMBus(1)` / `/dev/i2c-1`. Utilizar **3,3 V** nos conectores externos desta PCB. O barramento é compartilhado com outros circuitos do robô.

| Dispositivo | Referência na placa | Endereço I²C | Registrador de identificação | Valor observado | Situação |
|---|---|---|---|---|---|
| Display OLED 0,96" | U2 | `0x3C` | Não há ID universal consultado | — | Exibição visual funcionou |
| **BMP280**, não BME280 | U3 | `0x76` | `0xD0` | **`0x58`** | Temperatura e pressão testadas |
| **MPU6500**, não MPU6050 | U5 | `0x68` | `0x75` | **`0x70`** | ACC/GYRO/temperatura testados |
| VL53L0X | U4 | `0x29` esperado | — | Sem resposta | **Fora deste projeto** |
| Não identificado | Não mapeado | `0x45` | — | — | Não acessar sem investigação |
| Não identificado | Não mapeado | `0x58` | — | — | Não acessar sem investigação |

**Não confundir:** o **endereço I²C `0x58`** encontrado no scan é de um dispositivo ainda não identificado; o **chip ID `0x58`** é um valor lido **dentro do BMP280 no endereço `0x76`**. São coisas diferentes.

### BMP280 (U3)

- Sensores disponíveis: **temperatura (°C)** e **pressão atmosférica (hPa)**. **Não há leitura de umidade**, pois o chip detectado é BMP280.
- `0xD0`: identificação (`0x58`).
- `0x88`–`0x9F`: 24 bytes de parâmetros de calibração de fábrica.
- `0xF4`: registro de controle. O diagnóstico usa `0x27` temporariamente e restaura o valor anterior após o teste.
- `0xF7`–`0xFC`: dados brutos de pressão e temperatura (6 bytes). Os ADCs são de 20 bits, portanto não basta converter os bytes diretamente em °C/hPa.
- **Obrigatório usar compensação com calibração do fabricante**: referência funcional `bmp_compensar(cal, dados)` em [`diagnostico_yanshee.py`](diagnostico_yanshee.py).
- Um valor plausível não garante precisão: compare com referência se necessário. O aquecimento interno do robô pode afetar a temperatura.

### MPU6500 (U5)

- Sensores disponíveis: **acelerômetro 3 eixos**, **giroscópio 3 eixos** e **temperatura interna**.
- `0x75`: `WHO_AM_I` (`0x70`).
- `0x6B`: gerenciamento de energia (o script acorda o chip somente se necessário e restaura o estado anterior de suspensão quando aplicável).
- `0x1C`: escala do acelerômetro; `0x1B`: escala do giroscópio. **Ler as escalas configuradas**, não assumir uma escala fixa.
- `0x3B` em diante: bloco de 14 bytes — AX, AY, AZ, temperatura, GX, GY, GZ, em palavras *signed int16 big-endian*.
- Unidades adotadas pelo diagnóstico: **m/s²** (aceleração), **°/s** (velocidade angular) e **°C** (temperatura interna).
- Com o sensor estático, o módulo da aceleração tende a cerca de **9,81 m/s²**, dependendo da calibração e orientação. Giro tende a ficar próximo de zero, não exatamente zero.
- Exemplo funcional de leitura: `testar_mpu6500()` em [`diagnostico_yanshee.py`](diagnostico_yanshee.py). Em produção, refatore para retornar dados em vez de somente imprimir.

### OLED (U2)

- Endereço visto: `0x3C`; esperado **128 × 64 pixels** no teste de padrões de 8 páginas de 8 linhas.
- O teste funcional foi realizado via `smbus2`, **sem** `board`, `adafruit-blinka` ou driver SSD1306 moderno.
- Testou-se uma sequência de inicialização para **SSD1306** e outra para **SH1106**. **O teste visual funcionando não determina qual dos dois controladores está efetivamente montado.**
- Em modos de página, comandos I²C são enviados com byte de controle `0x00`; dados de pixels, com `0x40`.
- Para SH1106, o teste usa deslocamento de **2 colunas**. Para SSD1306, o deslocamento é **0**.
- Funções de referência: `oled_inicializar(bus, modelo)` e `oled_desenhar(bus, modelo, acender)` em `diagnostico_yanshee.py`.
- O teste mostra **listras**, não texto. Para desenhar textos, imagens ou gráficos, implementar um **framebuffer e fonte bitmap compatíveis com Python 3.5**, ou usar uma biblioteca que seja comprovadamente compatível com o sistema.
- Em produção, escolher e validar **um** controlador e evitar alternar inicializações a cada atualização do quadro.

### LED de status

O LED `LED1` da placa está em série com um resistor de **330 Ω** entre **3,3 V e GND**. Ele é somente um **indicador visual de alimentação**; não possui GPIO para controle por software.

## 7. Conectores de expansão (conforme o esquemático)

**A numeração abaixo é do próprio conector da PCB, não é a numeração física de 1 a 40 do Raspberry Pi.** Verifique serigrafia/orientação antes de conectar; nunca assuma a orientação apenas olhando o conector pelo lado oposto da placa.

| Conector | Interface | Pino 1 | Pino 2 | Pino 3 | Pino 4 |
|---|---|---|---|---|---|
| U6 | I²C | GND | 3,3 V | SDA1 | SCL1 |
| U7 | I²C | GND | 3,3 V | SDA1 | SCL1 |
| U8 | I²C | GND | 3,3 V | SDA1 | SCL1 |
| U9 | UART | GND | 3,3 V | TXD | RXD |
| U10 | SPI | MOSI | MISO | SCLK | CE0 |
| U11 | GPIO | GND | 3,3 V | GPIO0 (BCM17) | GPIO26 (BCM12) |

- **U6/U7/U8:** todos compartilham o mesmo SDA/SCL; endereços I²C de novos módulos não podem conflitar com `0x3C`, `0x68`, `0x76` ou outros dispositivos existentes. Não alimentar módulos que exijam 5 V pelo pino 3,3 V.
- **U9:** UART TTL do Raspberry Pi, **níveis de 3,3 V**, não RS-232 ±12 V. A porta `/dev/serial0` pode estar reservada pelo Yanshee; verificar serviços e console antes de usar.
- **U10:** SPI expõe MOSI/MISO/SCLK/CE0 e **não tem 3,3 V ou GND no conector U10**. Se conectar um periférico externo, providenciar GND comum e alimentação adequadas por outro conector, após checar requisitos elétricos.
- **U11:** GPIO extra `BCM17`/`BCM12` com 3,3 V e GND. As saídas não são tolerantes a 5 V.

### Testes opcionais de continuidade funcional

O script tem três flags inicialmente desabilitadas:

```python
TESTAR_GPIO_EXTERNO = False
TESTAR_SPI = False
TESTAR_UART = False
```

Para habilitar uma delas, alterar para `True` **somente depois de preparar o hardware, com a alimentação desligada**, e garantir que a interface não é usada por serviços do robô:

| Teste | Ligação temporária de loopback | Observação |
|---|---|---|
| GPIO U11 | **Pino 3 ↔ pino 4** (GPIO0 ↔ GPIO26 da PCB) | Programa alterna nível e confere leitura |
| SPI U10 | **Pino 1 ↔ pino 2** (**MOSI ↔ MISO**) | **Correção importante:** não unir pinos 2 e 3, pois pino 3 é SCLK |
| UART U9 | **Pino 3 ↔ pino 4** (TXD ↔ RXD) | Exige UART disponível e console serial desativado |

Esses testes **não validam** automaticamente os conectores de 3,3 V/GND, nem trilhas de todos os pinos. Para U6/U7/U8, testar individualmente com um dispositivo I²C conhecido e endereço não conflitante.

## 8. Exemplos mínimos para criar aplicações

Os exemplos são escritos para **Python 3.5** e preservam as convenções reais da expansão.

### 8.1 Piscar o LED vermelho

```python
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT, initial=GPIO.LOW)
try:
    for _ in range(3):
        GPIO.output(6, GPIO.HIGH)  # LED vermelho ligado
        time.sleep(0.5)
        GPIO.output(6, GPIO.LOW)
        time.sleep(0.5)
finally:
    GPIO.output(6, GPIO.LOW)
    GPIO.cleanup([6])
```

### 8.2 Ler KEY1

```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.IN, pull_up_down=GPIO.PUD_UP)
try:
    pressionado = (GPIO.input(5) == GPIO.LOW)
    print("KEY1 pressionado:", pressionado)
finally:
    GPIO.cleanup([5])
```

### 8.3 Verificar os IDs dos sensores sem alterar configuração

```python
from smbus2 import SMBus

with SMBus(1) as bus:
    bmp_id = bus.read_byte_data(0x76, 0xD0)
    mpu_id = bus.read_byte_data(0x68, 0x75)

print("BMP280:", hex(bmp_id))  # Esperado: 0x58
print("MPU6500:", hex(mpu_id))  # Esperado: 0x70
```

### 8.4 Consultar o MPU6500 sem reconfigurar as escalas

```python
from smbus2 import SMBus


def s16(msb, lsb):
    n = (msb << 8) | lsb
    return n - 65536 if n >= 32768 else n

with SMBus(1) as bus:
    if bus.read_byte_data(0x68, 0x75) != 0x70:
        raise RuntimeError("MPU6500 nao identificado")

    # Exemplo somente se o MPU ja estiver ativo.
    a = bus.read_byte_data(0x68, 0x1C)
    fator = [16384.0, 8192.0, 4096.0, 2048.0][(a >> 3) & 3]
    bloco = bus.read_i2c_block_data(0x68, 0x3B, 6)
    ax = s16(bloco[0], bloco[1]) / fator * 9.80665
    ay = s16(bloco[2], bloco[3]) / fator * 9.80665
    az = s16(bloco[4], bloco[5]) / fator * 9.80665

print("Aceleracao m/s2:", ax, ay, az)
```

> Se o MPU estiver suspenso, o exemplo somente de leitura não irá acordá-lo. Para isso, reutilizar a abordagem de `testar_mpu6500()`, incluindo restauração de estado e cautela com outros processos.

### 8.5 Reutilizar a compensação do BMP280

```python
import struct
from smbus2 import SMBus
from diagnostico_yanshee import bmp_compensar

with SMBus(1) as bus:
    if bus.read_byte_data(0x76, 0xD0) != 0x58:
        raise RuntimeError("BMP280 nao identificado")

    cal_bytes = bus.read_i2c_block_data(0x76, 0x88, 24)
    cal = struct.unpack("<HhhHhhhhhhhh", bytes(cal_bytes))
    anterior = bus.read_byte_data(0x76, 0xF4)

    try:
        bus.write_byte_data(0x76, 0xF4, 0x27)
        import time
        time.sleep(0.15)
        dados = bus.read_i2c_block_data(0x76, 0xF7, 6)
        temperatura, pressao = bmp_compensar(cal, dados)
    finally:
        bus.write_byte_data(0x76, 0xF4, anterior)

print("Temperatura C:", temperatura)
print("Pressao hPa:", pressao)
```

O ideal para **produção** é extrair `bmp_compensar()` para um módulo `drivers/bmp280.py` e transformar operações de leitura em funções que **retornam** dados, sem `print()` ou espera longa. Isso é uma recomendação de arquitetura, não um módulo já incluído no pacote.

## 9. Recomendações para uso contínuo (produção)

1. **Não executar o diagnóstico completo como serviço permanente**: ele pisca LEDs, espera botões e alterna a inicialização do OLED. Criar aplicações separadas para os componentes necessários.
2. **Não alterar o sistema do robô** (Python, SO, drivers, serviços de áudio/motores) para usar a placa; preservar o ambiente validado.
3. **Usar acesso controlado ao I²C**: preferir um processo proprietário para as leituras; se houver múltiplos processos, coordenar acesso a registradores e evitar alterações concorrentes de configuração. Abrir `SMBus(1)` com `with` e fechar a interface.
4. **Distinguir falha de dado real**: se `OSError` ocorrer, marcar medida indisponível; nunca reutilizar silenciosamente a leitura anterior como se fosse atual. Se necessário, inclua timestamp, *status* e mensagem de erro no registro.
5. **Não escrever em endereços não identificados**, particularmente `0x45` e `0x58`. Não desabilitar protocolos do robô para liberar pinos sem validação.
6. **Restaurar configurações sempre que possível**, em blocos `try/finally`, e chamar `GPIO.cleanup([...])` apenas para os GPIOs configurados pela própria aplicação.
7. **OLED**: inicializar uma vez, usar framebuffer eficiente e evitar redesenhar tudo continuamente. Escolher SSD1306 **ou** SH1106 após verificar o modelo do módulo.
8. **Requisitos elétricos**: todos os GPIOs são **3,3 V**; considerar corrente, *pull-up*, compartilhamento de alimentação, ruído, aterramento e endereço I²C ao acrescentar módulos.
9. **Controle de taxa**: leituras periódicas com intervalos adequados, *timeout* e logging; não fazer polling com loop infinito sem pausas.
10. **Validação em bancada**: desenvolver com robô estabilizado, sem movimentos; qualquer teste que possa acionar motores ou modificar pinos compartilhados precisa de revisão específica.

## 10. Solução de problemas

| Sintoma | Possível causa | Primeira verificação |
|---|---|---|
| `No module named 'board'` | Código usa Blinka/Adafruit, ausente no Python 3.5 | Reescrever para `smbus2`; não é requisito desta placa |
| `No module named 'smbus2'` | Instalado em outro interpretador ou ainda não instalado | `python3 -m pip install --user -r requirements.txt` |
| `No module named 'RPi'` | Ausência do pacote GPIO do SO | `sudo apt install python3-rpi.gpio` |
| Erros `SSLV3_ALERT_HANDSHAKE_FAILURE` no piwheels | Incompatibilidade TLS/repositório antigo | Conferir se PyPI foi usado e se houve `Successfully installed`; não ignorar falhas reais |
| `SyntaxError` em `f'...'` ao instalar dependências | Dependência atual exige Python mais novo | Manter versões conhecidas e evitar Blinka moderno |
| `FileNotFoundError: /dev/i2c-1` | I²C indisponível, desabilitado ou SO diferente | `ls /dev/i2c*`; revisar habilitação do I²C antes de alterar configurações |
| `Permission denied` ao abrir I²C | Usuário não tem permissão para o dispositivo | Conferir `ls -l /dev/i2c-1` e grupos de usuário |
| OLED `0x3C` aparece, mas tela preta | Controlador não inicializado ou modelo inadequado | Executar `testar_oled()`; conferir alimentação/pinagem |
| BMP280 retorna `0x58` em `0xD0` | **Correto:** ID de BMP280, não BME280 | Usar somente temperatura e pressão |
| MPU retorna `0x70` em `0x75` | **Correto:** ID compatível com MPU6500 | Usar driver/escala MPU6500 |
| `0x29` não aparece no scan | VL53L0X não respondeu | Fora do escopo deste script; investigar módulo/alimentação/XSHUT separadamente |
| SPI/UART falha | Interface ocupada, jumper incorreto ou interface desabilitada | Conferir pinagem desta documentação e serviços ativos |

## 11. Contrato para assistentes de IA que gerarem código

**Considere esta seção como instruções técnicas prioritárias ao gerar código para esta PCB.**

### Fatos fixos do ambiente

- Hardware: **Yanshee Expansion Board Rev. 1.0** no Raspberry Pi do Yanshee.
- Linguagem/runtime: **Python 3.5**, sintaxe compatível; usar `format()` no lugar de f-strings.
- I²C: **bus 1**, biblioteca **`smbus2==0.6.1`** (`from smbus2 import SMBus`).
- GPIO: **`RPi.GPIO` com `GPIO.setmode(GPIO.BCM)`**, não números WiringPi.
- RGB **cátodo comum ativo em HIGH**: R=**BCM6**, G=**BCM13**, B=**BCM16**.
- Botões **ativos em LOW com pull-up**: KEY1=**BCM5**, KEY2=**BCM4**.
- OLED **`0x3C`**, 128x64 em teste de padrões; controlador SSD1306 ou SH1106 **a confirmar**.
- **BMP280 `0x76`** (`ID 0x58`): temperatura e pressão; **não** gerar API para umidade.
- **MPU6500 `0x68`** (`WHO_AM_I 0x70`): ACC/GYRO/temperatura; **não** supor MPU6050.
- **VL53L0X não suportado neste pacote**; não simular distância nem reportar sensor funcional.
- **`0x45` e `0x58` são endereços desconhecidos no scan**; não inventar dispositivos.
- **Não reutilizar pinos I²S reservados do robô** (físicos 12,35,38,40), nem assumir que UART/SPI estão livres.
- **Somente sinais de 3,3 V** nos GPIOs; não usar nível lógico de 5 V.

### Ao criar um novo script

1. Informar quais componentes e pinos o código irá utilizar.
2. Usar imports existentes no Python 3.5 e dependências que possam ser instaladas no Yanshee.
3. Para sensores I²C, validar endereço e *chip ID* antes da leitura, quando disponível.
4. Para BMP280, utilizar calibração e compensação da fábrica (ver função `bmp_compensar` já testada).
5. Para MPU6500, ler escalas atuais dos registradores; converter ACC para m/s² e GYRO para °/s, explicitando as unidades.
6. Para OLED, reutilizar os comandos `0x00` e dados `0x40`; não afirmar suporte a textos/gráficos sem implementar seu desenho real.
7. Gerar funções com retorno estruturado (dicionário simples Python 3.5, por exemplo), tratamento de exceção e fechamento de recursos.
8. Se o hardware não responder, indicar **erro/indisponível**; nunca inventar ou manter como atual uma amostra antiga.
9. Não configurar GPIOs reservados, não assumir exclusividade de barramentos compartilhados e não fazer testes com motores automaticamente.
10. Se precisar de novo pacote, especificar versão compatível com Python 3.5 e separar dependências `pip` de pacotes APT.
11. Não alterar o arquivo de diagnóstico já validado sem explicar a mudança e preservar uma cópia testável.
12. Se faltar informação de hardware, declarar a limitação em vez de adivinhar pinagens, controladores ou endereços.

### Prompt sugerido ao reutilizar este repositório com uma IA

> Você está desenvolvendo para a **Yanshee Expansion Board Rev. 1.0**. Leia o `README.md`, o `diagnostico_yanshee.py` e o esquemático em `hardware/` antes de programar. Respeite Python 3.5, BCM, `smbus2`, os dispositivos identificados e os pinos reservados do Yanshee. Gere código compatível, sem Blinka e sem VL53L0X, trate falhas de I²C e preserve o estado do robô. Antes do código, diga quais GPIOs e endereços serão usados. Se houver divergência entre o esquema genérico e os IDs observados na placa montada, dê preferência ao hardware efetivamente identificado. Não invente valores de sensores.

## 12. Estado da validação

| Item | Evidência disponível | Limite |
|---|---|---|
| LED RGB | Teste de 7 cores executado e relatado como funcional | Validação visual do operador |
| KEY1 e KEY2 | Ambos detectados durante teste | Não caracteriza durabilidade do botão |
| OLED | Padrões apareceram após inicialização via `smbus2` | Controlador exato não identificado |
| BMP280 | ID `0x58` em `0x76`; teste integrado relatado como bem-sucedido | Não houve calibração externa/ensaio de precisão |
| MPU6500 | ID `0x70` em `0x68`; teste integrado relatado como bem-sucedido | Não houve calibração externa/ensaio de precisão |
| `0x45`, `0x58` I²C | Endereços apareceram no scan | Dispositivos não identificados |
| VL53L0X | Endereço esperado `0x29` ausente | Excluído do diagnóstico |
| U6–U11 | Mapeamento no esquemático | Loopbacks e conexões externas não confirmados como testados |

---

**Documentação de referência do projeto:** esquemático Rev. 1.0 e pinout Yanshee incluídos em `hardware/`. O programa integrado funciona como **exemplo de referência e teste**, mas aplicações de produção devem implementar somente os componentes que utilizam, sem rodar a sequência interativa de diagnóstico continuamente.
