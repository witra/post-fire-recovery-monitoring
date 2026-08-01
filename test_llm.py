from langchain_ollama import ChatOllama
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

llm = ChatOllama(model="qwen2.5:7b", temperature=0)
response = llm.invoke("Explain how to measure NDVI in remote sensing domain in one sentence.")

logger.info(response.content)