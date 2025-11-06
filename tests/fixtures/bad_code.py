"""
Sample Python file with various code quality issues
Used for testing code analyzer
"""
import os
import subprocess

# TODO: Refactor this entire module
# FIXME: Security issues need addressing
# HACK: This is a temporary solution

# Hardcoded credentials - security issue
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"
SECRET_TOKEN = "secret_abc_xyz"


def process_user_data(user_id, name, email, phone, address, city, state, zipcode):
    """
    Function with too many parameters (8 params)
    This should be flagged for refactoring
    """
    # TODO: Use a user object instead
    result = {
        'id': user_id,
        'name': name,
        'email': email,
        'phone': phone,
        'address': address,
        'city': city,
        'state': state,
        'zip': zipcode
    }
    return result


def calculate_discount(price, quantity, customer_type, is_member, promo_code, season, category):
    """
    Another function with too many parameters (7 params)
    """
    discount = 0
    if customer_type == 'premium':
        discount += 0.2
    if is_member:
        discount += 0.1
    if quantity > 10:
        discount += 0.05
    if promo_code:
        discount += 0.15
    if season == 'holiday':
        discount += 0.1
    if category == 'electronics':
        discount += 0.05
    
    return price * (1 - discount)


def dangerous_function(user_input):
    """
    Function with security vulnerabilities
    """
    # Security issue: eval
    result = eval(user_input)
    
    # Security issue: exec
    exec(user_input)
    
    # Security issue: shell injection
    subprocess.run(user_input, shell=True)
    
    return result


class DataProcessor:
    """
    Class with a very long and complex method
    """
    
    def __init__(self):
        self.data = []
    
    def complex_processing_method(self, items):
        """
        This is a very long function (>50 lines) with high complexity
        Should definitely be flagged for refactoring
        """
        results = []
        
        # FIXME: This is way too complex
        for item in items:
            if item is None:
                continue
            
            if isinstance(item, dict):
                if 'type' in item:
                    if item['type'] == 'A':
                        if 'value' in item:
                            if item['value'] > 100:
                                results.append(item['value'] * 2)
                            else:
                                results.append(item['value'])
                        else:
                            results.append(0)
                    elif item['type'] == 'B':
                        if 'value' in item:
                            if item['value'] < 50:
                                results.append(item['value'] / 2)
                            else:
                                results.append(item['value'])
                        else:
                            results.append(0)
                    elif item['type'] == 'C':
                        if 'value' in item:
                            results.append(item['value'] * 3)
                        else:
                            results.append(0)
                    else:
                        results.append(0)
                else:
                    results.append(0)
            elif isinstance(item, list):
                if len(item) > 0:
                    if isinstance(item[0], int):
                        results.append(sum(item))
                    else:
                        results.append(len(item))
                else:
                    results.append(0)
            elif isinstance(item, str):
                if item.isdigit():
                    results.append(int(item))
                else:
                    results.append(len(item))
            elif isinstance(item, int):
                if item > 0:
                    if item % 2 == 0:
                        results.append(item * 2)
                    else:
                        results.append(item * 3)
                else:
                    results.append(0)
            elif isinstance(item, float):
                results.append(int(item))
            else:
                results.append(0)
        
        return results


def add_user(first_name, last_name, email, phone, address, city, state, zipcode):
    """
    Function with 8 parameters - should be flagged
    """
    # TODO: Create a User class
    user = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'phone': phone,
        'address': address,
        'city': city,
        'state': state,
        'zipcode': zipcode
    }
    return user


def simple_function():
    """
    A simple, clean function for contrast
    """
    return "Hello, World!"


# XXX: This needs to be removed
def deprecated_function():
    """Old function that should be removed"""
    pass