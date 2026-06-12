class BH1750Sensor:
    def __init__(self, i2c, address=0x23):
        self.sensor = None
        self.last_error = None

        try:
            import adafruit_bh1750
            self.sensor = adafruit_bh1750.BH1750(i2c, address=address)
        except Exception as e:
            self.last_error = str(e)

    def read(self):
        data = {
            "lux": None,
            "status": False,
            "error": self.last_error,
        }

        if self.sensor is None:
            return data

        try:
            data.update({
                "lux": self.sensor.lux,
                "status": True,
                "error": None,
            })
        except Exception as e:
            self.last_error = str(e)
            data["error"] = self.last_error

        return data
