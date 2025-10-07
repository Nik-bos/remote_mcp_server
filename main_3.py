from fastmcp import FastMCP
import random
import json

# Creating the instance of FastMCP
mcp = FastMCP("Simple Calculator")

# Add two numbers
@mcp.tool
def add(a: float, b:float)->float:
    '''This function adds the two numbers.
    
    Args:
        a: First number
        b: Second number

    Return:
        Sum of a and b
    '''

    return a+b

# Roll n dices
@mcp.tool
def roll_dice(n: int)->list[int]:
    '''Roll n number of dices and return the result
    
    Args:
        n: Number of dices to roll

    Return:
        List of numbers obtained by rolling each dice.
    '''

    return [random.randint(1,6) for i in range(n)]

# Resources: For server's information
@mcp.resource("info://server")
def server_info()->str:
    '''Get information about this server'''

    info = {
        "name": "Simple Calculator Server",
        "version": "1.0.0",
        "description": 'A basic MCP server with math tools',
        "tools": ['add', 'roll_dice'],
        "author": 'Nikunj Bosamiya'
    }

    return json.dumps(info, indent = 2) 

if __name__ == "__main__":
    mcp.run(transport = 'http', host = "0.0.0.0", port = 8000)
    