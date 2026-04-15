from Enum.Pais import Pais

class Servidor:

    CAPACIDADE_TOTAL = 4096

    def __init__(self, nome: str, capacidade_atual: int, pais: Pais, status: bool = True):
        self.nome = nome
        self.capacidade_total = self.CAPACIDADE_TOTAL
        self.capacidade_atual = capacidade_atual
        self.pais = pais
        self.status = status