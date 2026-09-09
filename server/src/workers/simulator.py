import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass, field

import aiomqtt 

from src.core.config import settings

logger = logging.getLogger("simulator")


@dataclass
class PIDController:
    """Discrete PID controller for pH neutralization via chemical dosing."""

    kp: float = 2.2
    ki: float = 0.35
    kd: float = 0.15
    setpoint: float = 7.0
    _integral: float = field(default=0.0, init=False)
    _prev_error: float = field(default=0.0, init=False)
    _output_min: float = 0.0
    _output_max: float = 15.0  # mL/s dosing pump ceiling

    def step(self, measured_value: float, dt: float) -> float:
        error = self.setpoint - measured_value

        self._integral += error * dt
        # Anti-windup: clamp accumulated integral so a long drift doesn't
        # cause a violent overshoot once the setpoint is reached.
        self._integral = max(min(self._integral, 50.0), -50.0)

        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(min(output, self._output_max), self._output_min)


@dataclass
class SimulatedDevice:
    device_id: str
    facility_id: str
    ph: float = 6.4  # start slightly acidic to give the PID loop work
    turbidity_ntu: float = 2.1
    pid: PIDController = field(default_factory=PIDController)

    def tick(self, dt: float) -> dict:
        dose_ml = self.pid.step(self.ph, dt)

        # Physical model: dosing nudges pH toward neutral, with sensor noise
        # and slow random turbidity drift to mimic real intake variability.
        self.ph += (dose_ml * 0.01) + random.uniform(-0.03, 0.03)
        self.ph = max(min(self.ph, 9.5), 4.5)

        self.turbidity_ntu += random.uniform(-0.15, 0.15)
        self.turbidity_ntu = max(min(self.turbidity_ntu, 12.0), 0.1)

        return {
            "device_id": self.device_id,
            "facility_id": self.facility_id,
            "timestamp": time.time(),
            "metrics": {
                "ph": round(self.ph, 3),
                "turbidity_ntu": round(self.turbidity_ntu, 3),
                "chlorine_dose_ml": round(dose_ml, 3),
            },
        }


async def run_simulator(
    devices: list[SimulatedDevice], interval_s: float = 2.0
) -> None:
    """
    Publishes continuous synthetic telemetry to MQTT for each simulated
    device. Runs indefinitely as a backend startup task — telemetry starts
    flowing to the UI within one interval of boot.
    """
    dt = interval_s
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST, port=settings.MQTT_PORT
            ) as client:
                logger.info("Simulator connected to MQTT broker")
                while True:
                    for device in devices:
                        payload = device.tick(dt)
                        topic = f"telemetry/{device.facility_id}/{device.device_id}"
                        await client.publish(topic, json.dumps(payload), qos=1)
                    await asyncio.sleep(interval_s)
        except aiomqtt.MqttError as exc:
            logger.warning(f"MQTT connection lost ({exc}); retrying in 3s")
            await asyncio.sleep(3)


def default_fleet() -> list[SimulatedDevice]:
    """Seed a small demo fleet so the dashboard has data immediately on boot."""
    return [
        SimulatedDevice(device_id="dev-ph-01", facility_id="facility-demo-01"),
        SimulatedDevice(device_id="dev-ph-02", facility_id="facility-demo-01"),
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_simulator(default_fleet()))
