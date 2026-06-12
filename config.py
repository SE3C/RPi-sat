"""Shared configuration for the CubeSat software team.

All GPIO values use BCM numbering. This pin map is a temporary coding
baseline and must be rechecked during the real hardware wiring stage.
"""

I2C_SDA_PIN = 2
I2C_SCL_PIN = 3
I2C_BUS = 1

DHT11_DATA_PIN = 4
DHT11_GPIO_PIN = DHT11_DATA_PIN
DHT11_PIN = DHT11_DATA_PIN

GPS_UART_TX_PIN = 14
GPS_UART_RX_PIN = 15
GPS_PORT = "/dev/serial0"
GPS_BAUDRATE = 9600
GPS_TIMEOUT_SECONDS = 1.0

LED_PINS = {
    "red": 17,
    "green": 27,
    "yellow": 22,
    "blue": 23,
}

BUZZER_PIN = 24

BMP280_I2C_ADDRESS = 0x76
MPU6050_I2C_ADDRESS = 0x68
BH1750_I2C_ADDRESS = 0x23

SEA_LEVEL_PRESSURE_HPA = 1013.25
