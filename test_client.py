import asyncio
import logging
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

async def main(run_tool_test=True):
    transport = StdioTransport(
        command="python",
        args=["mcp_server.py"]
        )
    client = Client(transport)
    async with client:
        logger.info("mcp_server.py is connected")
        tools = await client.list_tools()
        logger.info(f"Available tools: ")
        for tool in tools:
            logger.info(f"- {tool.name}")
        if run_tool_test:
            result = await client.call_tool(
                "assess_fire_event",
                {
                    "lat": 44.57616,
                    "lon": -1.18168,
                    "pre_date": "10-07-2022",
                    "post_date": "01-08-2022",
                    "buffer_days": 10,
                    "half_size_m": 2500
                }
            )
            logger.info(f"Tool result: {result}")
        
if __name__ == "__main__":
    asyncio.run(main())