# config.py

"""Central configuration for the Investia Intranet app."""

CALENDAR_URL_FULL = (
    "https://calendar.google.com/calendar/embed?src=279f066c8ef646730af43e10bb02220a499f739391184c437529eab94ce61061%40group.calendar.google.com&ctz=Europe%2FBrussels"
)

CALENDAR_URL_AGENDA = (
    "https://calendar.google.com/calendar/embed?height=600&wkst=2&ctz=Europe%2FBrussels&showPrint=0&mode=AGENDA&hl=en&src=Mjc5ZjA2NmM4ZWY2NDY3MzBhZjQzZTEwYmIwMjIyMGE0OTlmNzM5MzkxMTg0YzQzNzUyOWVhYjk0Y2U2MTA2MUBncm91cC5jYWxlbmRhci5nb29nbGUuY29t&color=%23a79b8e"
)

# TOOL_LINKS structure:
#   (label: str, icon: str, url: str, requires_board: bool)
# The last boolean controls privileges. When True, the tool is only visible to board members.
# Keep it False for tools available to everyone.
TOOL_LINKS = [
    ("Member platform", "📊", "https://fund.investialeuven.be", False),
    ("Member Drive", "📂", "https://drive.google.com/drive/folders/1VfsWiHpd1oS8lM5YK4j2ik-3WPiuvNWV?usp=share_link", False),
    ("Industry scanner", "🔍", "https://industry.streamlit.app", False),
    ("Stock alert", "📈", "https://analyst-investia.streamlit.app", False),
    ("Investia website", "🌐", "https://investialeuven.be", False),
    ("Treasurer budget", "💲", "https://accounting-investia.streamlit.app", True),
]