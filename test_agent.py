import asyncio
import sys
import logging

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from langchain_ollama import ChatOllama
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
from pydantic import create_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

def get_input_args(tool):
    schema = tool.inputSchema
    input_args = {}
    for name, info in schema["properties"].items():
        python_type = {
            "number": float,
            "integer": int,
            "string": str
        }[info["type"]]

        if name in schema.get("required", []):
            input_args[name] = (python_type, ...)
        else:
            input_args[name] = (python_type, info['default'])
    return input_args


async def main():
    transport = StdioTransport(command=sys.executable, args=["mcp_server.py"])
    async with Client(transport) as mcp_client:
        logger.info("connected to mcp_server.py")
        mcp_tools = await mcp_client.list_tools()
        logger.info(f"Available tools: {[[tool.name] for tool in mcp_tools]}")

        lc_tools = []
        for tool in mcp_tools:
            input_args = get_input_args(tool)
            InputModel = create_model(f"{tool.name}Input", **input_args)

            async def call_mcp_tool(**kwargs):
                result = await mcp_client.call_tool(tool.name, kwargs)
                return result.data
            lc_tool = StructuredTool.from_function(coroutine=call_mcp_tool, 
                                                   name=tool.name, 
                                                   description=tool.description,
                                                   args_schema=InputModel)
            lc_tools.append(lc_tool)

        llm = ChatOllama(model="qwen2.5:7b", temperature=0)
        agent = create_agent(llm, lc_tools)

        response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content":
                        """
                        Assess wildfire impact at Girande, France as the following details:
                        latitude: 44.57616
                        longitude: -1.18168

                        use:
                        pre-fire date: 2022-07-10
                        post-fire date: 2022-08-01
                        buffer day: 2 weeks
                         
                        please save to a folder called "data_test". Then give your opinion on its result.

                        """
                    }
                ]
            }
        )


        logger.info(f"FINAL RESPONSE: \n {response['messages'][-1].content} \n\n")
        logger.info(f"TOOL CALLS: \n\n{response['messages'][1].tool_calls}")

if __name__ == "__main__":
    asyncio.run(main())
