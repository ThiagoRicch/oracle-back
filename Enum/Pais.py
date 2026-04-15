from Enum.Continentes import Continentes

class Pais:
    def __init__(self, nome: str, localizacoes: list):
        self.nome = nome
        self.localizacoes = localizacoes

PAISES = {
    Continentes.AMERICA_DO_SUL: [
        Pais('Brasil', localizacoes=[
         {"cidade": "São Paulo", "latitude": -23.5505, "longitude": -46.6333},
         {"cidade": "Rio de Janeiro", "latitude": -22.9068, "longitude": -43.1729}
     ]),
        Pais('Argentina', localizacoes=[
         {"cidade": "Buenos Aires", "latitude": -34.6037, "longitude": -58.3816},
         {"cidade": "Córdoba", "latitude": -31.4201, "longitude": -64.1888}
     ]),
        Pais('Colômbia', localizacoes=[
         {"cidade": "Bogotá", "latitude": 4.711, "longitude": -74.0721},
         {"cidade": "Medellín", "latitude": 6.2442, "longitude": -75.5812}
     ]),
        Pais('Peru', localizacoes=[
         {"cidade": "Lima", "latitude": -12.0464, "longitude": -77.0428},
         {"cidade": "Arequipa", "latitude": -16.409, "longitude": -71.5375}
     ]),
        Pais('Chile', localizacoes=[
         {"cidade": "Santiago", "latitude": -33.4489, "longitude": -70.6693},
         {"cidade": "Valparaíso", "latitude": -33.0472, "longitude": -71.6127}
     ])
    ],

    Continentes.AMERICA_DO_NORTE: [
        Pais('Estados Unidos', localizacoes=[
        {"cidade": "Nova York", "latitude": 40.7128, "longitude": -74.0060},
        {"cidade": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437}
     ]),
        Pais('Canadá', localizacoes=[
        {"cidade": "Toronto", "latitude": 43.65107, "longitude": -79.347015},
        {"cidade": "Vancouver", "latitude": 49.2827, "longitude": -123.1207}
     ]),
        Pais('México', localizacoes=[
        {"cidade": "Cidade do México", "latitude": 19.432608, "longitude": -99.133209},
        {"cidade": "Guadalajara", "latitude": 20.659698, "longitude": -103.349609}
     ])
    ],

    Continentes.AMERICA_CENTRAL: [
        Pais('Costa Rica', localizacoes=[
        {"cidade": "San José", "latitude": 9.748917, "longitude": -83.753428},
        {"cidade": "Limón", "latitude": 9.9905, "longitude": -83.0359}

     ]),
        Pais('Panamá', localizacoes=[
        {"cidade": "Cidade do Panamá", "latitude": 8.537981, "longitude": -80.782127},
        {"cidade": "Colón", "latitude": 9.3592, "longitude": -79.9011}
     ])
    ],

    Continentes.EUROPA: [
        Pais('Alemanha', localizacoes=[
        {"cidade": "Berlim", "latitude": 52.52, "longitude": 13.4050},
        {"cidade": "Munique", "latitude": 48.1351, "longitude": 11.5820}
     ]),
        Pais('França', localizacoes=[
        {"cidade": "Paris", "latitude": 48.8566, "longitude": 2.3522},
        {"cidade": "Lyon", "latitude": 45.7640, "longitude": 4.8357}
     ]),
        Pais('Reino Unido', localizacoes=[
        {"cidade": "Londres", "latitude": 51.5074, "longitude": -0.1278},
        {"cidade": "Manchester", "latitude": 53.4808, "longitude": -2.2426}
     ]),
        Pais('Itália', localizacoes=[
        {"cidade": "Roma", "latitude": 41.9028, "longitude": 12.4964},
        {"cidade": "Milão", "latitude": 45.4642, "longitude": 9.1900}
     ]),
        Pais('Espanha', localizacoes=[
        {"cidade": "Madri", "latitude": 40.4168, "longitude": -3.7038},
        {"cidade": "Barcelona", "latitude": 41.3851, "longitude": 2.1734}
     ]),
        Pais('Portugal', localizacoes=[
        {"cidade": "Lisboa", "latitude": 38.7169, "longitude": -9.1396},
        {"cidade": "Porto", "latitude": 41.1579, "longitude": -8.6291}
     ])
    ],

    Continentes.ASIA: [
        Pais('China',localizacoes=[
        {"cidade": "Pequim", "latitude": 39.9042, "longitude": 116.4074},
        {"cidade": "Xangai", "latitude": 31.2304, "longitude": 121.4737}
     ]),
        Pais('Índia', localizacoes=[
        {"cidade": "Nova Délhi", "latitude": 28.6139, "longitude": 77.2090},
        {"cidade": "Mumbai", "latitude": 19.0760, "longitude": 72.8777}
     ]),
        Pais('Japão', localizacoes=[
        {"cidade": "Tóquio", "latitude": 35.6895, "longitude": 139.6917},
        {"cidade": "Osaka", "latitude": 34.6937, "longitude": 135.5023}
     ])
    ],

    Continentes.AFRICA: [
        Pais('Nigéria', localizacoes=[
        {"cidade": "Abuja", "latitude": 9.081999, "longitude": 8.675277},
        {"cidade": "Lagos", "latitude": 6.5244, "longitude": 3.3792}
     ]),
        Pais('Egito', localizacoes=[
        {"cidade": "Cairo", "latitude": 30.0444, "longitude": 31.2357},
        {"cidade": "Alexandria", "latitude": 31.2001, "longitude": 29.9187}
     ]),
        Pais('África do Sul', localizacoes=[
        {"cidade": "Pretória", "latitude": -25.7479, "longitude": 28.2293},
        {"cidade": "Cidade do Cabo", "latitude": -33.9249, "longitude": 18.4241}
     ])
    ],

    Continentes.OCEANIA: [
        Pais('Austrália', localizacoes=[
        {"cidade": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
        {"cidade": "Melbourne", "latitude": -37.8136, "longitude": 144.9631}
     ]),
        Pais('Nova Zelândia', localizacoes=[
        {"cidade": "Auckland", "latitude": -36.8485, "longitude": 174.7633},
        {"cidade": "Wellington", "latitude": -41.2865, "longitude": 174.7762}
     ])
    ],
}