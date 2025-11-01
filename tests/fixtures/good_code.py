"""
Sample Python file with good code quality
Used for testing code analyzer - should have high maintainability score
"""


class Calculator:
    """
    A simple calculator class demonstrating clean code
    """
    
    def add(self, a, b):
        """Add two numbers"""
        return a + b
    
    def subtract(self, a, b):
        """Subtract b from a"""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers"""
        return a * b
    
    def divide(self, a, b):
        """
        Divide a by b
        Handles division by zero
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


def validate_email(email):
    """
    Validate email format
    Returns True if valid, False otherwise
    """
    if not email or '@' not in email:
        return False
    
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    return '.' in parts[1]


def format_name(first_name, last_name):
    """
    Format a person's name
    Returns formatted string
    """
    if not first_name or not last_name:
        return ""
    
    return f"{first_name.strip().title()} {last_name.strip().title()}"


def process_list(items):
    """
    Process a list of items
    Returns filtered and sorted list
    """
    if not items:
        return []
    
    # Filter out None values
    filtered = [item for item in items if item is not None]
    
    # Sort the list
    return sorted(filtered)


def main():
    """
    Main entry point
    Demonstrates clean, simple code structure
    """
    calc = Calculator()
    
    # Perform some calculations
    result1 = calc.add(10, 5)
    result2 = calc.multiply(3, 4)
    
    print(f"Results: {result1}, {result2}")


if __name__ == "__main__":
    main()