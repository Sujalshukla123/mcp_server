# from mcp.server.fastmcp import FastMCP
# import requests

# mcp = FastMCP("weather-server")

# @mcp.tool(name="get_weather", description="Returns weather information for a given city without using any API key.")
# def get_weather(city: str) -> dict:
#     try:
#         # Get simple weather summary from wttr.in
#         response = requests.get(f"https://wttr.in/{city}?format=3", timeout=10)
#         if response.status_code == 200:
#             return {"weather": response.text.strip()}
#         else:
#             return {"error": f"Failed to fetch weather (status code {response.status_code})"}
#     except Exception as e:
#         return {"error": str(e)}

# if __name__ == "__main__":
#     print("🌤️ Starting Weather MCP Server (no API)...")
#     mcp.run()
from mcp.server.fastmcp import FastMCP
import requests

# create server 
mcp = FastMCP("Weather Server")

@mcp.tool()
def get_weather(city : str)-> str :
    endpoint = "https://wttr.in"
    response = requests.get(f"{endpoint}/{city}")
    return response.text

# run the server
if __name__ == "__main__":
    mcp.run()