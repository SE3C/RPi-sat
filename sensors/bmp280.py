import board
import busio
import adafruit_bmp280

from config import BMP280_I2C_ADDRESS


class BMP280Sensor:
    def __init__(self):
        self.sensor = None

        try:
            i2c = busio.I2C(board.SCL, board.SDA)

            self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(
                i2c,
                address=BMP280_I2C_ADDRESS
            )

            # 해수면 기압 기준값(hPa)
            self.sensor.sea_level_pressure = 1013.25

        except Exception as e:
            print(f"[BMP280] 초기화 실패: {e}")

    def read(self):
        """
        반환 예시
        {
            "temperature": 23.4,
            "pressure": 1008.7,
            "altitude": 35.2
        }
        """

        if self.sensor is None:
            return None

        try:
            return {
                "temperature": self.sensor.temperature,
                "pressure": self.sensor.pressure,
                "altitude": self.sensor.altitude
            }

        except Exception as e:
            print(f"[BMP280] 읽기 오류: {e}")
            return None
