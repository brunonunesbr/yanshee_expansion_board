
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YAN SHEE EXPANSION BOARD - REV 1.0
Diagnostico de hardware
Compativel com Python 3.5

Dependencias:
    smbus2
    RPi.GPIO

Sensores:
    BMP280  - I2C 0x76
    MPU6500 - I2C 0x68
    OLED    - I2C 0x3C

VL53L0X excluido.
"""

from __future__ import print_function

import time
import math
import struct

from smbus2 import SMBus
import RPi.GPIO as GPIO


# ==================================================
# CONFIGURACOES
# ==================================================

I2C_BUS = 1

OLED_ADDR = 0x3C
BMP_ADDR = 0x76
MPU_ADDR = 0x68

# Mapeamento BCM, convertido do esquema WiringPi
LED_R = 6
LED_G = 13
LED_B = 16

KEY1 = 5
KEY2 = 4

# Conector externo U11
GPIO_TEST_OUT = 17
GPIO_TEST_IN = 12

# Ativar SOMENTE com jumpers preparados
TESTAR_GPIO_EXTERNO = False
TESTAR_SPI = False
TESTAR_UART = False

resultados = []


# ==================================================
# FUNCOES GERAIS
# ==================================================

def titulo(nome):
    print("\n" + "=" * 55)
    print(nome)
    print("=" * 55)


def executar(nome, funcao):
    titulo(nome)

    try:
        estado, descricao = funcao()

    except Exception as erro:
        estado = "FALHA"
        descricao = "{}: {}".format(
            type(erro).__name__, erro
        )

    resultados.append((nome, estado, descricao))
    print("[{}] {}".format(estado, descricao))


def assinado16(alto, baixo):
    valor = (alto << 8) | baixo

    if valor >= 32768:
        valor -= 65536

    return valor


# ==================================================
# TESTE 1 - LED RGB
# ==================================================

def testar_rgb():
    GPIO.setmode(GPIO.BCM)

    pinos = [LED_R, LED_G, LED_B]

    for pino in pinos:
        GPIO.setup(
            pino,
            GPIO.OUT,
            initial=GPIO.LOW
        )

    cores = [
        ("VERMELHO", (1, 0, 0)),
        ("VERDE",    (0, 1, 0)),
        ("AZUL",     (0, 0, 1)),
        ("AMARELO",  (1, 1, 0)),
        ("CIANO",    (0, 1, 1)),
        ("MAGENTA",  (1, 0, 1)),
        ("BRANCO",   (1, 1, 1))
    ]

    try:
        for nome, valores in cores:
            print("Acendendo:", nome)

            for pino, valor in zip(pinos, valores):
                GPIO.output(pino, valor)

            time.sleep(1)

    finally:
        for pino in pinos:
            GPIO.output(pino, GPIO.LOW)

        GPIO.cleanup(pinos)

    return "VISUAL", "Confira as sete cores do LED RGB"


# ==================================================
# TESTE 2 - BOTOES
# ==================================================

def testar_botoes():
    GPIO.setmode(GPIO.BCM)

    botoes = {
        "KEY1": KEY1,
        "KEY2": KEY2
    }

    detectado = {
        "KEY1": False,
        "KEY2": False
    }

    for pino in botoes.values():
        GPIO.setup(
            pino,
            GPIO.IN,
            pull_up_down=GPIO.PUD_UP
        )

    anterior = {
        nome: GPIO.input(pino)
        for nome, pino in botoes.items()
    }

    print("Solte os botoes e pressione KEY1 e KEY2.")
    print("Tempo disponivel: 15 segundos.")

    try:
        fim = time.monotonic() + 15

        while time.monotonic() < fim:

            for nome, pino in botoes.items():
                atual = GPIO.input(pino)

                if (anterior[nome] == GPIO.HIGH
                        and atual == GPIO.LOW):

                    time.sleep(0.03)

                    if GPIO.input(pino) == GPIO.LOW:
                        detectado[nome] = True
                        print("{} pressionado!".format(nome))

                anterior[nome] = GPIO.input(pino)

            if all(detectado.values()):
                break

            time.sleep(0.02)

    finally:
        GPIO.cleanup(list(botoes.values()))

    if all(detectado.values()):
        return "OK", "KEY1 e KEY2 detectados"

    return "ATENCAO", "Nem todos os botoes foram detectados"


# ==================================================
# TESTE 3 - OLED
# ==================================================

def oled_comando(bus, comandos):
    for valor in comandos:
        bus.write_byte_data(
            OLED_ADDR, 0x00, valor
        )


def oled_inicializar(bus, modelo):
    comandos = [
        0xAE,
        0xD5, 0x80,
        0xA8, 0x3F,
        0xD3, 0x00,
        0x40
    ]

    if modelo == "SSD1306":
        comandos += [
            0x8D, 0x14,
            0x20, 0x02
        ]
    else:
        comandos += [
            0xAD, 0x8B
        ]

    comandos += [
        0xA1,
        0xC8,
        0xDA, 0x12,
        0x81, 0xCF,
        0xD9,
        0xF1 if modelo == "SSD1306" else 0x22,
        0xDB, 0x40,
        0xA4,
        0xA6,
        0xAF
    ]

    oled_comando(bus, comandos)
    time.sleep(0.2)


def oled_desenhar(bus, modelo, acender):
    deslocamento = 2 if modelo == "SH1106" else 0

    for pagina in range(8):

        oled_comando(bus, [
            0xB0 + pagina,
            deslocamento & 0x0F,
            0x10 | (deslocamento >> 4)
        ])

        for inicio in range(0, 128, 16):
            dados = []

            for i in range(16):
                coluna = inicio + i

                if acender and (coluna // 16) % 2 == 0:
                    dados.append(0xFF)
                else:
                    dados.append(0x00)

            bus.write_i2c_block_data(
                OLED_ADDR,
                0x40,
                dados
            )


def testar_oled():
    print("Testando OLED em 0x3C")

    with SMBus(I2C_BUS) as bus:

        for modelo in ["SSD1306", "SH1106"]:
            print("\nControlador:", modelo)

            oled_inicializar(bus, modelo)
            oled_desenhar(bus, modelo, True)

            print("Verifique as listras na tela.")
            time.sleep(4)

            oled_desenhar(bus, modelo, False)

    return "VISUAL", "Teste dos dois controladores enviado"


# ==================================================
# TESTE 4 - BMP280
# Temperatura e pressao com compensacao Bosch
# ==================================================

def bmp_compensar(cal, dados):
    (
        t1, t2, t3,
        p1, p2, p3, p4, p5,
        p6, p7, p8, p9
    ) = cal

    adc_p = (
        (dados[0] << 16) |
        (dados[1] << 8) |
        dados[2]
    ) >> 4

    adc_t = (
        (dados[3] << 16) |
        (dados[4] << 8) |
        dados[5]
    ) >> 4

    if adc_t == 0x80000 or adc_p == 0x80000:
        raise ValueError("Conversao BMP280 indisponivel")

    # Compensacao de temperatura
    v1 = (adc_t / 16384.0 - t1 / 1024.0) * t2

    v2 = (
        (adc_t / 131072.0 - t1 / 8192.0) ** 2
    ) * t3

    t_fine = v1 + v2
    temperatura = t_fine / 5120.0

    # Compensacao de pressao
    v1 = t_fine / 2.0 - 64000.0

    v2 = v1 * v1 * p6 / 32768.0
    v2 = v2 + v1 * p5 * 2.0
    v2 = v2 / 4.0 + p4 * 65536.0

    v1 = (
        p3 * v1 * v1 / 524288.0 +
        p2 * v1
    ) / 524288.0

    v1 = (1.0 + v1 / 32768.0) * p1

    if v1 == 0:
        raise ValueError("Calibracao de pressao invalida")

    pressao = 1048576.0 - adc_p
    pressao = (
        pressao - v2 / 4096.0
    ) * 6250.0 / v1

    v1 = p9 * pressao * pressao / 2147483648.0
    v2 = pressao * p8 / 32768.0

    pressao = pressao + (v1 + v2 + p7) / 16.0

    return temperatura, pressao / 100.0


def testar_bmp280():
    with SMBus(I2C_BUS) as bus:

        chip_id = bus.read_byte_data(BMP_ADDR, 0xD0)

        print("Endereco:", hex(BMP_ADDR))
        print("Chip ID:", hex(chip_id))

        if chip_id != 0x58:
            return "FALHA", "Chip ID diferente de BMP280"

        # Calibracao de fabrica: 24 bytes
        calib_bytes = bus.read_i2c_block_data(
            BMP_ADDR, 0x88, 24
        )

        cal = struct.unpack(
            "<HhhHhhhhhhhh",
            bytes(calib_bytes)
        )

        if cal[3] == 0:
            raise ValueError("Calibracao BMP280 invalida")

        controle_original = bus.read_byte_data(
            BMP_ADDR, 0xF4
        )

        leituras = []

        try:
            # Temperatura x1, pressao x1, modo normal
            bus.write_byte_data(
                BMP_ADDR, 0xF4, 0x27
            )

            time.sleep(0.15)

            for i in range(5):
                dados = bus.read_i2c_block_data(
                    BMP_ADDR, 0xF7, 6
                )

                temp, pressao = bmp_compensar(
                    cal, dados
                )

                leituras.append((temp, pressao))

                print(
                    "Leitura {} | {:.2f} C | {:.2f} hPa"
                    .format(i + 1, temp, pressao)
                )

                time.sleep(0.4)

        finally:
            # Restaurar modo anterior
            bus.write_byte_data(
                BMP_ADDR, 0xF4, controle_original
            )

    valido = all(
        math.isfinite(t) and math.isfinite(p)
        and -40 <= t <= 85
        and 300 <= p <= 1100
        for t, p in leituras
    )

    if valido:
        return "OK", "BMP280: temperatura e pressao lidas"

    return "ATENCAO", "Valores fora da faixa esperada"


# ==================================================
# TESTE 5 - MPU6500
# Acelerometro, giroscopio e temperatura
# ==================================================

def testar_mpu6500():
    with SMBus(I2C_BUS) as bus:

        chip_id = bus.read_byte_data(
            MPU_ADDR, 0x75
        )

        print("Endereco:", hex(MPU_ADDR))
        print("WHO_AM_I:", hex(chip_id))

        if chip_id != 0x70:
            return "FALHA", "Chip ID diferente de MPU6500"

        pwr_original = bus.read_byte_data(
            MPU_ADDR, 0x6B
        )

        alterou_pwr = bool(pwr_original & 0x40)

        try:
            # Acordar somente se estiver dormindo
            if alterou_pwr:
                bus.write_byte_data(
                    MPU_ADDR,
                    0x6B,
                    pwr_original & ~0x40
                )

                time.sleep(0.15)

            # Consultar escalas atuais do sensor
            config_acc = bus.read_byte_data(
                MPU_ADDR, 0x1C
            )

            config_gyro = bus.read_byte_data(
                MPU_ADDR, 0x1B
            )

            idx_acc = (config_acc >> 3) & 0x03
            idx_gyro = (config_gyro >> 3) & 0x03

            escalas_acc = [
                16384.0, 8192.0, 4096.0, 2048.0
            ]

            escalas_gyro = [
                131.0, 65.5, 32.8, 16.4
            ]

            escala_acc = escalas_acc[idx_acc]
            escala_gyro = escalas_gyro[idx_gyro]

            print("Escala ACC:", 2 * (2 ** idx_acc), "g")
            print("Escala GYRO:", 250 * (2 ** idx_gyro), "dps")
            print("\nLeituras:")

            validas = []

            for i in range(5):

                dados = bus.read_i2c_block_data(
                    MPU_ADDR, 0x3B, 14
                )

                ax = assinado16(dados[0], dados[1])
                ay = assinado16(dados[2], dados[3])
                az = assinado16(dados[4], dados[5])

                temp_raw = assinado16(
                    dados[6], dados[7]
                )

                gx = assinado16(dados[8], dados[9])
                gy = assinado16(dados[10], dados[11])
                gz = assinado16(dados[12], dados[13])

                # Aceleracao em m/s2
                ax = ax / escala_acc * 9.80665
                ay = ay / escala_acc * 9.80665
                az = az / escala_acc * 9.80665

                # Velocidade angular em graus/s
                gx = gx / escala_gyro
                gy = gy / escala_gyro
                gz = gz / escala_gyro

                temperatura = temp_raw / 333.87 + 21.0

                modulo_acc = math.sqrt(
                    ax * ax + ay * ay + az * az
                )

                print("\nAmostra:", i + 1)

                print(
                    "ACC X:{:.2f} Y:{:.2f} Z:{:.2f} m/s2"
                    .format(ax, ay, az)
                )

                print(
                    "GYRO X:{:.2f} Y:{:.2f} Z:{:.2f} graus/s"
                    .format(gx, gy, gz)
                )

                print(
                    "Temperatura: {:.2f} C"
                    .format(temperatura)
                )

                print(
                    "Modulo aceleracao: {:.2f} m/s2"
                    .format(modulo_acc)
                )

                validas.append(
                    math.isfinite(modulo_acc)
                    and math.isfinite(temperatura)
                    and 0.5 < modulo_acc < 160
                    and -40 <= temperatura <= 85
                )

                time.sleep(0.5)

        finally:
            if alterou_pwr:
                bus.write_byte_data(
                    MPU_ADDR, 0x6B, pwr_original
                )

    if all(validas):
        return "OK", "MPU6500 respondeu as 5 leituras"

    return "ATENCAO", "Verifique as leituras do MPU6500"


# ==================================================
# TESTE 6 - GPIO EXTERNO U11
# OPCIONAL - REQUER JUMPER
# ==================================================

def testar_gpio_externo():
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(
        GPIO_TEST_OUT,
        GPIO.OUT,
        initial=GPIO.LOW
    )

    GPIO.setup(
        GPIO_TEST_IN,
        GPIO.IN,
        pull_up_down=GPIO.PUD_DOWN
    )

    passou = True

    try:
        for nivel in [0, 1, 0, 1, 0, 1]:

            GPIO.output(GPIO_TEST_OUT, nivel)
            time.sleep(0.1)

            recebido = GPIO.input(GPIO_TEST_IN)

            print(
                "Enviado:", nivel,
                "Recebido:", recebido
            )

            if nivel != recebido:
                passou = False

    finally:
        GPIO.cleanup([
            GPIO_TEST_OUT,
            GPIO_TEST_IN
        ])

    if passou:
        return "OK", "GPIO externo funcionando"

    return "FALHA", "Loopback GPIO falhou"


# ==================================================
# TESTE 7 - SPI U10
# OPCIONAL - MOSI LIGADO AO MISO
# ==================================================

def testar_spi():
    import spidev

    spi = spidev.SpiDev()

    try:
        spi.open(0, 0)
        spi.max_speed_hz = 100000
        spi.mode = 0

        enviado = [0x55, 0xAA, 0x12, 0x34]
        recebido = spi.xfer2(enviado)

        print("Enviado:", enviado)
        print("Recebido:", recebido)

    finally:
        spi.close()

    if recebido == enviado:
        return "OK", "SPI loopback funcionando"

    return "FALHA", "SPI loopback falhou"


# ==================================================
# TESTE 8 - UART U9
# OPCIONAL - TXD LIGADO AO RXD
# ==================================================

def testar_uart():
    import serial

    dados = b"YANSH EE UART TEST"

    with serial.Serial(
        "/dev/serial0",
        baudrate=9600,
        timeout=2,
        write_timeout=2
    ) as porta:

        porta.reset_input_buffer()
        porta.write(dados)
        porta.flush()

        recebido = porta.read(len(dados))

    print("Enviado:", dados)
    print("Recebido:", recebido)

    if recebido == dados:
        return "OK", "UART loopback funcionando"

    return "FALHA", "UART loopback falhou"


# ==================================================
# CONFIRMACAO DE TESTES EXTERNOS
# ==================================================

def executar_opcional(nome, funcao, ligacao):
    titulo(nome + " - SEGURANCA")

    print("Ligacao necessaria:", ligacao)
    print("O jumper deve ser instalado com o robo desligado.")
    print("Execute somente se a interface estiver livre.")

    resposta = input(
        "Confirma a ligacao e a interface livre? Digite SIM: "
    )

    if resposta.strip().upper() == "SIM":
        executar(nome, funcao)
    else:
        resultados.append(
            (nome, "PULADO", "Sem confirmacao")
        )


# ==================================================
# RELATORIO FINAL
# ==================================================

def relatorio():
    titulo("RELATORIO FINAL - YANSHEE EXPANSION BOARD")

    for nome, estado, descricao in resultados:

        print(
            "{:<22} {:<10} {}"
            .format(nome, estado, descricao)
        )

    falhas = sum(
        1 for item in resultados
        if item[1] == "FALHA"
    )

    atencoes = sum(
        1 for item in resultados
        if item[1] == "ATENCAO"
    )

    visuais = sum(
        1 for item in resultados
        if item[1] == "VISUAL"
    )

    print("\nFalhas:", falhas)
    print("Atencoes:", atencoes)
    print("Verificacoes visuais:", visuais)

    print("\nDiagnostico encerrado.")
    print("VL53L0X nao foi testado.")


# ==================================================
# PROGRAMA PRINCIPAL
# ==================================================

def main():
    titulo("YANSH EE EXPANSION BOARD - DIAGNOSTICO")

    print("Revisao da PCB: 1.0")
    print("Python 3.5 - smbus2 - RPi.GPIO")
    print("Sensores confirmados: BMP280 / MPU6500")
    print("I2C: /dev/i2c-1")

    executar("LED RGB", testar_rgb)

    executar("KEY1 e KEY2", testar_botoes)

    executar("OLED", testar_oled)

    executar("BMP280", testar_bmp280)

    executar("MPU6500", testar_mpu6500)

    resultados.append((
        "LED Status",
        "VISUAL",
        "Confirmar LED de alimentacao aceso"
    ))

    if TESTAR_GPIO_EXTERNO:
        executar_opcional(
            "GPIO U11",
            testar_gpio_externo,
            "U11 pino 3 com pino 4"
        )

    if TESTAR_SPI:
        executar_opcional(
            "SPI U10",
            testar_spi,
            "U10 pino 2 com pino 3"
        )

    if TESTAR_UART:
        executar_opcional(
            "UART U9",
            testar_uart,
            "U9 pino 3 com pino 4"
        )

    relatorio()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usuario.")
