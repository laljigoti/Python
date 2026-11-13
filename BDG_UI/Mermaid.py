from nicegui import ui

# Initial mermaid syntax definition
mermaid_code = """
graph LR
    A[Start] --> B{Is it working?}
    B -- Yes --> C[Great!]
    B -- No --> D[Debug]
"""

# Create the mermaid element
chart = ui.mermaid(mermaid_code).style('width: 100%; height: 300px;')

def add_node():
    global mermaid_code
    # Dynamically append a new node and link to the Mermaid syntax string
    mermaid_code += "\n    D --> E[Fix Issue]"
    
    # Update the content and refresh the element on the client side
    chart.content = mermaid_code
    chart.update()

ui.button('Extend Chart', on_click=add_node)

ui.run()