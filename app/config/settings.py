import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "")
HORARIO_EXECUCAO = os.getenv("HORARIO_EXECUCAO", "08:00")
NICHO_BUSCA = os.getenv("NICHO_BUSCA", "restaurantes")
CIDADE_BUSCA = os.getenv("CIDADE_BUSCA", "São Paulo")
MAX_LEADS_POR_DIA = int(os.getenv("MAX_LEADS_POR_DIA", "20"))
CANAL_ENVIO = "whatsapp"

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/prospects.db")
LOG_PATH = os.path.join(os.path.dirname(__file__), "../../logs/agent.log")
TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "../../data/templates")
