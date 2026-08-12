import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient({
        "hybrid_search": {   # server name
            "command": "python",
            "args": [
                r"D:\complete_content_new\llmops-batch\ecomm-prod-assistant\prod_assistant\mcp_servers\product_search_server.py"
            ],  # absolute path
            "transport": "stdio",
        }
    })

    # Discover tools
    tools = await client.get_tools()
    print("Available tools:", [t.name for t in tools])

    # Pick tools by name
    retriever_tool = next(t for t in tools if t.name == "get_product_info")
    web_tool = next(t for t in tools if t.name == "web_search")

    # --- Step 1: Try retriever first ---
    #query = "Samsung Galaxy S25 price"
    # query = "iPhone 15"
    query = "iPhone 17?"
    retriever_result = await retriever_tool.ainvoke({"query": query})
    print("\nRetriever Result:\n", retriever_result)

    # --- Step 2: Fallback to web search if retriever fails ---
    if not retriever_result.strip() or "No local results found." in retriever_result:
        print("\n No local results, falling back to web search...\n")
        web_result = await web_tool.ainvoke({"query": query})
        print("Web Search Result:\n", web_result)

if __name__ == "__main__":
    asyncio.run(main())