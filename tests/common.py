import math
import random
from datetime import datetime, timedelta

from app.models.sleep import SensorType, SleepData, SleepSample


def create_test_sleep_data(
    duration_hours=8, quality="good", sampling_rate=1  # 1 sample per second
):
    """Generate synthetic sleep data for testing."""
    samples = []
    now = datetime.now()
    start_time = now - timedelta(hours=duration_hours)

    # Total samples
    total_samples = int(duration_hours * 3600 * sampling_rate)

    # Generate accelerometer data
    for i in range(total_samples):
        timestamp = start_time + timedelta(seconds=i / sampling_rate)

        # Time progress as a fraction of total sleep duration
        i / total_samples

        # Create sleep cycle pattern (roughly 90 minutes per cycle)
        cycle_duration = 90 * 60  # 90 minutes in seconds
        cycle_progress = (i % (cycle_duration * sampling_rate)) / (
            cycle_duration * sampling_rate
        )

        # Determine which sleep stage we're simulating
        if quality == "good":
            # Good sleep has clear cycles and lower movement
            if (
                cycle_progress < 0.1
            ):  # Initial falling asleep or transitioning between cycles
                movement_intensity = 0.2 + 0.15 * random.random()  # Moderate movement
                70 + 10 * random.random()  # Slightly elevated HR
                is_awake = i < (20 * 60 * sampling_rate)  # Awake only in first 20 min
            elif cycle_progress < 0.4:  # Light sleep
                movement_intensity = 0.1 + 0.1 * random.random()
                65 + 8 * random.random()
                is_awake = False
            elif cycle_progress < 0.7:  # Deep sleep
                movement_intensity = 0.05 + 0.05 * random.random()  # Very low movement
                55 + 5 * random.random()  # Lower HR
                is_awake = False
            else:  # REM sleep
                movement_intensity = (
                    0.1 + 0.15 * random.random()
                )  # More variable movement
                65 + 15 * random.random()  # More variable HR
                is_awake = False

            # Add some brief awakenings
            if random.random() < 0.0002 and i > (
                60 * 60 * sampling_rate
            ):  # 0.02% chance after first hour
                is_awake = True
                movement_intensity = 0.3 + 0.2 * random.random()
                75 + 15 * random.random()

        elif quality == "poor":
            # Poor sleep has fragmented patterns and more movement
            if cycle_progress < 0.2:  # More time falling asleep or transitioning
                movement_intensity = 0.3 + 0.2 * random.random()
                75 + 15 * random.random()
                is_awake = (
                    i < (45 * 60 * sampling_rate) or random.random() < 0.3
                )  # Awake more often
            elif cycle_progress < 0.6:  # More light sleep, less deep
                movement_intensity = 0.15 + 0.15 * random.random()
                70 + 10 * random.random()
                is_awake = random.random() < 0.05  # Occasional awakening
            elif cycle_progress < 0.75:  # Less deep sleep
                movement_intensity = 0.1 + 0.1 * random.random()
                60 + 8 * random.random()
                is_awake = random.random() < 0.01  # Rare awakening during deep sleep
            else:  # REM sleep
                movement_intensity = 0.15 + 0.2 * random.random()
                70 + 15 * random.random()
                is_awake = random.random() < 0.1  # More likely to wake from REM

            # Add more frequent awakenings
            if random.random() < 0.001:  # 0.1% chance
                is_awake = True
                movement_intensity = 0.4 + 0.3 * random.random()
                80 + 15 * random.random()

        else:  # Default moderate quality
            if cycle_progress < 0.15:
                movement_intensity = 0.25 + 0.15 * random.random()
                72 + 10 * random.random()
                is_awake = i < (30 * 60 * sampling_rate)
            elif cycle_progress < 0.5:
                movement_intensity = 0.12 + 0.12 * random.random()
                68 + 8 * random.random()
                is_awake = False
            elif cycle_progress < 0.7:
                movement_intensity = 0.08 + 0.07 * random.random()
                58 + 7 * random.random()
                is_awake = False
            else:
                movement_intensity = 0.12 + 0.18 * random.random()
                68 + 12 * random.random()
                is_awake = False

            # Occasional awakening
            if random.random() < 0.0005:
                is_awake = True
                movement_intensity = 0.35 + 0.25 * random.random()
                78 + 12 * random.random()

        # Calculate accelerometer values
        # Base values (gravity is approximately 1g in normalized device values)
        if is_awake:
            # More movement when awake
            x = 0.3 * math.sin(i / 50) + movement_intensity * (random.random() - 0.5)
            y = 0.3 * math.cos(i / 70) + movement_intensity * (random.random() - 0.5)
            z = (
                0.9
                + 0.2 * math.sin(i / 100)
                + movement_intensity * (random.random() - 0.5)
            )
        else:
            # Less movement during sleep
            x = 0.1 * math.sin(i / 200) + movement_intensity * (random.random() - 0.5)
            y = 0.1 * math.cos(i / 250) + movement_intensity * (random.random() - 0.5)
            z = (
                0.95
                + 0.05 * math.sin(i / 300)
                + movement_intensity * (random.random() - 0.5)
            )

        # Add accelerometer sample
        if i % 5 == 0:  # Reduce sample frequency for readability
            acc_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.ACCELEROMETER,
                values={"x": x, "y": y, "z": z},
            )
            samples.append(acc_sample)

    # Create sleep data object
    sleep_data = SleepData(
        data_type="sleep_data",
        device_info={"device_id": "test_device"},
        sampling_rate_hz=sampling_rate,
        start_time=start_time,
        samples=samples,
    )

    return sleep_data
