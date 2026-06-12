class MPU6050Sensor:
    def __init__(self, i2c, address=0x68):
        self.sensor = None
        self.last_error = None

        try:
            import adafruit_mpu6050
            self.sensor = adafruit_mpu6050.MPU6050(i2c, address=address)
        except Exception as e:
            self.last_error = str(e)

    def read(self):
        data = {
            "accel_x": None,
            "accel_y": None,
            "accel_z": None,
            "gyro_x": None,
            "gyro_y": None,
            "gyro_z": None,
            "status": False,
            "error": self.last_error,
        }

        if self.sensor is None:
            return data

        try:
            ax, ay, az = self.sensor.acceleration
            gx, gy, gz = self.sensor.gyro

            data.update({
                "accel_x": ax,
                "accel_y": ay,
                "accel_z": az,
                "gyro_x": gx,
                "gyro_y": gy,
                "gyro_z": gz,
                "status": True,
                "error": None,
            })
        except Exception as e:
            self.last_error = str(e)
            data["error"] = self.last_error

        return data
