import adafruit_dht
import board
import time

from config import DHT11_PIN


class DHT11Sensor:
    def __init__(self):
        self.sensor = None

        try:
            pin = getattr(board, f"D{DHT11_PIN}")
            self.sensor = adafruit_dht.DHT11(pin)
        except Exception as e:
            print(f"[DHT11] 초기화 실패: {e}")

    def read(self):
        """
        반환 예시
        {
            "temperature": 24.0,
            "humidity": 55.0
        }
        """

        if self.sensor is None:
            return None

        try:
            temperature = self.sensor.temperature
            humidity = self.sensor.humidity

            return {
                "temperature": temperature,
                "humidity": humidity
            }

        except Exception as e:
            print(f"[DHT11] 읽기 오류: {e}")
            return None
