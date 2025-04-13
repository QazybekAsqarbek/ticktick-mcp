from mcp.server.fastmcp import FastMCP

# make requests to database to get data

mcp = FastMCP("ticktick-mcp")


@mcp.route("/")
def index():
    return "Hello, World!"



@mcp.route("/tasks")
def tasks():
    return "Tasks"



# ===== Tools =====

@mcp.tool("get_tasks")
def get_tasks():
    return "Tasks"


@mcp.tool("get_projects")
def get_projects():
    return "Projects"


@mcp.tool("get_notes")
def get_notes():
    return "Notes"


if __name__ == "__main__":
    mcp.run()
