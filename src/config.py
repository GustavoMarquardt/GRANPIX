"""
Configurações globais do sistema GRANPIX
"""

# ============ PRÊMIOS EM DORICOINS ============

# Valor ganho por vitória em uma batalha
PREMIACAO_VITORIA_BATALHA = 1000

# Valor padrão ganho por participar de uma etapa
PREMIACAO_POR_ETAPA = 2000

# ============ DESGASTE ============

# Desgaste base aplicado a cada batalha (inclusive empates)
DESGASTE_BASE_BATALHA = 15.0

# Multiplicador de desgaste em caso de empate (1 = mesmo desgaste, 2 = dobrado)
MULTIPLICADOR_DESGASTE_EMPATE = 2.0

# ============ BATALHAS ============

# Chance de empate em uma batalha (em percentual)
# Empates causam desgaste mas ninguém recebe premiação
CHANCE_EMPATE = 10.0
