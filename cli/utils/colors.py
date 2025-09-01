"""
Color constants for CLI output
"""

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color
    
    @staticmethod
    def disable():
        """Disable colors (for non-terminal output)"""
        Colors.RED = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.BLUE = ''
        Colors.PURPLE = ''
        Colors.CYAN = ''
        Colors.WHITE = ''
        Colors.BOLD = ''
        Colors.NC = ''