from abc import ABC, abstractmethod


class AbstractWeatherManager(ABC):
    def __init__(self):
        self.weather_api = ""

    @abstractmethod
    async def get_weather():
        pass
