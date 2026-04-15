from Repository.ServidorRepository import ServidorRepository
from Entity.Servidor import Servidor

class ServidorService:
    def __init__(self):
        self.repo = ServidorRepository()

    def listar(self):
        return self.repo.listar_servidores()

    def listar_por_id(self, servidor_id):
        return self.repo.listar_servidor_por_id(servidor_id)

    def criar(self, nome, pais, indice: int | None = None):
        CAPACIDADE_80PRCT = int(Servidor.CAPACIDADE_TOTAL * 0.8)

        existentes_nome = self.repo.buscar_servidor_por_nome(nome)
        if existentes_nome:
            return f"Já existe um servidor com o nome '{nome}'."

        servidores = self.repo.buscar_servidores_por_pais(pais)

        if indice is not None:
            if indice not in (0, 1):
                return "Indice de cidade invalido. Use 0 ou 1."

            # Frontend-selected city index should be respected directly.
            return self.repo.criar_servidor(nome, pais, indice=indice)

        if not servidores:
            return self.repo.criar_servidor(nome, pais, indice=0)
        
        if len(servidores) >= 2:
            return f"Limite de servidores atingido para {pais}."
        
        if servidores[0]["capacidade_atual"] < CAPACIDADE_80PRCT:
            return f"servidor em {pais} ainda não atingiu 80% de uso."
        return self.repo.criar_servidor(nome, pais, indice=1)

    def listar_servidores_por_continente(self, continente):
        return self.repo.buscar_servidores_por_continente(continente)

    def listar_servidores_por_pais(self, pais):
        return self.repo.buscar_servidores_por_pais(pais)

    def atualizar(self, servidor_id, **kwargs):
        novo_nome = kwargs.get('nome')
        if novo_nome and novo_nome.strip():
            existentes = self.repo.buscar_servidor_por_nome(novo_nome.strip())
            if existentes and all(str(s.get('id')) != str(servidor_id) for s in existentes):
                return f"Já existe um servidor com o nome '{novo_nome.strip()}'."
        return self.repo.atualizar_servidor(servidor_id, **kwargs)

    def ativar_desativar(self, servidor_id, status):
        return self.repo.ativar_desativar_servidor(servidor_id, status)

    def adicionar_capacidade(self, servidor_id, capacidade_a_adicionar):
        servidor = self.repo.listar_servidor_por_id(servidor_id)
        if not servidor:
            return None
        nova_capacidade = servidor["capacidade_atual"] + capacidade_a_adicionar

        if nova_capacidade > Servidor.CAPACIDADE_TOTAL:
            return(f"Capacidade excedida. Capacidade máxima: {Servidor.CAPACIDADE_TOTAL}")
            
        return self.repo.atualizar_servidor(servidor_id, capacidade_atual=nova_capacidade)

    def listar_arquivos(self, servidor_id):
        return self.repo.listar_arquivos_por_servidor(servidor_id)

    def adicionar_arquivo(self, servidor_id, titulo, descricao, tipo_arquivo, tamanho_gb):
        servidor = self.repo.listar_servidor_por_id(servidor_id)
        if not servidor:
            return "Servidor não encontrado."

        if tamanho_gb < 1 or tamanho_gb > 10:
            return "Tamanho do arquivo deve estar entre 1GB e 10GB."

        capacidade_atual = servidor.get("capacidade_atual", 0)
        capacidade_total = servidor.get("capacidade_total", Servidor.CAPACIDADE_TOTAL)
        nova_capacidade = capacidade_atual + tamanho_gb

        if nova_capacidade > capacidade_total:
            return f"Capacidade excedida. Máximo disponível: {capacidade_total - capacidade_atual}GB."

        arquivo = self.repo.adicionar_arquivo_servidor(
            servidor_id=servidor_id,
            titulo=titulo,
            descricao=descricao,
            tipo_arquivo=tipo_arquivo,
            tamanho_gb=tamanho_gb,
        )
        self.repo.atualizar_servidor(servidor_id, capacidade_atual=nova_capacidade)

        return {
            "arquivo": arquivo,
            "capacidade_atual": nova_capacidade,
            "capacidade_total": capacidade_total,
        }

    def atualizar_arquivo(self, servidor_id, arquivo_id, **kwargs):
        servidor = self.repo.listar_servidor_por_id(servidor_id)
        if not servidor:
            return "Servidor não encontrado."

        arquivo = self.repo.buscar_arquivo_por_id(arquivo_id)
        if not arquivo:
            return "Arquivo não encontrado."

        if str(arquivo.get("servidor_id")) != str(servidor_id):
            return "Arquivo não pertence a este servidor."

        capacidade_atual = servidor.get("capacidade_atual", 0)
        capacidade_total = servidor.get("capacidade_total", Servidor.CAPACIDADE_TOTAL)

        novo_tamanho = kwargs.get("tamanho_gb")
        delta = 0
        if novo_tamanho is not None:
            if novo_tamanho < 1 or novo_tamanho > 10:
                return "Tamanho do arquivo deve estar entre 1GB e 10GB."
            tamanho_anterior = arquivo.get("tamanho_gb", 0)
            delta = novo_tamanho - tamanho_anterior

        nova_capacidade = capacidade_atual + delta
        if nova_capacidade > capacidade_total:
            return f"Capacidade excedida. Máximo disponível: {capacidade_total - capacidade_atual}GB."
        if nova_capacidade < 0:
            nova_capacidade = 0

        atualizado = self.repo.atualizar_arquivo_servidor(arquivo_id, **kwargs)
        if atualizado is None:
            return "Nenhuma alteração informada para o arquivo."

        if delta != 0:
            self.repo.atualizar_servidor(servidor_id, capacidade_atual=nova_capacidade)

        return {
            "arquivo": atualizado,
            "capacidade_atual": nova_capacidade,
            "capacidade_total": capacidade_total,
        }

    def excluir_arquivo(self, servidor_id, arquivo_id):
        servidor = self.repo.listar_servidor_por_id(servidor_id)
        if not servidor:
            return "Servidor não encontrado."

        arquivo = self.repo.buscar_arquivo_por_id(arquivo_id)
        if not arquivo:
            return "Arquivo não encontrado."

        if str(arquivo.get("servidor_id")) != str(servidor_id):
            return "Arquivo não pertence a este servidor."

        capacidade_atual = servidor.get("capacidade_atual", 0)
        capacidade_total = servidor.get("capacidade_total", Servidor.CAPACIDADE_TOTAL)
        tamanho = arquivo.get("tamanho_gb", 0)
        nova_capacidade = capacidade_atual - tamanho
        if nova_capacidade < 0:
            nova_capacidade = 0

        self.repo.excluir_arquivo_servidor(arquivo_id)
        self.repo.atualizar_servidor(servidor_id, capacidade_atual=nova_capacidade)

        return {
            "deleted": True,
            "capacidade_atual": nova_capacidade,
            "capacidade_total": capacidade_total,
        }
    
    