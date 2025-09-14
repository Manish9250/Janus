from rich.console import Console
from rich.theme import Theme

# Create a console object
console = Console()

# Your comment variable
comment = "This is a message with a dark background."

# Print the text with a bold white foreground and a black background
# The style [bold white on black] wraps the entire string.
console.print(f"[bold white on black] Janus : {comment}[/bold white on black]")

# A dark blue background
console.print(f"[bold cyan on navy_blue] Janus : {comment}[/bold cyan on navy_blue]")

# A dark grey background
console.print(f"[bold yellow on grey30] Janus : {comment}[/bold yellow on grey30]")